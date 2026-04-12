# Medication Label Reader V2

FastAPI backend for reading medication package images, extracting grounded medication details, matching medication data stored in PostgreSQL, reusing S3-hosted audio when possible, and generating new compressed medication audio only when needed.

This is an accessibility-focused backend. The app stays conservative: it distinguishes between verified database-backed matches and no-match fallback output, and it avoids inventing instructions that are not supported by OCR text or stored medication data.

## 1. Happy Path

In the happy path, OCR and extraction succeed, PostgreSQL has a confident medication match, and the API returns a database-grounded summary plus S3 audio.

If the matched medication already has reusable S3 audio, the app skips TTS and FFmpeg to avoid unnecessary cost. If the medication does not have audio yet, the app generates it once, compresses it, uploads it to S3, and saves the S3 reference on the medication record for future reuse.

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI API
    participant OCR as OCR Provider
    participant LLM as OpenAI Extraction
    participant DB as PostgreSQL
    participant TTS as OpenAI TTS
    participant FFmpeg
    participant S3 as AWS S3

    User->>API: Upload medication label image
    API->>OCR: Extract text from image
    OCR-->>API: OCR text
    API->>LLM: Extract drug_name, dose, form, confidence
    LLM-->>API: Structured extraction
    API->>DB: Find confident medication match
    DB-->>API: Medication record

    alt Medication has existing S3 audio
        API-->>User: Return summary + existing S3 audio URL
    else Medication audio missing
        API->>TTS: Generate summary audio
        TTS-->>API: Raw audio file
        API->>FFmpeg: Compress to MP3, mono, 32 kHz, 64 kbps
        FFmpeg-->>API: Compressed MP3
        API->>S3: Upload compressed MP3
        S3-->>API: S3 key + URL
        API->>DB: Save audio_s3_key, audio_url, audio_updated_at
        API-->>User: Return summary + new S3 audio URL
    end
```

Example successful response shape:

```json
{
  "request_id": "uuid",
  "ocr_text": "Tylenol 500 mg tablet",
  "extraction": {
    "drug_name": "Tylenol",
    "dose": "500 mg",
    "form": "tablet",
    "confidence": 0.95,
    "notes": "..."
  },
  "kb_match": {
    "matched": true,
    "canonical_name": "Tylenol",
    "match_type": "canonical",
    "score": 1.0
  },
  "summary": {
    "text": "Tylenol, 500 mg. Commonly used for pain relief and fever reduction. Warning: Do not exceed the recommended dose.",
    "source": "structured_kb"
  },
  "audio": {
    "content_type": "audio/mpeg",
    "s3_key": "medications/tylenol.mp3",
    "url": "https://<bucket>.s3.<region>.amazonaws.com/medications/tylenol.mp3",
    "source": "medication_audio_cache"
  },
  "status": "success"
}
```

## 2. Unhappy Path

In the main unhappy path, OCR may still succeed, but the extracted medication cannot be confidently matched to PostgreSQL. The product rule is simple: do not guess the medication and do not generate new request-specific fallback audio.

Instead, the API returns a conservative fallback message and points to one shared pre-generated fallback audio file in S3.

Fallback text:

```text
I could not confidently identify this medication. Please verify with a doctor, pharmacist, or caregiver before taking it.
```

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI API
    participant OCR as OCR Provider
    participant LLM as OpenAI Extraction
    participant DB as PostgreSQL
    participant S3 as AWS S3

    User->>API: Upload medication label image
    API->>OCR: Extract text from image
    OCR-->>API: OCR text
    API->>LLM: Extract drug_name, dose, form, confidence
    LLM-->>API: Structured extraction
    API->>DB: Find confident medication match
    DB-->>API: No confident match
    API->>S3: Use configured shared fallback audio URL
    API-->>User: Return conservative fallback + shared S3 fallback audio
```

Other failure behavior:

- If OCR fails, the API returns an error because there is no reliable text to analyze.
- If extraction fails after OCR succeeds, the API falls back to the same conservative no-match response.
- If TTS, FFmpeg, or S3 upload fails while creating missing medication audio, the API still returns the text summary and reports audio as unavailable or not updated.
- No-match fallback audio should not call TTS, should not call FFmpeg, and should not create new S3 objects per request.

## 3. Architecture

```mermaid
graph TB
    subgraph Client
        C[Mobile / Web Client]
    end

    subgraph API["API Layer"]
        R[routes.py]
    end

    subgraph Pipeline["Pipeline Orchestrator"]
        P[pipeline.py]
    end

    subgraph Services
        OCR[OCR Adapter\nPaddleOCR]
        EXT[Extraction Service]
        KB[KB Service]
        SUM[Summary Service]
        MED[Medication Audio Service]
        TTS[TTS Service]
        FFM[FFmpeg Compression]
        STG[Storage Service]
    end

    subgraph Data
        REPO[Medication Repository]
        DB[(PostgreSQL)]
        SEED[init_db / medications.json]
    end

    subgraph External
        OAI[OpenAI API]
        S3[AWS S3]
    end

    C -->|analyze-medication| R
    R --> P

    P -->|extract text| OCR
    P -->|parse drug info| EXT
    P -->|find medication| KB
    P -->|build summary| SUM
    P -->|resolve audio| MED

    EXT --> OAI
    TTS --> OAI

    KB --> REPO
    REPO --> DB
    SEED -->|seed on bootstrap| DB

    MED -->|check audio cache| REPO
    MED -->|synthesize speech| TTS
    TTS -->|raw audio| FFM
    FFM -->|compressed MP3| STG
    STG -->|upload / fetch URL| S3
    MED -->|save audio reference| REPO
```

Key architecture decisions:

- PostgreSQL is the source of truth for medication data.
- Each medication can store `audio_s3_key`, `audio_url`, and `audio_updated_at` for reusable happy-path audio.
- FFmpeg is only needed when generating missing medication audio.
- New medication audio must be compressed as MP3, mono, `32000 Hz`, `64 kbps`.
- No-match fallback uses a shared S3 audio asset configured by `FALLBACK_AUDIO_S3_KEY` and `FALLBACK_AUDIO_URL`.
- If TTS, FFmpeg, or S3 upload fails while generating missing medication audio, the API returns HTTP 500 with an error audio payload pointing to a pre-generated S3 file (`ERROR_AUDIO_S3_KEY`, `ERROR_AUDIO_URL`). The error audio instructs the user to check their internet connection and retry, ensuring visually impaired users always receive audio feedback even on failure.
- Local files under `storage/` are temporary or intermediate artifacts, not the final client-facing audio source.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

For V2 local development you also need:

- PostgreSQL running locally or remotely
- `ffmpeg` installed and available on your `PATH`
- AWS credentials with permission to upload objects to your S3 bucket

Minimal local database bootstrap:

```bash
.venv/bin/python -m app.db.init_db
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open the API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Configuration

```env
OPENAI_API_KEY=
OCR_PROVIDER=paddle
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TTS_MODEL=gpt-4o-mini-tts
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/med_label_reader
UPLOAD_DIR=storage/uploads
AUDIO_DIR=storage/audio
FFMPEG_BINARY=ffmpeg
AUDIO_OUTPUT_FORMAT=mp3
AUDIO_SAMPLE_RATE=32000
AUDIO_CHANNELS=1
AUDIO_BITRATE=64k
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
S3_BUCKET_NAME=
FALLBACK_AUDIO_S3_KEY=system-audio/fallback-no-match.mp3
FALLBACK_AUDIO_URL=https://<bucket>.s3.<region>.amazonaws.com/system-audio/fallback-no-match.mp3
ERROR_AUDIO_S3_KEY=system-audio/error-audio-unavailable.mp3
ERROR_AUDIO_URL=https://<bucket>.s3.<region>.amazonaws.com/system-audio/error-audio-unavailable.mp3
EXTRACTION_CONFIDENCE_THRESHOLD=0.65
KB_MATCH_CONFIDENCE_THRESHOLD=0.8
ENABLE_MOCK_SERVICES=false
```

## Testing

```bash
.venv/bin/python -m pytest -q
```

Current tests cover health checks, mocked analyze flow, KB matching, summary generation, extraction mock behavior, medication audio cache reuse, and shared fallback audio behavior.

# EchoAid — Medication Label Reader

FastAPI backend for reading medication package images, extracting structured medication details, matching against a PostgreSQL knowledge base, and returning a spoken audio summary generated locally via Coqui TTS.

This is an accessibility-focused backend. The app stays conservative: it distinguishes between verified database-backed matches and no-match fallback output, and it avoids inventing instructions that are not supported by OCR text or stored medication data.

Audio is **always regenerated per request** — never cached — to ensure the spoken summary always reflects the exact dose and details extracted from the current scan. This is a deliberate safety decision: reusing cached audio risks reading out a stale dose to a patient.

## 1. Happy Path

In the happy path, OCR and extraction succeed and PostgreSQL has a confident medication match. The API generates fresh audio from the current summary, compresses it, uploads it to S3, and returns a pre-signed URL.

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI API
    participant OCR as PaddleOCR
    participant LLM as OpenAI Extraction
    participant DB as PostgreSQL
    participant TTS as Coqui TTS (local)
    participant FFmpeg
    participant S3 as AWS S3

    User->>API: Upload medication label image
    API->>OCR: Extract text from image
    OCR-->>API: OCR text
    API->>LLM: Extract drug_name, dose, form, confidence
    LLM-->>API: Structured extraction
    API->>DB: Find confident medication match
    DB-->>API: Medication record
    API->>TTS: Generate audio from summary text
    TTS-->>API: Raw WAV file (local, no API call)
    API->>FFmpeg: Compress to MP3, mono, 32 kHz, 64 kbps
    FFmpeg-->>API: Compressed MP3
    API->>S3: Upload compressed MP3 (keyed by request_id)
    S3-->>API: Pre-signed URL (7-day expiry)
    API-->>User: Return summary + pre-signed audio URL
```

Example successful response:

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
    "s3_key": "medications/<request_id>.mp3",
    "url": "https://s3.<region>.amazonaws.com/<bucket>/medications/<request_id>.mp3?X-Amz-...",
    "source": "generated_medication_audio"
  },
  "status": "success"
}
```

## 2. Unhappy Path

In the main unhappy path, OCR may succeed but the extracted medication cannot be confidently matched to the database. The app returns a conservative fallback message and points to a shared pre-generated fallback audio file in S3.

Fallback text:

```text
I could not confidently identify this medication. Please verify with a doctor, pharmacist, or caregiver before taking it.
```

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI API
    participant OCR as PaddleOCR
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
    API-->>User: Return conservative fallback + shared S3 fallback audio URL
```

Other failure behavior:

- If OCR fails, the API returns an error — there is no reliable text to analyze.
- If extraction fails after OCR succeeds, the app falls back to the same conservative no-match response.
- If TTS, FFmpeg, or S3 upload fails, the API returns HTTP 500 with an error audio payload pointing to a pre-generated S3 file (`ERROR_AUDIO_S3_KEY`). This ensures visually impaired users always receive audio feedback even on failure.
- No-match fallback does not call TTS, FFmpeg, or create new S3 objects per request.

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
        TTS[Coqui TTS\nlocal inference]
        FFM[FFmpeg Compression]
        STG[Storage Service]
    end

    subgraph Data
        REPO[Medication Repository]
        DB[(PostgreSQL)]
        SEED[init_db / medications.json]
    end

    subgraph External
        OAI[OpenAI API\nextraction only]
        S3[AWS S3]
    end

    C -->|analyze-medication| R
    R --> P

    P -->|extract text| OCR
    P -->|parse drug info| EXT
    P -->|find medication| KB
    P -->|build summary| SUM
    P -->|generate audio| MED

    EXT --> OAI

    KB --> REPO
    REPO --> DB
    SEED -->|seed on bootstrap| DB

    MED -->|synthesize speech| TTS
    TTS -->|raw WAV| FFM
    FFM -->|compressed MP3| STG
    STG -->|upload + pre-sign URL| S3
```

Key architecture decisions:

- PostgreSQL is the source of truth for medication data.
- TTS runs locally via Coqui TTS — no external API call, no cost per request.
- Audio is never cached. Every request generates fresh audio from the current summary so the spoken dose always matches what was scanned.
- Each audio file is keyed by `request_id` in S3 (`medications/<request_id>.mp3`), making every request traceable and independent.
- S3 audio URLs are pre-signed with a 7-day expiry using the regional endpoint (SigV4) to avoid redirect-signature mismatches.
- OpenAI is used only for structured extraction (drug name, dose, form) — not for audio.
- FFmpeg compresses audio to MP3, mono, 32000 Hz, 64 kbps.
- No-match fallback uses a shared S3 audio asset configured by `FALLBACK_AUDIO_S3_KEY` and `FALLBACK_AUDIO_URL`.
- If TTS, FFmpeg, or S3 upload fails, the API returns HTTP 500 with an error audio payload (`ERROR_AUDIO_S3_KEY`, `ERROR_AUDIO_URL`).
- Local files under `storage/` are temporary intermediate artifacts, not the final client-facing audio source.

## Local Setup

```bash
# Install Anaconda Python dependencies
conda activate base
pip install -r requirements.txt
pip install paddlepaddle paddleocr TTS

# Copy and fill in environment config
cp .env.example .env

# Bootstrap the database
/opt/homebrew/anaconda3/bin/python -m app.db.init_db

# Run the API
/opt/homebrew/anaconda3/bin/uvicorn app.main:app --reload
```

Prerequisites:
- PostgreSQL running locally or remotely
- `ffmpeg` installed and available on `PATH`
- AWS credentials with `s3:PutObject` and `s3:GetObject` on your bucket

Open the test UI at [http://127.0.0.1:8000/static/test.html](http://127.0.0.1:8000/static/test.html) or API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Configuration

```env
OPENAI_API_KEY=
OCR_PROVIDER=paddle
OPENAI_MODEL=gpt-4.1-mini
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
AWS_REGION=us-east-2
S3_BUCKET_NAME=
FALLBACK_AUDIO_S3_KEY=system-audio/fallback-no-match.mp3
FALLBACK_AUDIO_URL=https://<bucket>.s3.<region>.amazonaws.com/system-audio/fallback-no-match.mp3
ERROR_AUDIO_S3_KEY=system-audio/error-audio-unavailable.mp3
ERROR_AUDIO_URL=https://<bucket>.s3.<region>.amazonaws.com/system-audio/error-audio-unavailable.mp3
EXTRACTION_CONFIDENCE_THRESHOLD=0.65
KB_MATCH_CONFIDENCE_THRESHOLD=0.8
ENABLE_MOCK_SERVICES=false
GOOGLE_APPLICATION_CREDENTIALS=
```

## Testing

```bash
/opt/homebrew/anaconda3/bin/python -m pytest -q
```

Current tests cover health checks, mocked analyze flow, KB matching, summary generation, extraction mock behavior, and shared fallback audio behavior.

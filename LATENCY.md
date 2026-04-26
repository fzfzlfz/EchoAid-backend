# EchoAid — Latency Tracker

This file tracks expected and measured latency for each step of the `/analyze-medication` pipeline.
Update this file every time a step is optimized or a real measurement is taken.

## Current Status: First real measurements taken (2026-04-23)

Test image: Tylenol Extra Strength 500mg caplet label (real photo)
Environment: Local Mac, server running via uvicorn, S3 in us-east-2

---

## Per-Step Breakdown

| Step | What runs | Estimated | Real measurement | Notes |
|------|-----------|-----------|------------------|-------|
| OCR | PaddleOCR on-device | 300–800ms | **9,438–11,666ms** | Far slower than estimated — large label image, 42 lines detected |
| Extraction | OpenAI gpt-4.1-mini API call | 500–1500ms | **1,658–2,877ms** | Within range on high end |
| KB scoring | In-memory fuzzy match | 1–5ms | **44–53ms** | Slightly higher than estimated — still negligible |
| S3 HEAD (cache check) | boto3 head_object | 30–80ms | **85–349ms** → **1–2ms** | First request only — key written to DB, all subsequent requests skip S3 HEAD entirely |
| TTS | Coqui Tacotron2 local inference | 2000–5000ms | **2,988ms** | Within estimated range |
| FFmpeg | MP3 compression subprocess | 100–300ms | **366ms** | Slightly above estimate |
| S3 upload | boto3 upload_file | 150–400ms | **329ms** | Within estimated range |
| S3 presign | boto3 generate_presigned_url | ~5ms | ~1ms | Local signing, no network |

> **To capture logs:** start server with:
> ```bash
> mkdir -p logs && uvicorn app.main:app --reload > logs/server.log 2>&1
> ```
> Then grep: `grep -E "step_|tts_ms|ffmpeg_ms|s3_head_ms|s3_upload_ms|openai_ms|request_end" logs/server.log`

---

## End-to-End Summary

| Scenario | Estimated | Real (2026-04-23) | Real (2026-04-24) | Notes |
|----------|-----------|-------------------|-------------------|-------|
| First scan (cache miss) | 3–8s | 34.15s | **16.08s** | OCR + OpenAI + TTS + FFmpeg + S3 upload |
| Repeat scan (cache hit) | 1–2.5s | 13.65s | **11.33s** | OCR + OpenAI only, TTS/FFmpeg/upload skipped |

### Key observations from real runs
- **OCR is the real bottleneck**: 9,438–11,666ms — far slower than estimated. PaddleOCR is heavy on CPU for dense labels (42 lines)
- **OpenAI is the second bottleneck**: 1,658–2,877ms — variable depending on API load
- **TTS is fast once warm**: 2,988ms — within estimate, model was already loaded
- **S3 HEAD is variable**: 85–349ms — network latency to us-east-2 fluctuates
- **Caching saves ~4s per repeat scan**: audio step drops from 3,965ms to 86–351ms
- **KB match was perfect**: `score: 1.0`, matched as "Tylenol Extra Strength" via alias

---

## Log Lines to Watch

Redirect server output to capture granular per-step timings:

```bash
uvicorn app.main:app --reload > logs/server.log 2>&1
```

Then grep after a request:

```
step_ocr_ms=<ms>
step_extraction_ms=<ms>        # includes openai_ms inside
step_kb_ms=<ms>
step_audio_ms=<ms>             # covers TTS + FFmpeg + S3 upload (cache miss) or just presign (cache hit)
request_end total_ms=<ms>

# Granular inside step_audio:
tts_ms=<ms>
ffmpeg_ms=<ms>
s3_head_ms=<ms>
s3_upload_ms=<ms>
```

---

## Real: `/analyze-medication-text` (Apple path — OCR done on device)

Test: PaddleOCR text from previous Tylenol scan fed directly into `/analyze-medication-text`.
Both calls were cache hits (audio already in S3).

### Per-step (from server logs)

| Step | Call 1 | Call 2 | Notes |
|------|--------|--------|-------|
| OCR | **0ms** | **0ms** | Skipped entirely — client sends text |
| OpenAI extraction | 1,801ms | 2,737ms | Still the variable factor |
| KB scoring | 62ms | 11ms | |
| S3 HEAD (cache hit) | 309ms | 87ms | Variable S3 round trip |
| S3 presign | ~1ms | ~1ms | |
| **Total (server-side)** | **2,175ms** | **2,837ms** | |
| **Total (curl)** | **10,765ms** | **2,843ms** | Call 1 includes ~8.5s cold-start model loading |

> **Cold start note:** The first request after a server restart/reload triggers `@lru_cache`
> initialization for TTS and PaddleOCR models (~8s overhead). Subsequent requests are unaffected.
> In production, use a warm-up request at deploy time to avoid this.

### End-to-end comparison (warmed up, audio cached)

| Endpoint | Client | Total | vs image endpoint |
|----------|--------|-------|-------------------|
| `POST /analyze-medication` | Android | ~11s | baseline |
| `POST /analyze-medication-text` | Apple (Swift) | **~2–3s** | **~8–9s faster** |

---

## Model Comparison: GPT-4.1-mini vs GPT-4.1-nano vs GPT-5.4-nano

All tested on `/analyze-medication-text`, audio cached, warmed up server.
Cost per 1K requests based on ~500 input + ~100 output tokens.

| | GPT-4.1-mini | GPT-4.1-nano | GPT-5.4-nano | GPT-5.4-nano + trimmed prompt |
|---|---|---|---|---|
| OpenAI latency | 1,801–2,737ms | 1,284–2,370ms | 1,116–2,193ms | **964–1,234ms** |
| Server total_ms | 2,175–2,837ms | 1,375–2,472ms | 1,200–2,296ms | **~1,050–1,320ms** |
| curl total (warmed) | ~2–3s | ~1.4–2.5s | ~1.2–2.3s | **~1.0–1.3s** |
| Input price /1M tokens | $0.40 | $0.10 | $0.20 | **$0.20** |
| Output price /1M tokens | $1.60 | $0.40 | $1.25 | **$1.25** |
| Cost per 1K requests | ~$3.25 | ~$0.21 | ~$0.28 | **~$0.28** |
| Extraction accuracy | Tylenol ✓ | Tylenol ✓ | Tylenol Extra Strength ✓ | **Tylenol Extra Strength ✓** |
| Confidence | 0.90 | 0.90–0.95 | 0.86–0.92 | **0.86** |

**Verdict:** GPT-5.4-nano + trimmed prompt (~70 tokens vs ~200) is the fastest (~1.0–1.3s curl) with no accuracy loss.
Prompt trimming saved ~200–900ms vs the original prompt. Current default: `gpt-5.4-nano` with trimmed prompt.

---

## Projected: After Switching OCR to Apple Vision (Swift)

Apple Vision runs on-device using the Neural Engine. Swift would call `/extract-only` with raw text instead of uploading the image to `/analyze-medication`.

### New flow
```
Swift → Apple Vision OCR (~200ms, on-device) → POST /extract-only (text only) → OpenAI → KB → Audio → response
```

### Per-step projection

| Step | Current (PaddleOCR) | Projected (Apple Vision) | Notes |
|------|---------------------|--------------------------|-------|
| OCR | 9,438–11,666ms | **~100–300ms** | On-device Neural Engine, no server involvement |
| Image upload | included in OCR step | **~0ms** | Text sent instead of image — negligible payload |
| OpenAI extraction | 1,658–2,877ms | 1,658–2,877ms | Unchanged |
| KB scoring | 44–53ms | 44–53ms | Unchanged |
| S3 HEAD | 85–349ms | 85–349ms | Unchanged |
| TTS / FFmpeg / S3 upload | 3,965ms (cache miss) | 3,965ms (cache miss) | Unchanged |
| Audio (cache hit) | 86–351ms | 86–351ms | Unchanged |

### End-to-end projection

| Scenario | Current | Projected | Saving |
|----------|---------|-----------|--------|
| First scan (cache miss) | 16.08s | **~6–7s** | ~10s |
| Repeat scan (cache hit) | 11.33s | **~2–3s** | ~9s |

OCR alone accounts for ~60–70% of total latency. Switching to Apple Vision would make repeat scans feel near-instant from the user's perspective.

---

## History

| Date | Change | Impact |
|------|--------|--------|
| 2026-04-23 | Added per-step and granular latency logging | Can now measure all steps |
| 2026-04-23 | Added S3 audio caching by canonical_name + strength + form | Repeat scans skip TTS, FFmpeg, S3 upload |
| 2026-04-23 | First real measurement with Tylenol photo | First scan: 34.15s, Repeat: 13.65s |
| 2026-04-24 | Server log redirection — full granular breakdown captured | First scan: 16.08s, Repeat: 11.33s. OCR identified as dominant bottleneck at 9–11s |
| 2026-04-24 | Added `/analyze-medication-text` for Apple clients | Warmed-up repeat scan drops to **2–3s** — 8–9s faster than image endpoint |
| 2026-04-24 | Switched from gpt-4.1-mini → gpt-4.1-nano | ~30% faster (1.4–2.5s vs 2–3s), 93% cheaper ($0.21 vs $3.25 per 1K) |
| 2026-04-24 | Switched from gpt-4.1-nano → gpt-5.4-nano | Faster again (1.2–1.7s), better extraction ("Tylenol Extra Strength" vs "Tylenol"), slightly higher cost ($0.28 vs $0.21 per 1K) |
| 2026-04-24 | Re-measured gpt-5.4-nano on `/analyze-medication-text` (3 warmed runs) | openai_ms: 1,116–2,193ms, server total: 1,200–2,296ms. Floor is faster than 4.1-nano (1,116ms vs 1,284ms). High-end variance from OpenAI API load. Confirmed faster. |
| 2026-04-24 | Trimmed system prompt from ~200 → ~70 tokens | openai_ms dropped to 964–1,234ms, curl ~1.0–1.3s. ~200–900ms faster than full prompt. Added "full brand name including variant" hint to preserve "Tylenol Extra Strength" accuracy. |
| 2026-04-24 | S3 audio key cached in PostgreSQL per medication record | S3 HEAD eliminated after first request — step_audio_ms drops from 75–350ms to **1–2ms**. On S3 delete, DB key is cleared and audio regenerated automatically. |
| 2026-04-24 | Projected Apple Vision migration | Expected first scan: ~6–7s, repeat: ~2–3s — saving ~9–10s by moving OCR to Swift |

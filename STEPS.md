# Build Steps

1. Read `README.md` thoroughly and capture the MVP scope.
2. Scaffold the FastAPI project structure, config, prompt, storage folders, and sample medication KB.
3. Implement the OCR adapter layer and one default provider path, while keeping Google Vision extension points ready.
4. Implement OpenAI-backed extraction and TTS services with safe fallbacks and clear error handling.
5. Implement KB lookup, summary generation, and the end-to-end medication analysis pipeline.
6. Expose FastAPI endpoints for health, OCR debug, extraction debug, and end-to-end analysis.
7. Add tests that mock OCR, extraction, and TTS so the project is runnable locally without external calls.
8. Install dependencies when possible, run tests, and fix build issues until the project is in a clean runnable state.

## V2 Migration Steps

1. Update the README to describe PostgreSQL medication storage, FFmpeg compression, and AWS S3 processed audio storage.
2. Replace the JSON-backed KB service wiring with a PostgreSQL repository interface.
3. Add medication audio metadata fields so each matched medication can reuse an existing S3 audio file.
4. Add FFmpeg compression with MP3, mono, 32 kHz, and 64 kbps output settings.
5. Add S3 upload support for newly generated medication audio.
6. Update the pipeline so cached medication audio skips TTS and FFmpeg.
7. Update the no-match path so it returns a shared fallback S3 audio file without generating request-specific TTS.
8. Add tests for cached medication audio reuse and shared fallback audio behavior.

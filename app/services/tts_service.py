import time
from pathlib import Path

from app.core.exceptions import TextToSpeechError
from app.core.logging import get_logger

logger = get_logger(__name__)


class TextToSpeechService:
    MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"

    def __init__(self, audio_dir: Path, enable_mock: bool = False) -> None:
        self.audio_dir = audio_dir
        self.enable_mock = enable_mock
        self._tts = None
        if not enable_mock:
            try:
                from TTS.api import TTS  # type: ignore
                self._tts = TTS(model_name=self.MODEL_NAME, progress_bar=False)
            except ImportError as exc:
                raise TextToSpeechError("Coqui TTS is not installed. Run: pip install TTS") from exc

    def synthesize(self, text: str, request_id: str) -> Path:
        output_path = self.audio_dir / f"{request_id}.wav"

        if self.enable_mock:
            output_path.write_bytes(b"mock-audio")
            return output_path

        logger.info("tts_start request_id=%s text_length=%d", request_id, len(text))
        t0 = time.perf_counter()
        try:
            self._tts.tts_to_file(text=text, file_path=str(output_path))
            logger.info("tts_success request_id=%s output=%s tts_ms=%.0f", request_id, output_path.name, (time.perf_counter() - t0) * 1000)
            return output_path
        except Exception as exc:
            raise TextToSpeechError(f"Failed to generate audio: {exc}") from exc

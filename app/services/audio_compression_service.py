import subprocess
import time
from pathlib import Path

from app.core.exceptions import AudioCompressionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AudioCompressionService:
    def __init__(
        self,
        ffmpeg_binary: str,
        sample_rate: int,
        channels: int,
        bitrate: str,
        output_format: str = "mp3",
        enable_mock: bool = False,
    ) -> None:
        self.ffmpeg_binary = ffmpeg_binary
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.output_format = output_format
        self.enable_mock = enable_mock

    def compress(self, input_path: Path, request_id: str, output_dir: Path) -> Path:
        output_path = output_dir / f"{request_id}_compressed.{self.output_format}"

        if self.enable_mock:
            output_path.write_bytes(input_path.read_bytes())
            return output_path

        command = [
            self.ffmpeg_binary,
            "-y",
            "-i",
            str(input_path),
            "-acodec",
            "libmp3lame",
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            "-b:a",
            self.bitrate,
            str(output_path),
        ]

        logger.info("ffmpeg_start input=%s", input_path.name)
        t0 = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("ffmpeg_failed returncode=%d stderr=%s", result.returncode, result.stderr.strip())
            raise AudioCompressionError(f"FFmpeg failed: {result.stderr.strip()}")
        logger.info("ffmpeg_success output=%s ffmpeg_ms=%.0f", output_path.name, (time.perf_counter() - t0) * 1000)
        return output_path

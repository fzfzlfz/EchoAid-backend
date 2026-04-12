import subprocess
from pathlib import Path

from app.core.exceptions import AudioCompressionError


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

        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AudioCompressionError(f"FFmpeg failed: {result.stderr.strip()}")
        return output_path

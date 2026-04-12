from pathlib import Path

from openai import OpenAI

from app.core.exceptions import TextToSpeechError


class TextToSpeechService:
    def __init__(
        self,
        audio_dir: Path,
        model: str,
        api_key: str | None,
        enable_mock: bool = False,
    ) -> None:
        self.audio_dir = audio_dir
        self.model = model
        self.enable_mock = enable_mock
        self.client = OpenAI(api_key=api_key) if api_key else None

    def synthesize(self, text: str, request_id: str) -> Path:
        output_path = self.audio_dir / f"{request_id}.mp3"

        if self.enable_mock:
            output_path.write_bytes(b"mock-audio")
            return output_path

        if not self.client:
            raise TextToSpeechError("OPENAI_API_KEY is missing. Configure it or enable mock services.")

        try:
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice="alloy",
                input=text,
                format="mp3",
            ) as response:
                response.stream_to_file(output_path)
            return output_path
        except Exception as exc:
            raise TextToSpeechError("Failed to generate audio.") from exc

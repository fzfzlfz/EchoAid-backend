from typing import Protocol

from app.models.domain import OCRResult


class OCRProvider(Protocol):
    def extract_text(self, image_path: str) -> OCRResult:
        """Extract text from an image path."""

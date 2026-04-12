from app.core.exceptions import OCRProcessingError
from app.models.domain import OCRResult


class GoogleVisionOCREngine:
    def extract_text(self, image_path: str) -> OCRResult:
        raise OCRProcessingError(
            "Google Vision OCR is not implemented in V1. Use PaddleOCR or mock services."
        )

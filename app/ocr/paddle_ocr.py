from pathlib import Path

from app.core.exceptions import OCRProcessingError
from app.models.domain import OCRResult


class PaddleOCREngine:
    """Thin adapter around PaddleOCR with a small mock fallback for tests."""

    def __init__(self, enable_mock: bool = False) -> None:
        self.enable_mock = enable_mock
        self._engine = None
        if not enable_mock:
            try:
                from paddleocr import PaddleOCR  # type: ignore

                self._engine = PaddleOCR(
                    lang="en",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                )
            except ImportError as exc:
                raise OCRProcessingError(
                    "PaddleOCR is not installed. Install paddleocr or enable mock services."
                ) from exc

    def extract_text(self, image_path: str) -> OCRResult:
        if self.enable_mock:
            stem = Path(image_path).stem.replace("_", " ")
            text = stem if stem else "unreadable label"
            return OCRResult(full_text=text, lines=[text], confidence=0.5)

        result = self._engine.predict(image_path) if self._engine else None
        if not result or not result[0]:
            raise OCRProcessingError("OCR provider did not return any text.")

        page = result[0]
        rec_texts: list[str] = page.get("rec_texts", [])
        rec_scores: list[float] = page.get("rec_scores", [])

        lines: list[str] = []
        confidences: list[float] = []
        for text, score in zip(rec_texts, rec_scores):
            text = text.strip()
            if text:
                lines.append(text)
                confidences.append(float(score))

        if not lines:
            raise OCRProcessingError("OCR provider returned empty text.")

        average_confidence = sum(confidences) / len(confidences) if confidences else None
        return OCRResult(full_text="\n".join(lines), lines=lines, confidence=average_confidence)

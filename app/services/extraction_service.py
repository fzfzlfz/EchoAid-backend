import json
import time
from pathlib import Path

from openai import OpenAI

from app.core.exceptions import ExtractionError
from app.core.logging import get_logger
from app.models.domain import MedicationExtraction

logger = get_logger(__name__)


class ExtractionService:
    def __init__(
        self,
        prompt_path: Path,
        model: str,
        api_key: str | None,
        enable_mock: bool = False,
    ) -> None:
        self.prompt = prompt_path.read_text(encoding="utf-8")
        self.model = model
        self.enable_mock = enable_mock
        self.client = OpenAI(api_key=api_key) if api_key else None

    def extract(self, ocr_text: str) -> MedicationExtraction:
        if self.enable_mock:
            return self._mock_extract(ocr_text)

        if not self.client:
            raise ExtractionError("OPENAI_API_KEY is missing. Configure it or enable mock services.")

        logger.info("extraction_start model=%s", self.model)
        t0 = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": ocr_text},
                ],
                response_format={"type": "json_object"},
            )
            payload = json.loads(response.choices[0].message.content)
            result = MedicationExtraction.model_validate(payload)
            logger.info("extraction_success drug_name=%s confidence=%.2f openai_ms=%.0f", result.drug_name, result.confidence, (time.perf_counter() - t0) * 1000)
            return result
        except Exception as exc:
            raise ExtractionError(f"Failed to extract structured medication data: {exc}") from exc

    @staticmethod
    def _mock_extract(ocr_text: str) -> MedicationExtraction:
        lowered = ocr_text.lower()
        if "tylenol" in lowered or "acetaminophen" in lowered:
            logger.info("keyword_fallback_match drug_name=Tylenol")
            return MedicationExtraction(
                drug_name="Tylenol",
                dose="500 mg" if "500" in lowered else None,
                form="tablet" if "tablet" in lowered else None,
                confidence=0.9,
                notes="Mock match from OCR text.",
            )
        logger.warning("keyword_fallback_no_match ocr_text_length=%d", len(ocr_text))
        return MedicationExtraction(confidence=0.2, notes="Mock extraction could not identify a medication.")

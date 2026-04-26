import json
from pathlib import Path
from unittest.mock import MagicMock

from app.services.extraction_service import ExtractionService


PROMPT_PATH = Path(__file__).resolve().parents[1] / "app" / "prompts" / "extract_medication.txt"


def _service(enable_mock: bool = False) -> ExtractionService:
    return ExtractionService(
        prompt_path=PROMPT_PATH,
        model="gpt-4.1-mini",
        api_key=None,
        enable_mock=enable_mock,
    )


# Branch 3 — keyword fallback YES
def test_extraction_parser_mock_mode() -> None:
    result = _service(enable_mock=True).extract("Tylenol 500 mg tablet")
    assert result.drug_name == "Tylenol"
    assert result.dose == "500 mg"


# Branch 4 — keyword fallback NO
def test_extraction_keyword_fallback_no_match() -> None:
    result = _service(enable_mock=True).extract("completely unknown product xyz")
    assert result.drug_name is None
    assert result.confidence == 0.2


# Branch 2 — OpenAI extraction success
def test_extraction_openai_success() -> None:
    service = _service()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "drug_name": "Tylenol",
        "strength": "500mg",
        "dose": "2 tablets every 6 hours",
        "form": "tablet",
        "confidence": 0.95,
    })
    service.client = mock_client

    result = service.extract("Tylenol 500mg tablet take 2 tablets every 6 hours")
    assert result.drug_name == "Tylenol"
    assert result.confidence == 0.95

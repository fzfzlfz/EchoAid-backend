from pathlib import Path

from app.services.extraction_service import ExtractionService


PROMPT_PATH = Path(__file__).resolve().parents[1] / "app" / "prompts" / "extract_medication.txt"


def test_extraction_parser_mock_mode() -> None:
    service = ExtractionService(
        prompt_path=PROMPT_PATH,
        model="gpt-4.1-mini",
        api_key=None,
        enable_mock=True,
    )
    result = service.extract("Tylenol 500 mg tablet")
    assert result.drug_name == "Tylenol"
    assert result.dose == "500 mg"

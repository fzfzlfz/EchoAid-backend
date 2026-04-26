from app.ocr.paddle_ocr import PaddleOCREngine


# Branch 1 — OCR success
def test_ocr_mock_returns_text_from_filename(tmp_path) -> None:
    image = tmp_path / "tylenol_500mg_tablet.png"
    image.write_bytes(b"fake-image")

    engine = PaddleOCREngine(enable_mock=True)
    result = engine.extract_text(str(image))

    assert result.full_text == "tylenol 500mg tablet"
    assert result.confidence == 0.5
    assert len(result.lines) == 1

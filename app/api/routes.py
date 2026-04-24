from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.dependencies import get_extraction_service, get_pipeline_service
from app.core.exceptions import AudioUnavailableError, OCRProcessingError
from app.models.schemas import AnalyzeMedicationResponse, ExtractOnlyRequest, OCRDebugResponse
from app.utils.ids import generate_request_id


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ocr-only", response_model=OCRDebugResponse)
async def ocr_only(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline_service),
) -> OCRDebugResponse:
    request_id = generate_request_id()
    try:
        result = await pipeline.run_ocr(file, request_id)
        return OCRDebugResponse(request_id=request_id, ocr=result)
    except OCRProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/extract-only")
async def extract_only(
    payload: ExtractOnlyRequest,
    extraction_service=Depends(get_extraction_service),
) -> dict:
    return extraction_service.extract(payload.ocr_text).model_dump()


@router.post("/analyze-medication", response_model=AnalyzeMedicationResponse)
async def analyze_medication(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline_service),
) -> AnalyzeMedicationResponse | JSONResponse:
    if not file.filename or not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, and png files are supported.")

    try:
        return await pipeline.analyze(file, generate_request_id())
    except OCRProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AudioUnavailableError as exc:
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "audio": {
                    "content_type": "audio/mpeg",
                    "s3_key": settings.error_audio_s3_key,
                    "url": settings.error_audio_url,
                    "source": "error_audio",
                },
            },
        )

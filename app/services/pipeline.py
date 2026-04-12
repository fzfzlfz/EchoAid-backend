from pathlib import Path

from fastapi import UploadFile

from app.core.exceptions import AppError, AudioUnavailableError, ExtractionError, OCRProcessingError
from app.core.logging import get_logger
from app.models.schemas import AnalyzeMedicationResponse, AudioPayload, SummaryPayload
from app.ocr.base import OCRProvider
from app.services.extraction_service import ExtractionService
from app.services.kb_service import MedicationKBService
from app.services.medication_audio_service import MedicationAudioService
from app.services.summary_service import SummaryService
from app.utils.file_utils import save_upload_file


logger = get_logger(__name__)


class MedicationPipelineService:
    def __init__(
        self,
        ocr_provider: OCRProvider,
        extraction_service: ExtractionService,
        kb_service: MedicationKBService,
        summary_service: SummaryService,
        medication_audio_service: MedicationAudioService,
        upload_dir: Path,
    ) -> None:
        self.ocr_provider = ocr_provider
        self.extraction_service = extraction_service
        self.kb_service = kb_service
        self.summary_service = summary_service
        self.medication_audio_service = medication_audio_service
        self.upload_dir = upload_dir

    async def run_ocr(self, upload_file: UploadFile, request_id: str):
        destination = self.upload_dir / f"{request_id}_{upload_file.filename}"
        await save_upload_file(upload_file, destination)
        return self.ocr_provider.extract_text(str(destination))

    async def analyze(self, upload_file: UploadFile, request_id: str) -> AnalyzeMedicationResponse:
        logger.info("request_start request_id=%s provider=%s", request_id, type(self.ocr_provider).__name__)

        try:
            ocr_result = await self.run_ocr(upload_file, request_id)
        except OCRProcessingError:
            logger.exception("ocr_failed request_id=%s", request_id)
            raise

        try:
            extraction = self.extraction_service.extract(ocr_result.full_text)
        except ExtractionError:
            logger.exception("extraction_failed request_id=%s", request_id)
            extraction = self.extraction_service._mock_extract(ocr_result.full_text)

        kb_match = self.kb_service.lookup(extraction)
        logger.info("kb_match request_id=%s matched=%s score=%s", request_id, kb_match.matched, kb_match.score)

        if kb_match.matched:
            summary_text = self.summary_service.generate_from_kb(kb_match, extraction)
            source = "structured_kb"
            status = "success"
            audio_source = "medication_match"
        else:
            summary_text = self.summary_service.generate_fallback()
            source = "fallback"
            status = "partial_success"
            audio_source = "shared_fallback"

        if kb_match.matched:
            audio = self.medication_audio_service.get_audio_for_match(
                kb_match,
                summary_text,
                request_id,
            )
        else:
            audio = self.medication_audio_service.fallback_audio()
        logger.info("audio_resolved request_id=%s source=%s", request_id, audio_source)

        logger.info("request_end request_id=%s summary_source=%s", request_id, source)
        return AnalyzeMedicationResponse(
            request_id=request_id,
            ocr_text=ocr_result.full_text,
            extraction=extraction,
            kb_match=kb_match,
            summary=SummaryPayload(text=summary_text, source=source),
            audio=audio,
            status=status,
        )

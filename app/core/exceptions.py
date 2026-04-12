class AppError(Exception):
    """Base exception for expected application failures."""


class OCRProcessingError(AppError):
    """Raised when OCR cannot extract text from an image."""


class ExtractionError(AppError):
    """Raised when structured extraction fails."""


class TextToSpeechError(AppError):
    """Raised when audio generation fails."""


class AudioCompressionError(AppError):
    """Raised when FFmpeg cannot compress audio."""


class StorageUploadError(AppError):
    """Raised when processed audio cannot be uploaded."""


class AudioUnavailableError(AppError):
    """Raised when audio generation fails due to TTS, FFmpeg, or S3 upload failure."""

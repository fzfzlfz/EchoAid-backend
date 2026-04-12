from pathlib import Path

from fastapi import UploadFile


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    with destination.open("wb") as output_file:
        while chunk := await upload_file.read(1024 * 1024):
            output_file.write(chunk)

import re


def normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def clean_text_for_audio(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()
    return collapsed


def truncate_text(value: str, max_length: int = 180) -> str:
    cleaned = clean_text_for_audio(value)
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3].rstrip() + "..."

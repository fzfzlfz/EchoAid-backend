import re

# Forms that are functionally equivalent for matching purposes
_SOLID_FORMS = {"tablet", "caplet", "pill", "tab"}
_CAPSULE_FORMS = {"capsule", "cap", "gelcap", "softgel", "liqui-gel", "liquigel"}
_LIQUID_FORMS = {"liquid", "syrup", "suspension", "solution", "drops", "elixir"}

_FORM_CATEGORIES = {
    **{f: "solid" for f in _SOLID_FORMS},
    **{f: "capsule" for f in _CAPSULE_FORMS},
    **{f: "liquid" for f in _LIQUID_FORMS},
}


def normalize_form(form: str | None) -> str | None:
    if not form:
        return None
    return form.strip().lower()


def form_category(form: str | None) -> str | None:
    if not form:
        return None
    return _FORM_CATEGORIES.get(normalize_form(form))


def score_form(extracted: str | None, kb: str) -> float:
    """Score 0.0–1.0 how well extracted form matches a KB entry form."""
    if not extracted:
        return 0.5  # unknown — partial credit
    e = normalize_form(extracted)
    k = normalize_form(kb)
    if e == k:
        return 1.0
    if form_category(e) and form_category(e) == form_category(k):
        return 0.7  # same category (caplet ≈ tablet)
    return 0.0


def parse_strength_mg(strength: str | None) -> float | None:
    """
    Parse a strength string to a float in mg.
    Handles: "500mg", "500 mg", "160mg/5mL" (returns per-unit: 32.0), "25 MG"
    Returns None if unparseable.
    """
    if not strength:
        return None
    s = strength.strip().lower()

    # Per-volume form e.g. "160mg/5mL" → 160/5 = 32.0 mg/mL
    per_vol = re.match(r"([\d.]+)\s*mg\s*/\s*([\d.]+)\s*ml", s)
    if per_vol:
        return round(float(per_vol.group(1)) / float(per_vol.group(2)), 4)

    # Simple mg form e.g. "500mg", "500 mg"
    simple = re.match(r"([\d.]+)\s*mg", s)
    if simple:
        return float(simple.group(1))

    return None


def score_strength(extracted: str | None, kb: str) -> float:
    """Score 0.0–1.0 how well extracted strength matches a KB entry strength."""
    if not extracted:
        return 0.5  # unknown — partial credit

    e_val = parse_strength_mg(extracted)
    k_val = parse_strength_mg(kb)

    if e_val is None or k_val is None:
        # Fall back to normalized string comparison
        return 1.0 if extracted.strip().lower() == kb.strip().lower() else 0.0

    if e_val == k_val:
        return 1.0
    # Allow ±10% tolerance for OCR errors (e.g. "498mg" vs "500mg")
    if k_val > 0 and abs(e_val - k_val) / k_val <= 0.10:
        return 0.7
    return 0.0

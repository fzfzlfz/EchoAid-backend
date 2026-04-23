from app.models.domain import KBMatchResult, MedicationExtraction
from app.repositories.base import MedicationRepository
from app.utils.medication_normalization import score_form, score_strength
from app.utils.text_normalization import normalize_text

_NAME_WEIGHT = 0.5
_STRENGTH_WEIGHT = 0.3
_FORM_WEIGHT = 0.2
_NAME_MIN = 0.5  # name must reach this before strength/form are considered


class MedicationKBService:
    def __init__(self, repository: MedicationRepository, match_threshold: float = 0.75) -> None:
        self.repository = repository
        self.match_threshold = match_threshold

    def lookup(self, extraction: MedicationExtraction) -> KBMatchResult:
        if not extraction.drug_name:
            return KBMatchResult(matched=False)

        target_name = normalize_text(extraction.drug_name)
        best_result = KBMatchResult(matched=False)

        for record in self.repository.list_medications():
            candidates = [(record.canonical_name, "canonical")] + [
                (alias, "alias") for alias in record.aliases
            ]

            best_name_score = 0.0
            best_match_type = "canonical"
            for candidate, match_type in candidates:
                s = self._score_name(target_name, normalize_text(candidate))
                if s > best_name_score:
                    best_name_score = s
                    best_match_type = match_type

            # Skip entries where name doesn't even loosely match
            if best_name_score < _NAME_MIN:
                continue

            s_strength = score_strength(extraction.strength, record.strength)
            s_form = score_form(extraction.form, record.form)

            combined = (
                _NAME_WEIGHT * best_name_score
                + _STRENGTH_WEIGHT * s_strength
                + _FORM_WEIGHT * s_form
            )

            if combined > (best_result.score or 0):
                matched = combined >= self.match_threshold
                best_result = KBMatchResult(
                    matched=matched,
                    canonical_name=record.canonical_name if matched else None,
                    match_type=best_match_type if matched else None,
                    score=round(combined, 4),
                    record=record if matched else None,
                )

        return best_result if best_result.matched else KBMatchResult(matched=False, score=best_result.score)

    @staticmethod
    def _score_name(target: str, candidate: str) -> float:
        if not target or not candidate:
            return 0.0
        if target == candidate:
            return 1.0
        if target in candidate or candidate in target:
            shorter = min(len(target), len(candidate))
            longer = max(len(target), len(candidate))
            return shorter / longer
        return 0.0

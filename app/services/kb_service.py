from app.models.domain import KBMatchResult, MedicationExtraction, MedicationRecord
from app.repositories.base import MedicationRepository
from app.utils.text_normalization import normalize_text


class MedicationKBService:
    def __init__(self, repository: MedicationRepository, match_threshold: float = 0.8) -> None:
        self.repository = repository
        self.match_threshold = match_threshold

    def lookup(self, extraction: MedicationExtraction) -> KBMatchResult:
        if not extraction.drug_name:
            return KBMatchResult(matched=False)

        target = normalize_text(extraction.drug_name)
        best_result = KBMatchResult(matched=False)

        for record in self.repository.list_medications():
            candidates = [(record.canonical_name, "canonical")] + [
                (alias, "alias") for alias in record.aliases
            ]
            for candidate, match_type in candidates:
                score = self._score_candidate(target, normalize_text(candidate))
                if score > (best_result.score or 0):
                    matched = score >= self.match_threshold
                    best_result = KBMatchResult(
                        matched=matched,
                        canonical_name=record.canonical_name if matched else None,
                        match_type=match_type if matched else None,
                        score=score,
                        record=record if matched else None,
                    )

        return best_result if best_result.matched else KBMatchResult(matched=False, score=best_result.score)

    @staticmethod
    def _score_candidate(target: str, candidate: str) -> float:
        if not target or not candidate:
            return 0.0
        if target == candidate:
            return 1.0
        if target in candidate or candidate in target:
            shorter = min(len(target), len(candidate))
            longer = max(len(target), len(candidate))
            return shorter / longer
        return 0.0

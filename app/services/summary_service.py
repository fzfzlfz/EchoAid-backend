from app.models.domain import KBMatchResult, MedicationExtraction


class SummaryService:
    def generate_from_kb(
        self,
        match: KBMatchResult,
        extraction: MedicationExtraction,
    ) -> str:
        if not match.record:
            raise ValueError("KB match record is required for structured summaries.")

        dose = extraction.dose or "dose not listed"
        warning_short = match.record.warnings[0] if match.record.warnings else "Please follow the package directions."
        return match.record.audio_summary_template.format(
            name=match.record.canonical_name,
            strength=match.record.strength,
            dose=dose,
            purpose=match.record.purpose,
            warning_short=warning_short,
        )

    def generate_fallback(self) -> str:
        return (
            "I could not confidently identify this medication. "
            "Please verify with a doctor, pharmacist, or caregiver before taking it."
        )

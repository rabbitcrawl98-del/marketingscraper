"""Engine package: Plagiarism guard, Golden Examples, and LangGraph Pod."""
from src.engine.plagiarism_guard import (
    PlagiarismAndFingerprintGuard,
    VerifiedHumanEmail,
    compute_flesch_kincaid_grade,
    count_syllables_pure_python,
    BANNED_AI_SLOP_PHRASES,
)

__all__ = [
    "PlagiarismAndFingerprintGuard",
    "VerifiedHumanEmail",
    "compute_flesch_kincaid_grade",
    "count_syllables_pure_python",
    "BANNED_AI_SLOP_PHRASES",
]


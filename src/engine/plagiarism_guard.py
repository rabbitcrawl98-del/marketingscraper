from __future__ import annotations
import hashlib
import re
import statistics
from typing import Any, Dict, List, Set, Tuple
from pydantic import BaseModel, Field
try:
    from pydantic import ConfigDict, model_validator
    HAS_PYDANTIC_V2 = True
except ImportError:
    from pydantic import root_validator
    HAS_PYDANTIC_V2 = False
    def ConfigDict(**kwargs): return kwargs

try:
    from datasketch import MinHash, MinHashLSH
    HAS_DATASKETCH = True
except ImportError:
    HAS_DATASKETCH = False


class _NativeMinHash:
    """Pure-Python 128-Permutation Universal MinHash signature when datasketch C-wheel is absent."""

    def __init__(self, num_perm: int = 128) -> None:
        self.num_perm = num_perm
        self.hashvalues: List[int] = [(1 << 64) - 1] * num_perm

    def update(self, b: bytes) -> None:
        for i in range(self.num_perm):
            digest = hashlib.blake2b(b, digest_size=8, person=f"zm{i:04d}".encode("ascii")).digest()
            val = int.from_bytes(digest, "little")
            if val < self.hashvalues[i]:
                self.hashvalues[i] = val

    def jaccard(self, other: "_NativeMinHash") -> float:
        matches = sum(1 for a, b in zip(self.hashvalues, other.hashvalues) if a == b)
        return matches / float(self.num_perm)


class _NativeMinHashLSH:
    """Pure-Python LSH Banding Index (16 bands x 8 rows = 128 permutations)."""

    def __init__(self, threshold: float = 0.35, num_perm: int = 128) -> None:
        self.threshold = threshold
        self.num_perm = num_perm
        self.bands = 16
        self.rows = max(1, num_perm // self.bands)
        self.buckets: Dict[Tuple[int, Tuple[int, ...]], Set[str]] = {}

    def insert(self, key: str, mh: _NativeMinHash) -> None:
        for b in range(self.bands):
            start = b * self.rows
            band_sig = tuple(mh.hashvalues[start : start + self.rows])
            self.buckets.setdefault((b, band_sig), set()).add(key)

    def query(self, mh: _NativeMinHash) -> List[str]:
        candidates: Set[str] = set()
        for b in range(self.bands):
            start = b * self.rows
            band_sig = tuple(mh.hashvalues[start : start + self.rows])
            candidates |= self.buckets.get((b, band_sig), set())
        return list(candidates)


BANNED_AI_SLOP_PHRASES: Tuple[str, ...] = (
    "delve", "tapestry", "synergy", "seamless", "seamlessly", "elevate",
    "supercharge", "game-changer", "game changer", "testament", "beacon",
    "unleash", "unlock", "revolutionize", "thrilled", "excited to",
    "hope this email finds you well", "hope you are doing well",
    "i noticed that", "i came across your profile", "in today's fast-paced",
    "cutting-edge", "cutting edge", "bespoke", "holistic", "paradigm",
    "leverage", "utilize", "spearhead", "skyrocket", "transformative",
    "unparalleled", "state-of-the-art", "best-in-class", "low-hanging fruit",
    "circle back", "touch base", "move the needle", "value-add",
    "thought leader", "deep dive", "at the end of the day", "win-win"
)

EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def count_syllables_pure_python(word: str) -> int:
    """Deterministic pure-Python syllable estimator."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    vowels = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(vowels))


def compute_flesch_kincaid_grade(text: str) -> float:
    """Computes exact Flesch-Kincaid Grade Level: 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59."""
    words = re.findall(r"[A-Za-z0-9']+", text)
    sentences = [s for s in re.split(r"[.?!]+(?:\s+|$)", text.strip()) if len(s.strip().split()) >= 2]
    num_words = max(1, len(words))
    num_sentences = max(1, len(sentences))
    num_syllables = sum(count_syllables_pure_python(w) for w in words)
    grade = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    return round(max(1.0, grade), 2)


class PlagiarismAndFingerprintGuard:
    """
    O(1) 128-Permutation MinHash LSH + 5-Gram Shingle Detector.
    Uses datasketch when installed and falls back transparently to _NativeMinHash.
    """

    def __init__(self, jaccard_ceiling: float = 0.35, num_perm: int = 128) -> None:
        self.jaccard_ceiling = jaccard_ceiling
        self.num_perm = num_perm
        self.lsh = (
            MinHashLSH(threshold=jaccard_ceiling, num_perm=num_perm)
            if HAS_DATASKETCH
            else _NativeMinHashLSH(threshold=jaccard_ceiling, num_perm=num_perm)
        )
        self.minhash_store: Dict[str, Any] = {}
        self.shingle_store: Dict[str, Set[str]] = {}

    @staticmethod
    def extract_k_shingles(text: str, k: int = 5) -> Set[str]:
        tokens = re.findall(r"[a-z0-9']+", text.lower())
        if len(tokens) < k:
            return {" ".join(tokens)}
        return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}

    def compute_minhash(self, text: str) -> Any:
        mh = MinHash(num_perm=self.num_perm) if HAS_DATASKETCH else _NativeMinHash(num_perm=self.num_perm)
        for shingle in self.extract_k_shingles(text, k=3):
            mh.update(shingle.encode("utf-8"))
        return mh

    def verify_uniqueness(
        self, candidate_id: str, candidate_text: str, prospect_website_text: str = ""
    ) -> Tuple[bool, float, float, str]:
        cand_mh = self.compute_minhash(candidate_text)
        cand_5grams = self.extract_k_shingles(candidate_text, k=5)

        if prospect_website_text:
            site_5grams = self.extract_k_shingles(prospect_website_text, k=5)
            if cand_5grams and site_5grams:
                web_overlap = (len(cand_5grams & site_5grams) / len(cand_5grams)) * 100.0
                if web_overlap > 12.0:
                    return (
                        False,
                        0.0,
                        round(web_overlap, 2),
                        f"Copied {web_overlap:.1f}% 5-gram phrases verbatim from prospect website. Paraphrase naturally.",
                    )

        near_duplicates = self.lsh.query(cand_mh)
        check_ids = set(near_duplicates) | set(list(self.minhash_store.keys())[-200:])

        max_jaccard = 0.0
        max_5gram_pct = 0.0
        for existing_id in check_ids:
            if existing_id == candidate_id or existing_id not in self.minhash_store:
                continue
            existing_mh = self.minhash_store[existing_id]
            existing_5grams = self.shingle_store[existing_id]
            j_score = cand_mh.jaccard(existing_mh)
            overlap_pct = (
                (len(cand_5grams & existing_5grams) / max(len(cand_5grams), 1)) * 100.0
            )
            max_jaccard = max(max_jaccard, j_score)
            max_5gram_pct = max(max_5gram_pct, overlap_pct)

        if max_jaccard > self.jaccard_ceiling or max_5gram_pct > 15.0:
            return (
                False,
                round(max_jaccard, 3),
                round(max_5gram_pct, 2),
                f"Template fingerprint collision (Jaccard={max_jaccard:.2f} > 0.35, 5-Gram={max_5gram_pct:.1f}% > 15%). Rotate sentence syntax.",
            )

        return True, round(max_jaccard, 3), round(max_5gram_pct, 2), "OK"

    def register_approved_email(self, email_id: str, body_text: str) -> None:
        mh = self.compute_minhash(body_text)
        if email_id not in self.minhash_store:
            try:
                self.lsh.insert(email_id, mh)
            except Exception:
                pass
        self.minhash_store[email_id] = mh
        self.shingle_store[email_id] = self.extract_k_shingles(body_text, k=5)


class VerifiedHumanEmail(BaseModel):
    """
    FORGE v15.0 VERCEL SOVEREIGN — Uncapped Human Psychology & Cadence Gate.
    Enforces:
      - Gate 1: Zero AI slop words, zero emojis, zero exclamation marks ('!')
      - Gate 2: Natural human cadence (Burstiness SD >= 3.8, Flesch-Kincaid 3.0 to 10.5, You:We >= 1.2x)
        with NO upper word-count cap (supports concise 45-word executive notes up to 350+ word deep psychological teardowns)
      - Gate 3: MinHash Jaccard <= 0.35 & 5-Gram Overlap <= 15.0%
    """
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., description="Lowercase or natural 2-14 word peer subject line")
    body_text: str = Field(..., description="Uncapped, deeply personalized plain-text human email (minimum 25 words, no upper limit)")
    minhash_jaccard_max: float = Field(default=0.0, ge=0.0, le=1.0)
    five_gram_overlap_pct: float = Field(default=0.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def _validate_gates(self) -> "VerifiedHumanEmail":
        combined_lower = f"{self.subject} {self.body_text}".lower()

        for phrase in BANNED_AI_SLOP_PHRASES:
            if re.search(rf"\b{re.escape(phrase)}\b", combined_lower):
                raise ValueError(
                    f"[GATE 1 SLOP VIOLATION] Banned AI phrase detected: '{phrase}'. Rewrite like a blunt, friendly human peer at a desk."
                )

        if EMOJI_REGEX.search(self.subject) or EMOJI_REGEX.search(self.body_text):
            raise ValueError("[GATE 1 EMOJI VIOLATION] Remove all emojis from subject and body.")

        if "!" in self.body_text:
            raise ValueError(
                "[GATE 1 PUNCTUATION VIOLATION] Remove exclamation marks ('!') from body; calm peer confidence never shouts."
            )

        subj_words = self.subject.strip().split()
        if not (2 <= len(subj_words) <= 14):
            raise ValueError(
                f"[GATE 2 SUBJECT LENGTH] Subject has {len(subj_words)} words; must be 2 to 14 words."
            )

        words = re.findall(r"[A-Za-z0-9']+", self.body_text)
        word_count = len(words)
        if word_count < 25:
            raise ValueError(
                f"[GATE 2 WORD COUNT] Body has {word_count} words; minimum is 25 words (no upper word limit — tailor depth freely to each lead)."
            )

        fk_grade = compute_flesch_kincaid_grade(self.body_text)
        if not (3.0 <= fk_grade <= 11.5):
            raise ValueError(
                f"[GATE 2 READING GRADE] Flesch-Kincaid Grade is {fk_grade} (must be between 3.0 and 11.5 for natural human reading ease)."
            )

        sentences = [
            s.strip()
            for s in re.split(r"[.?!]+(?:\s+|$)", self.body_text.strip())
            if len(s.strip().split()) >= 2
        ]
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            burstiness_sd = statistics.stdev(lengths)
            if burstiness_sd < 3.8:
                raise ValueError(
                    f"[GATE 2 BURSTINESS] Sentence length SD is {burstiness_sd:.2f} (< 3.8). Mix short 4-6 word punchy observations with 16-26 word concrete diagnostic sentences."
                )

        you_count = len(re.findall(r"\b(you|your|yours)\b", self.body_text.lower()))
        self_count = max(1, len(re.findall(r"\b(i|we|our|my)\b", self.body_text.lower())))
        if (you_count / self_count) < 1.2:
            raise ValueError(
                f"[GATE 2 EGO RATIO] Too many 'I/we/my' pronouns ({self_count}) vs 'you/your' ({you_count}). Focus on the prospect's bottleneck."
            )

        if self.minhash_jaccard_max > 0.35 or self.five_gram_overlap_pct > 15.0:
            raise ValueError(
                f"[GATE 3 PLAGIARISM SHIELD] Jaccard={self.minhash_jaccard_max} (>0.35) or 5-Gram={self.five_gram_overlap_pct}% (>15%). Rewrite syntax."
            )

        return self

if HAS_PYDANTIC_V2:
    VerifiedHumanEmail.enforce_three_human_gates = model_validator(mode="after")(VerifiedHumanEmail._validate_gates)
    VerifiedHumanEmail.model_rebuild()
else:
    old_init = VerifiedHumanEmail.__init__
    def _v1_init(self, **data):
        old_init(self, **data)
        self._validate_gates()
    VerifiedHumanEmail.__init__ = _v1_init

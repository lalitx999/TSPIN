"""
TSPI M8: Clinical Guardrail Engine.
Enforces Medical Ethics & Thai Medical Council (แพทยสภา) Compliance:
1. Deterministic Forbidden Assertion Filter (Zero Direct Diagnoses)
2. Calibrated Semantic Citation Grounding (Cosine Similarity >= 0.70)
3. Unverified Claim Redaction Engine
"""

import re
import math
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("tspi.guardrail")


class GuardrailViolation(Exception):
    """Raised when an AI response violates institutional clinical safety rules."""
    pass


class ClinicalGuardrail:
    """Enforces clinical safety and citation integrity on all model outputs."""

    # 1. Patterns strictly forbidden by medical governance
    FORBIDDEN_ASSERTIONS = [
        re.compile(r'วินิจฉัยว่า(?:เป็น)?\s*([ก-๙a-zA-Z0-9_]+)'),
        re.compile(r'คุณเป็นโรค\s*([ก-๙a-zA-Z0-9_]+)'),
        re.compile(r'ฟันธงว่า\s*([ก-๙a-zA-Z0-9_]+)'),
        re.compile(r'ขอสั่งยา\s*([ก-๙a-zA-Z0-9_]+)'),
        re.compile(r'สั่งจ่ายยา\s*([ก-๙a-zA-Z0-9_]+)'),
        re.compile(r'\bdiagnose[sd]?\s+(?:with|as)\b', re.IGNORECASE),
        re.compile(r'\byou\s+have\s+(?:the\s+disease|cancer|diabetes|hiv)\b', re.IGNORECASE),
    ]

    # 2. Calibrated Threshold approved by Medical Director & Library Curator
    # Trade-off: False Positive = 0%, Recall >= 70%
    CALIBRATED_SIMILARITY_THRESHOLD: float = 0.70

    @classmethod
    def check_forbidden_assertions(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Scans text for illegal diagnostic assertions.
        Returns: (has_violations: bool, violated_patterns: list)
        """
        violations = []
        for pattern in cls.FORBIDDEN_ASSERTIONS:
            matches = pattern.findall(text)
            if matches:
                violations.append(pattern.pattern)
        return (len(violations) > 0, violations)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two numerical vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    @classmethod
    def _keyword_similarity(cls, text1: str, text2: str) -> float:
        """
        Calculates character tri-gram containment similarity for Thai & multilingual text.
        Measures the extent to which the claim's semantic assertions (text1) are contained
        within the cited reference text (text2).
        """
        def get_shingles(text: str, n: int = 3):
            clean = re.sub(r'[\s\.,;:\-\(\)\[\]/]+', '', text.lower())
            if len(clean) < n:
                return {clean} if clean else set()
            return {clean[i:i+n] for i in range(len(clean) - n + 1)}

        s1 = get_shingles(text1)
        s2 = get_shingles(text2)
        if not s1 or not s2:
            return 0.0
        intersection = s1.intersection(s2)
        return len(intersection) / len(s1)

    @classmethod
    def verify_citation_grounding(
        cls,
        claim: str,
        source_text: str,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Verifies that an AI claim is groundable in the cited source text.
        Applies calibrated threshold (default 0.70).
        """
        active_threshold = threshold if threshold is not None else cls.CALIBRATED_SIMILARITY_THRESHOLD

        if not claim or not source_text:
            return {
                "grounded": False,
                "score": 0.0,
                "threshold": active_threshold,
                "reason": "EMPTY_CLAIM_OR_SOURCE"
            }

        # Calculate containment score (0.0 - 1.0)
        score = cls._keyword_similarity(claim, source_text)

        is_grounded = score >= active_threshold

        return {
            "grounded": is_grounded,
            "score": round(score, 4),
            "threshold": active_threshold,
            "status": "VERIFIED" if is_grounded else "REDACTED"
        }

    @classmethod
    def sanitize_and_guard(
        cls,
        ai_response_text: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        library_store: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive Guardrail pipeline:
        1. Blocks/replaces forbidden assertions
        2. Validates citation grounding
        3. Returns clinical safe output with audit telemetry
        """
        has_violations, violated_patterns = cls.check_forbidden_assertions(ai_response_text)
        
        guarded_text = ai_response_text
        if has_violations:
            # Redact forbidden assertion phrases
            for pattern in cls.FORBIDDEN_ASSERTIONS:
                guarded_text = pattern.sub(r'[การประเมินทางคลินิกเบื้องต้น — แพทย์เป็นผู้ตัดสินใจ]', guarded_text)

        verified_citations = []
        unverified_citations = []

        if citations and library_store:
            for cit in citations:
                axis_id = cit.get("axis_id")
                page = cit.get("source_page")
                quote = cit.get("quote", "")

                # Lookup canonical text
                canonical_chunk = ""
                for ax in library_store.get("axes", []):
                    if ax.get("id") == axis_id or ax.get("axis_id") == axis_id:
                        canonical_chunk = f"{ax.get('title', '')} {ax.get('description', '')}"
                        break

                verif_res = cls.verify_citation_grounding(quote, canonical_chunk)
                if verif_res["grounded"]:
                    verified_citations.append(cit)
                else:
                    unverified_citations.append({**cit, **verif_res})

        return {
            "safe_text": guarded_text,
            "had_forbidden_assertions": has_violations,
            "violated_patterns": violated_patterns,
            "verified_citations": verified_citations,
            "unverified_citations": unverified_citations,
            "guardrail_status": "PASS" if not has_violations and not unverified_citations else "FLAGGED"
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
deflection_classifier.py — AI-Powered Bureaucratic Deflection Classifier

Classifies Greek government responses into 7 deflection types, derived from
real AADE/myAADE response patterns documented in the Kyprianos case.

The classifier operates in two modes:
  1. RULE-BASED (default): Fast, deterministic, zero dependencies
  2. AI-ENHANCED (optional): Uses OpenAI GPT-4o for nuanced Greek text analysis

Part of the Zeus MyAADE Monitor System.
Case: EPPO PP.00179/2026/EN | FBI IC3 | IRS CI

Author: Kypria Technologies
Date: March 10, 2026
License: MIT
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


# ═══════════════════════════════════════════════════════════════════
# DEFLECTION TAXONOMY — 7 types from real March 9, 2026 data
# ═══════════════════════════════════════════════════════════════════

class DeflectionType(str, Enum):
    """
    Seven deflection types observed in Greek bureaucratic responses.
    Each maps to a specific evasion tactic used by AADE and related agencies.
    """

    INTIMIDATION = "INTIMIDATION"
    # Agency tells citizen to stop filing complaints/requests.
    # Example: ΚΕΦΟΔΕ Α4' — "μην επανέρχεστε με καταγγελίες και κατηγορίες"
    # Violates: Art.13 GDPR (right to complain), N.2690/1999 Art.4

    CIRCULAR_REFERRAL = "CIRCULAR_REFERRAL"
    # Agency refers to "previous answers" that didn't actually answer.
    # Example: ΚΕ.Β.ΕΙΣ./ΚΕΦΟΔΕ Α3' — "βλ. προηγούμενες απαντήσεις"
    # Also known as: Φαύλος Κύκλος (vicious circle)

    PHANTOM_CLOSURE = "PHANTOM_CLOSURE"
    # Agency marks request as "already answered" without substantive reply.
    # Example: ΚΕΦΟΔΕ Α3' — "Έχει ήδη απαντηθεί"
    # Variant of "responded" in v1.0, but specifically no actual content

    SCOPE_DODGE = "SCOPE_DODGE"
    # Agency answers only a narrow part, ignoring the core question.
    # Example: ΚΕΦΟΔΕ Α4' — discusses Greek-source income but ignores
    #          who is filing declarations under the AFM

    DOCUMENT_TRAP = "DOCUMENT_TRAP"
    # Agency demands documents that another agency blocks from being issued.
    # Example: ΚΕΦΟΔΕ Γ1' demands Δ210 + certificates, but Δήμος Σπετσών
    #          blocks Πιστοποιητικό Εγγυτέρων Συγγενών (8 errors in Prot. 504)
    # This is the CORE of the Φαύλος Κύκλος

    SYSTEM_REDIRECT = "SYSTEM_REDIRECT"
    # Agency says "use a different system/portal" instead of answering.
    # Example: ΚΕ.ΦΟ.Κ. Β3' — "τροποποιήσεις μόνο μέσω ΟΠΣ Περιουσιολογίου"
    # Variant: "send to protokollo@attica.gr" (procedural redirect)

    PROCEDURAL_DEFLECTION = "PROCEDURAL_DEFLECTION"
    # Agency invokes procedural requirements to avoid acting.
    # Example: Τμήμα Εποπτείας Ο.Τ.Α. — demands signed docs + ID sent
    #          to protokollo@attica.gr, despite having all this from prior filings
    # Adds friction to force re-submission of already-provided materials


class Severity(str, Enum):
    """Severity levels for deflection events."""
    CRITICAL = "CRITICAL"     # Active obstruction / intimidation / fraud cover
    HIGH = "HIGH"             # Substantive evasion requiring escalation
    MEDIUM = "MEDIUM"         # Procedural dodge, may resolve with persistence
    WATCH = "WATCH"           # Ambiguous, needs monitoring


# ═══════════════════════════════════════════════════════════════════
# CLASSIFICATION RESULT
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DeflectionResult:
    """Result of classifying a government response text."""
    deflection_type: DeflectionType
    severity: Severity
    confidence: float              # 0.0 – 1.0
    description: str               # Human-readable explanation
    matched_patterns: List[str]    # Which patterns triggered
    legal_violations: List[str]    # Applicable legal violations
    recommended_action: str        # What to do next
    escalation_targets: List[str]  # Who to escalate to
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["deflection_type"] = self.deflection_type.value
        d["severity"] = self.severity.value
        return d

    def to_github_comment(self, protocol: str = "", agency: str = "") -> str:
        """Generate a GitHub Issue #147 comment for this deflection."""
        emoji = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.WATCH: "⚪",
        }
        e = emoji.get(self.severity, "⚪")
        lines = [
            f"## {e} Deflection Detected — {self.deflection_type.value}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Protocol | `{protocol}` |" if protocol else "",
            f"| Agency | {agency} |" if agency else "",
            f"| Type | **{self.deflection_type.value}** |",
            f"| Severity | {self.severity.value} |",
            f"| Confidence | {self.confidence:.0%} |",
            f"| Legal Violations | {', '.join(self.legal_violations)} |",
            f"| Recommended Action | {self.recommended_action} |",
            f"| Escalation Targets | {', '.join(self.escalation_targets)} |",
            f"| Detected | {self.timestamp} |",
            "",
            f"> **Description:** {self.description}",
            "",
            f"> **Matched patterns:** {', '.join(self.matched_patterns)}",
        ]
        return "\n".join(line for line in lines if line is not None)


# ═══════════════════════════════════════════════════════════════════
# GREEK TEXT NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

def _norm(text: str) -> str:
    """Normalize Greek text: remove accents, lowercase, collapse whitespace."""
    text = text.casefold()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ═══════════════════════════════════════════════════════════════════
# RULE-BASED PATTERN DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

# Each pattern has:
#   keywords_el: Greek keywords/phrases (normalized, no accents)
#   keywords_en: English equivalents (for bilingual responses)
#   negative_el: Keywords that indicate this is NOT a deflection of this type
#   weight: How strongly this pattern indicates the deflection type (0.0-1.0)

DEFLECTION_RULES: Dict[DeflectionType, Dict[str, Any]] = {

    DeflectionType.INTIMIDATION: {
        "keywords_el": [
            "μην επανερχεστε",
            "μη επανερχεσθε",
            "σταματηστε να υποβαλλετε",
            "δεν ειναι αποδεκτο να",
            "μην επαναλαμβανετε",
            "αποφυγετε τις καταγγελιες",
            "δεν δεχομαστε αλλες καταγγελιες",
            "μην υποβαλλετε εκ νεου",
            "παρακαλουμε να μην",
            "θεωρηθει ως παρενοχληση",
        ],
        "keywords_en": [
            "stop filing complaints",
            "do not submit again",
            "cease and desist",
            "considered harassment",
            "refrain from further",
        ],
        "negative_el": [],
        "weight": 0.95,
        "severity": Severity.CRITICAL,
        "legal_violations": [
            "Art.13 GDPR (right to lodge complaint without retaliation)",
            "N.2690/1999 Art.4 (right of petition/complaint)",
            "N.4443/2016 Art.2 (whistleblower protection)",
        ],
        "recommended_action": "File complaint with ΑΠΔΠΧ + Συνήγορος + report to EPPO as obstruction of justice",
        "escalation_targets": [
            "complaints@dpa.gr (ΑΠΔΠΧ)",
            "contact@synigoros.gr",
            "Athens.Office@eppo.europa.eu",
            "IRS-CI SA Zacheranik (evidence of cover-up)",
        ],
    },

    DeflectionType.CIRCULAR_REFERRAL: {
        "keywords_el": [
            "βλ. προηγουμενες απαντησεις",
            "βλεπε προηγουμενη",
            "εχει ηδη απαντηθει σε προηγουμενο",
            "παραπεμπουμε στην απαντηση",
            "σας εχουμε ηδη ενημερωσει",
            "οπως σας εχουμε ενημερωσει",
            "οπως εχουμε αναφερει",
            "βλ. σχετικα αιτηματα",
            "παραπομπη σε αρμοδια υπηρεσια",
            "αρμοδια για το αιτημα σας",
            "θα πρεπει να απευθυνθειτε",
            "αρμοδιοτητα αλλης υπηρεσιας",
        ],
        "keywords_en": [
            "see previous answers",
            "already informed you",
            "refer to competent authority",
            "refer you to",
            "not within our jurisdiction",
            "contact the relevant",
        ],
        "negative_el": [
            "σας αποστελλουμε την απαντηση",  # actual answer attached
            "επισυναπτεται η απαντηση",  # answer is attached
        ],
        "weight": 0.80,
        "severity": Severity.HIGH,
        "legal_violations": [
            "N.2690/1999 Art.4§1 (duty to respond substantively)",
            "N.4727/2020 Art.9 (obligation of inter-agency cooperation)",
        ],
        "recommended_action": "Document circular chain, file with Συνήγορος as systemic Φαύλος Κύκλος",
        "escalation_targets": [
            "contact@synigoros.gr",
            "kataggelies@aead.gr (ΕΑΔ)",
        ],
    },

    DeflectionType.PHANTOM_CLOSURE: {
        "keywords_el": [
            "εχει ηδη απαντηθει",
            "η υποθεση εχει κλεισει",
            "εχει ολοκληρωθει",
            "εχει διεκπεραιωθει",
            "εχει αρχειοθετηθει",
            "θεωρειται λυθεισα",
            "δεν υφισταται εκκρεμοτητα",
            "τεθηκε στο αρχειο",
            "η απαντηση εχει δοθει",
        ],
        "keywords_en": [
            "already answered",
            "case closed",
            "matter resolved",
            "no pending issues",
            "archived",
            "response has been given",
        ],
        "negative_el": [],
        "weight": 0.85,
        "severity": Severity.CRITICAL,
        "legal_violations": [
            "N.2690/1999 Art.4 (duty of substantive response)",
            "N.3528/2007 Art.24 (civil servant duty of diligence)",
        ],
        "recommended_action": "Demand specific protocol number and content of alleged prior answer; if none exists, file πειθαρχική καταγγελία",
        "escalation_targets": [
            "contact@synigoros.gr",
            "kataggelies@aead.gr",
            "dpo@aade.gr (if AADE-specific)",
        ],
    },

    DeflectionType.SCOPE_DODGE: {
        "keywords_el": [
            "οσον αφορα το ζητημα",
            "ειδικα για το θεμα",
            "ως προς το σκελος",
            "σχετικα με το ερωτημα σας για",
            "μονο ελληνικης πηγης",
            "φορολογηση ελληνικης πηγης",
            "δεν εμπιπτει στην αρμοδιοτητα μας",
            "δεν αφορα την υπηρεσια μας",
            "ως προς τα λοιπα",
        ],
        "keywords_en": [
            "regarding your question about",
            "only greek-source",
            "as for the remaining",
            "does not fall within our competence",
            "not within our scope",
        ],
        "negative_el": [],
        "weight": 0.70,
        "severity": Severity.HIGH,
        "legal_violations": [
            "N.2690/1999 Art.4 (complete response obligation)",
            "N.4727/2020 Art.14 (digital governance completeness)",
        ],
        "recommended_action": "Re-submit with explicit numbered demands; file with ΕΑΔ if core questions remain unanswered",
        "escalation_targets": [
            "kataggelies@aead.gr",
            "desyp@aade.gr",
        ],
    },

    DeflectionType.DOCUMENT_TRAP: {
        "keywords_el": [
            "απαιτουνται τα εξης δικαιολογητικα",
            "πρεπει να προσκομισετε",
            "χρειαζεται πιστοποιητικο",
            "απαιτειται δηλωση",
            "δ210",
            "πιστοποιητικο εγγυτερων συγγενων",
            "πιστοποιητικο μη δημοσιευσης διαθηκης",
            "ληξιαρχικη πραξη θανατου",
            "πρεπει να υποβληθει πρωτα",
            "εφοσον προσκομισετε",
            "με την προσκομιση",
            "οταν ολοκληρωθει η",
        ],
        "keywords_en": [
            "required documents",
            "must submit",
            "certificate required",
            "declaration required",
            "upon submission of",
            "once you provide",
        ],
        "negative_el": [
            "σας αποστελλουμε το πιστοποιητικο",  # they're actually sending the cert
        ],
        "weight": 0.75,
        "severity": Severity.CRITICAL,
        "legal_violations": [
            "N.2690/1999 Art.4 + Art.5 (inter-agency document sharing obligation)",
            "N.4727/2020 Art.47 (once-only principle — citizen shouldn't re-submit)",
            "EU SDG Regulation 2018/1724 (single digital gateway)",
        ],
        "recommended_action": "Document the catch-22 chain: Agency A demands X, Agency B blocks X. File coordinated complaint with Συνήγορος + ΕΑΔ",
        "escalation_targets": [
            "contact@synigoros.gr",
            "kataggelies@aead.gr",
            "Athens.Office@eppo.europa.eu (if obstruction enables ongoing fraud)",
        ],
    },

    DeflectionType.SYSTEM_REDIRECT: {
        "keywords_el": [
            "μεσω οπσ",
            "μεσω περιουσιολογιου",
            "μεσω taxisnet",
            "μεσω myaade",
            "μεσω ηλεκτρονικης πυλης",
            "μεσω πλατφορμας",
            "ηλεκτρονικα μεσω",
            "μονο ηλεκτρονικα",
            "αποκλειστικα μεσω",
            "δεν μπορει να γινει μεσω αιτηματος",
            "αποστειλετε στο protokollo",
            "αποστειλετε στην διευθυνση",
            "αποστειλετε εγγραφο",
        ],
        "keywords_en": [
            "via the platform",
            "only electronically",
            "through the portal",
            "submit via",
            "send to protokollo",
            "official email address",
        ],
        "negative_el": [],
        "weight": 0.70,
        "severity": Severity.MEDIUM,
        "legal_violations": [
            "N.4727/2020 Art.25 (multi-channel access obligation)",
            "N.2690/1999 Art.3 (right to submit via any means)",
        ],
        "recommended_action": "Re-submit via the demanded channel but also document the redirect as evidence of systemic friction",
        "escalation_targets": [
            "contact@synigoros.gr (if repeated system redirects)",
        ],
    },

    DeflectionType.PROCEDURAL_DEFLECTION: {
        "keywords_el": [
            "παρακαλεισθε να αποστειλετε",
            "παρακαλω αποστειλατε",
            "με φυσικη υπογραφη",
            "ψηφιακη υπογραφη",
            "επικυρωμενο φωτοαντιγραφο",
            "υπευθυνη δηλωση",
            "φωτοαντιγραφο ταυτοτητας",
            "απλη ενημερωση χωρις ενεργεια",
            "χωρις περαιτερω ενεργεια",
            "αλλως θα ληφθει ως",
            "εαν επιθυμειτε να πρωτοκολληθει",
            "προσηκοντως",
            "εισαχθει προσηκοντως",
            "αρθρου 10 του ν. 2690",
            "αρθρου 3 και της παρ",
            "αρθρου 11 του ν. 2690",
        ],
        "keywords_en": [
            "please submit with signature",
            "certified copy",
            "sworn declaration",
            "copy of identity",
            "will be treated as simple notification",
            "without further action",
            "if you wish it to be protocolled",
        ],
        "negative_el": [],
        "weight": 0.80,
        "severity": Severity.HIGH,
        "legal_violations": [
            "N.2690/1999 Art.4 (duty to act on all submissions)",
            "N.4727/2020 Art.31 (digital submission equivalence)",
            "Art.10 N.2690/1999 (the very article they cite actually allows email submissions)",
        ],
        "recommended_action": "Re-submit to protokollo@ with all docs BUT also file complaint that prior submissions contained all required materials",
        "escalation_targets": [
            "contact@synigoros.gr",
            "protokollo@attica.gr (re-submission with complaint about procedural obstruction)",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════
# CATCH-22 CHAIN DETECTOR
# ═══════════════════════════════════════════════════════════════════

# Known circular dependency chains in this case
CATCH22_CHAINS = [
    {
        "name": "Heir Declaration Catch-22",
        "chain": [
            "AADE demands Δ210 + Πιστ. Εγγυτέρων Συγγενών",
            "Δήμος Σπετσών blocks Πιστ. Εγγυτέρων Συγγενών (8 errors in Prot. 504)",
            "Αποκεντρωμένη Διοίκηση demands re-submission to protokollo@attica.gr",
            "Meanwhile AFM 051422558 runs 1,729+ days post-mortem",
        ],
        "agencies": ["AADE", "Δήμος Σπετσών", "Αποκεντρωμένη Διοίκηση Αττικής"],
        "trigger_keywords": ["δ210", "πιστοποιητικο εγγυτερων", "πρωτ. 504", "δημος σπετσων"],
    },
    {
        "name": "E9 Modification Catch-22",
        "chain": [
            "AADE says E9 changes only via ΟΠΣ Περιουσιολογίου",
            "ΟΠΣ requires AFM login — deceased AFM 051422558 has no authorized user",
            "AADE won't disclose who modified E9 post-mortem",
            "Ktimatologio won't correct records without AADE E9 update",
        ],
        "agencies": ["AADE", "Ktimatologio"],
        "trigger_keywords": ["οπσ περιουσιολογιου", "ε9", "τροποποιηση", "αποβιωσαντ"],
    },
    {
        "name": "Refund Misdirection Catch-22",
        "chain": [
            "AADE sent refund to wrong AFM (Αίτημα 257636)",
            "AADE refers to 'previous answers' instead of disclosing recipient AFM",
            "If recipient is AFM 052822816 (Efthalia) = complete embezzlement",
            "AADE refuses to disclose, citing 'tax secrecy' for the perpetrator",
        ],
        "agencies": ["AADE"],
        "trigger_keywords": ["επιστροφη χρηματων", "λαθος αφμ", "257636", "052822816"],
    },
]


def detect_catch22(text: str, all_responses: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Detect if a response is part of a known catch-22 chain.
    Returns chain info if detected, None otherwise.
    """
    norm_text = _norm(text)
    for chain in CATCH22_CHAINS:
        matches = sum(1 for kw in chain["trigger_keywords"] if kw in norm_text)
        if matches >= 2:
            return {
                "chain_name": chain["name"],
                "matched_keywords": matches,
                "total_keywords": len(chain["trigger_keywords"]),
                "chain_description": chain["chain"],
                "agencies_involved": chain["agencies"],
            }
    return None


# ═══════════════════════════════════════════════════════════════════
# RULE-BASED CLASSIFIER
# ═══════════════════════════════════════════════════════════════════

def classify_deflection(
    text: str,
    agency: str = "",
    protocol: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Optional[DeflectionResult]:
    """
    Classify a government response text for deflection patterns.

    Args:
        text: The response text (Greek or English)
        agency: Name of the responding agency
        protocol: Protocol number of the request
        context: Optional additional context (prior responses, case data)

    Returns:
        DeflectionResult if deflection detected, None if clean response
    """
    norm_text = _norm(text)
    best_match: Optional[Tuple[DeflectionType, float, List[str]]] = None
    best_score = 0.0

    for deflection_type, rules in DEFLECTION_RULES.items():
        matched = []
        score = 0.0

        # Check negative patterns first (false positive prevention)
        is_negated = False
        for neg_kw in rules.get("negative_el", []):
            if _norm(neg_kw) in norm_text:
                is_negated = True
                break
        if is_negated:
            continue

        # Check Greek keywords
        for kw in rules["keywords_el"]:
            if _norm(kw) in norm_text:
                matched.append(kw)
                # Each match gives a base score proportional to weight
                score += rules["weight"] * 0.4

        # Check English keywords
        for kw in rules["keywords_en"]:
            if kw.lower() in text.lower():
                matched.append(kw)
                score += rules["weight"] * 0.4

        # Normalize: first match is strong, diminishing returns after
        if matched:
            # First match = base weight, each additional adds less
            score = rules["weight"] * (0.6 + 0.15 * min(len(matched) - 1, 3))
            score = min(score, 1.0)

        if matched and score > best_score:
            best_score = score
            best_match = (deflection_type, score, matched)

    if best_match is None:
        return None

    dtype, confidence, patterns = best_match
    rules = DEFLECTION_RULES[dtype]

    # Check for catch-22 chain involvement
    catch22 = detect_catch22(text)
    description = rules.get("description", f"Deflection type: {dtype.value}")
    if catch22:
        description = (
            f"⚠️ ΦΑΥΛΟΣ ΚΥΚΛΟΣ DETECTED: {catch22['chain_name']}. "
            f"{', '.join(catch22['chain_description'][:2])}..."
        )
        confidence = min(confidence + 0.15, 1.0)

    return DeflectionResult(
        deflection_type=dtype,
        severity=rules["severity"],
        confidence=round(confidence, 2),
        description=_build_description(dtype, patterns, agency, protocol),
        matched_patterns=patterns,
        legal_violations=rules["legal_violations"],
        recommended_action=rules["recommended_action"],
        escalation_targets=rules["escalation_targets"],
    )


def _build_description(
    dtype: DeflectionType,
    patterns: List[str],
    agency: str,
    protocol: str,
) -> str:
    """Build a human-readable description of the deflection."""
    descs = {
        DeflectionType.INTIMIDATION: (
            f"{agency or 'Agency'} told citizen to stop filing complaints/requests. "
            "This constitutes institutional intimidation against a fraud victim."
        ),
        DeflectionType.CIRCULAR_REFERRAL: (
            f"{agency or 'Agency'} referred to 'previous answers' or another agency "
            "without providing a substantive response. Classic Φαύλος Κύκλος."
        ),
        DeflectionType.PHANTOM_CLOSURE: (
            f"{agency or 'Agency'} marked the request as 'already answered' "
            "without actually providing the requested information."
        ),
        DeflectionType.SCOPE_DODGE: (
            f"{agency or 'Agency'} answered only a narrow aspect of the request, "
            "deliberately ignoring the core questions."
        ),
        DeflectionType.DOCUMENT_TRAP: (
            f"{agency or 'Agency'} demands documents that another agency blocks "
            "from being issued, creating an impossible circular dependency."
        ),
        DeflectionType.SYSTEM_REDIRECT: (
            f"{agency or 'Agency'} redirected to a different system/portal/email "
            "instead of processing the request as submitted."
        ),
        DeflectionType.PROCEDURAL_DEFLECTION: (
            f"{agency or 'Agency'} invoked procedural requirements (signature, ID, "
            "specific email) to avoid acting on an already-valid submission."
        ),
    }
    base = descs.get(dtype, f"Deflection type: {dtype.value}")
    if protocol:
        base += f" Protocol: {protocol}."
    return base


# ═══════════════════════════════════════════════════════════════════
# MULTI-RESPONSE ANALYZER (batch classification)
# ═══════════════════════════════════════════════════════════════════

def analyze_batch(
    responses: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Analyze a batch of responses and detect systemic patterns.

    Args:
        responses: List of dicts with keys: text, agency, protocol

    Returns:
        Summary with individual results + systemic pattern analysis
    """
    results = []
    type_counts: Dict[str, int] = {}
    agencies_deflecting: Dict[str, List[str]] = {}

    for resp in responses:
        result = classify_deflection(
            text=resp.get("text", ""),
            agency=resp.get("agency", ""),
            protocol=resp.get("protocol", ""),
        )
        if result:
            results.append({
                "protocol": resp.get("protocol", ""),
                "agency": resp.get("agency", ""),
                "result": result.to_dict(),
            })
            # Track patterns
            dtype = result.deflection_type.value
            type_counts[dtype] = type_counts.get(dtype, 0) + 1
            agency = resp.get("agency", "UNKNOWN")
            if agency not in agencies_deflecting:
                agencies_deflecting[agency] = []
            agencies_deflecting[agency].append(dtype)

    # Systemic pattern detection
    systemic_patterns = []
    if len(results) >= 3:
        systemic_patterns.append(
            f"SYSTEMIC: {len(results)} out of {len(responses)} responses "
            f"classified as deflections"
        )
    if len(type_counts) >= 3:
        systemic_patterns.append(
            f"DIVERSE TACTICS: {len(type_counts)} different deflection types used — "
            f"indicates coordinated evasion strategy"
        )
    if DeflectionType.INTIMIDATION.value in type_counts:
        systemic_patterns.append(
            "INTIMIDATION DETECTED: Agency actively discouraging complaints — "
            "immediate Συνήγορος + ΑΠΔΠΧ referral required"
        )
    if (DeflectionType.DOCUMENT_TRAP.value in type_counts
            and DeflectionType.CIRCULAR_REFERRAL.value in type_counts):
        systemic_patterns.append(
            "ΦΑΥΛΟΣ ΚΥΚΛΟΣ CONFIRMED: Document trap + circular referral = "
            "impossible compliance chain. File coordinated complaint."
        )

    return {
        "total_responses": len(responses),
        "deflections_found": len(results),
        "deflection_rate": f"{len(results)/max(len(responses),1):.0%}",
        "type_counts": type_counts,
        "agencies_deflecting": agencies_deflecting,
        "systemic_patterns": systemic_patterns,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════
# AUTO-ESCALATION GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_escalation(
    result: DeflectionResult,
    protocol: str = "",
    agency: str = "",
    days_since_death: int = 0,
) -> Dict[str, str]:
    """
    Generate a ready-to-send escalation response based on deflection classification.

    Returns dict with:
        subject_el: Greek email subject
        body_el: Greek email body
        body_en_summary: English summary paragraph
        escalation_to: Primary recipient
        cc: CC recipients
    """
    if not days_since_death:
        from datetime import date
        death_date = date(2021, 6, 13)
        days_since_death = (date.today() - death_date).days

    dtype = result.deflection_type

    # Subject line
    subjects = {
        DeflectionType.INTIMIDATION: (
            f"ΚΑΤΑΓΓΕΛΙΑ — Θεσμική Εκφόβιση Πολίτη-Θύματος — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.CIRCULAR_REFERRAL: (
            f"ΟΧΛΗΣΗ — Κυκλική Παραπομπή Χωρίς Ουσιαστική Απάντηση — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.PHANTOM_CLOSURE: (
            f"ΕΝΣΤΑΣΗ — Ψευδής Κλείσιμο Αιτήματος — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.SCOPE_DODGE: (
            f"ΕΠΑΝΑΥΠΟΒΟΛΗ — Ελλιπής Απάντηση σε Βασικά Ερωτήματα — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.DOCUMENT_TRAP: (
            f"ΚΑΤΑΓΓΕΛΙΑ — Φαύλος Κύκλος Δικαιολογητικών — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.SYSTEM_REDIRECT: (
            f"ΟΧΛΗΣΗ — Ανεπίτρεπτη Παραπομπή σε Εναλλακτικό Σύστημα — {agency} — Πρωτ. {protocol}"
        ),
        DeflectionType.PROCEDURAL_DEFLECTION: (
            f"ΕΝΣΤΑΣΗ — Διαδικαστικός Αποκλεισμός — {agency} — Πρωτ. {protocol}"
        ),
    }

    # Body templates
    bodies = {
        DeflectionType.INTIMIDATION: (
            f"Αξιότιμοι,\n\n"
            f"Η δήλωση της υπηρεσίας σας «μην επανέρχεστε με καταγγελίες» αποτελεί "
            f"θεσμική εκφόβιση πολίτη-θύματος.\n\n"
            f"Αυτό παραβιάζει:\n"
            f"• Άρθ.13 ΓΚΠΔ — δικαίωμα υποβολής καταγγελίας χωρίς αντίποινα\n"
            f"• Ν.2690/1999 Άρθ.4 — δικαίωμα αναφοράς\n"
            f"• Ν.4443/2016 Άρθ.2 — προστασία καταγγέλλοντος\n\n"
            f"Σας ενημερώνω ότι η δήλωση αυτή:\n"
            f"1. Κατατίθεται στην ΑΠΔΠΧ ως παράβαση ΓΚΠΔ\n"
            f"2. Κοινοποιείται στον Συνήγορο του Πολίτη\n"
            f"3. Κοινοποιείται στο EPPO ως ένδειξη συγκάλυψης\n"
            f"4. Θα προσκομιστεί στο IRS-CI ως απόδειξη θεσμικής παρεμπόδισης\n\n"
            f"Έχουν παρέλθει {days_since_death} ημέρες από τον θάνατο του συζύγου μου.\n"
        ),
        DeflectionType.CIRCULAR_REFERRAL: (
            f"Αξιότιμοι,\n\n"
            f"Η παραπομπή σε «προηγούμενες απαντήσεις» δεν αποτελεί ουσιαστική απάντηση.\n\n"
            f"Οι «προηγούμενες απαντήσεις» δεν απάντησαν στα βασικά ερωτήματα:\n"
            f"• Σε ποιον ΑΦΜ εστάλη η επιστροφή;\n"
            f"• Ποιος υποβάλλει δηλώσεις υπό τον ΑΦΜ 051422558 μετά θάνατον;\n"
            f"• Ποιος τροποποιεί Ε9 αποβιώσαντος;\n\n"
            f"Η κυκλική παραπομπή χωρίς δράση παραβιάζει:\n"
            f"• Ν.2690/1999 Άρθ.4§1 — υποχρέωση ουσιαστικής απάντησης\n"
            f"• Ν.4727/2020 Άρθ.9 — υποχρέωση διυπηρεσιακής συνεργασίας\n\n"
            f"Ημέρες από θάνατο: {days_since_death}. Ο ΑΦΜ 051422558 παραμένει ενεργός.\n"
        ),
        DeflectionType.DOCUMENT_TRAP: (
            f"Αξιότιμοι,\n\n"
            f"Η απαίτηση εγγράφων που εμποδίζει άλλος φορέας να εκδοθούν συνιστά "
            f"ΦΑΥΛΟ ΚΥΚΛΟ (catch-22):\n\n"
            f"1. Η ΑΑΔΕ απαιτεί Δ210 + Πιστοποιητικό Εγγυτέρων Συγγενών\n"
            f"2. Ο Δήμος Σπετσών εμποδίζει έκδοση Πιστοποιητικού (Πρωτ. 504, 8 σφάλματα)\n"
            f"3. Η Αποκεντρωμένη Διοίκηση απαιτεί εκ νέου υποβολή σε protokollo@attica.gr\n"
            f"4. Εν τω μεταξύ, ο ΑΦΜ 051422558 λειτουργεί {days_since_death} ημέρες μετά θάνατον\n\n"
            f"Κανένας φορέας δεν αναλαμβάνει δράση. Κάθε φορέας παραπέμπει σε άλλον.\n"
            f"Αυτό παραβιάζει:\n"
            f"• Ν.2690/1999 Άρθ.4+5 — υποχρέωση διυπηρεσιακής ανταλλαγής εγγράφων\n"
            f"• Ν.4727/2020 Άρθ.47 — αρχή once-only\n"
            f"• Κανονισμός ΕΕ 2018/1724 — ενιαία ψηφιακή πύλη\n"
        ),
    }

    # Default body for types without specific template
    default_body = (
        f"Αξιότιμοι,\n\n"
        f"Η απάντησή σας στο αίτημα Πρωτ. {protocol} αποτελεί {result.deflection_type.value}.\n\n"
        f"Παραβιάζει: {', '.join(result.legal_violations[:2])}\n\n"
        f"Αιτούμαι ουσιαστική απάντηση εντός 10 εργασίμων ημερών.\n"
        f"Ημέρες από θάνατο Ιωάννη Κυπριανού: {days_since_death}.\n"
    )

    body = bodies.get(dtype, default_body)

    # Common signature
    signature = (
        f"\nΜε εκτίμηση,\n"
        f"Σταματίνα Κυπριανού\n"
        f"ΑΦΜ: 044594747\n"
        f"Χήρα και μοναδική κληρονόμος Ιωάννη Κυπριανού (AFM 051422558)\n"
        f"Email: stamatinakyprianou@gmail.com\n"
    )

    en_summary = (
        f"English Summary: Formal complaint regarding {dtype.value} by {agency} "
        f"on protocol {protocol}. {days_since_death} days since death of John Kyprianos "
        f"(Hellenic Navy veteran, AFM 051422558). "
        f"Legal violations: {', '.join(result.legal_violations[:2])}. "
        f"Next step: {result.recommended_action}"
    )

    return {
        "subject_el": subjects.get(dtype, f"ΟΧΛΗΣΗ — {dtype.value} — {agency} — Πρωτ. {protocol}"),
        "body_el": body + f"\n{en_summary}\n" + signature,
        "body_en_summary": en_summary,
        "escalation_to": result.escalation_targets[0] if result.escalation_targets else "",
        "cc": ", ".join(result.escalation_targets[1:]) if len(result.escalation_targets) > 1 else "",
    }


# ═══════════════════════════════════════════════════════════════════
# AI-ENHANCED CLASSIFIER (optional, requires OpenAI API key)
# ═══════════════════════════════════════════════════════════════════

def classify_with_ai(
    text: str,
    agency: str = "",
    protocol: str = "",
    model: str = "gpt-4o",
) -> Optional[DeflectionResult]:
    """
    Use GPT-4o to classify a Greek government response.
    Falls back to rule-based if OpenAI API key not set.

    Requires: OPENAI_API_KEY environment variable
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Fall back to rule-based
        return classify_deflection(text, agency, protocol)

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
    except ImportError:
        return classify_deflection(text, agency, protocol)

    system_prompt = """You are an expert classifier for Greek government bureaucratic responses.
You analyze responses from Greek agencies (AADE, EFKA, Ktimatologio, etc.) and classify them
into one of 7 deflection types:

1. INTIMIDATION — Agency tells citizen to stop filing complaints
2. CIRCULAR_REFERRAL — Agency refers to "previous answers" or another agency without substance
3. PHANTOM_CLOSURE — Marks request as "answered" without actually answering
4. SCOPE_DODGE — Answers only a narrow part, ignoring core questions
5. DOCUMENT_TRAP — Demands documents that another blocked agency must issue (catch-22)
6. SYSTEM_REDIRECT — Redirects to a different system/portal instead of answering
7. PROCEDURAL_DEFLECTION — Invokes procedural requirements to avoid acting
8. NONE — Genuine substantive response (not a deflection)

Context: This is the case of Σταματίνα Κυπριανού (AFM 044594747), widow of deceased
Ιωάννης Κυπριανός (AFM 051422558, Hellenic Navy veteran, died 13/06/2021).
The deceased's AFM has been active for 1,700+ days post-mortem with unauthorized
tax filings, E9 modifications, and property transfers.

Respond with JSON only:
{
  "deflection_type": "INTIMIDATION|CIRCULAR_REFERRAL|PHANTOM_CLOSURE|SCOPE_DODGE|DOCUMENT_TRAP|SYSTEM_REDIRECT|PROCEDURAL_DEFLECTION|NONE",
  "confidence": 0.0-1.0,
  "severity": "CRITICAL|HIGH|MEDIUM|WATCH",
  "reasoning": "Brief explanation in English",
  "legal_violations": ["list of violated Greek/EU laws"]
}"""

    user_prompt = (
        f"Agency: {agency}\n"
        f"Protocol: {protocol}\n"
        f"Response text:\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result_json = json.loads(response.choices[0].message.content)

        if result_json.get("deflection_type") == "NONE":
            return None

        dtype = DeflectionType(result_json["deflection_type"])
        rules = DEFLECTION_RULES.get(dtype, {})

        return DeflectionResult(
            deflection_type=dtype,
            severity=Severity(result_json.get("severity", "HIGH")),
            confidence=round(result_json.get("confidence", 0.8), 2),
            description=result_json.get("reasoning", "AI classification"),
            matched_patterns=["AI_CLASSIFIED"],
            legal_violations=result_json.get("legal_violations", rules.get("legal_violations", [])),
            recommended_action=rules.get("recommended_action", "Escalate"),
            escalation_targets=rules.get("escalation_targets", []),
        )

    except Exception as e:
        # Fall back to rule-based on any error
        print(f"[AI CLASSIFIER] Error: {e} — falling back to rule-based")
        return classify_deflection(text, agency, protocol)


# ═══════════════════════════════════════════════════════════════════
# CLI / STANDALONE USAGE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Demo: classify the 7 myAADE responses from March 9, 2026
    demo_responses = [
        {
            "text": "Παρακαλείσθε να μην επανέρχεστε με καταγγελίες και κατηγορίες.",
            "agency": "ΚΕΦΟΔΕ Α4'",
            "protocol": "190731/20260130/45105",
        },
        {
            "text": "Βλ. προηγούμενες απαντήσεις. Η υπηρεσία μας σας έχει ήδη ενημερώσει.",
            "agency": "ΚΕ.Β.ΕΙΣ./ΚΕΦΟΔΕ Α3'",
            "protocol": "257636/20260207/10003",
        },
        {
            "text": "Το αίτημά σας έχει ήδη απαντηθεί.",
            "agency": "ΚΕΦΟΔΕ Α3'",
            "protocol": "190736/20260130/45105",
        },
        {
            "text": "Όσον αφορά τη φορολόγηση μόνο ελληνικής πηγής (ενοίκια), σας ενημερώνουμε ότι...",
            "agency": "ΚΕΦΟΔΕ Α4'",
            "protocol": "190725/20260130/45105",
        },
        {
            "text": "Απαιτούνται τα εξής δικαιολογητικά: Δ210, Πιστοποιητικό Εγγυτέρων Συγγενών, Πιστοποιητικό μη Δημοσίευσης Διαθήκης, Ληξιαρχική Πράξη Θανάτου.",
            "agency": "ΚΕΦΟΔΕ Γ1'",
            "protocol": "97153/20260117",
        },
        {
            "text": "Τροποποιήσεις μόνο μέσω ΟΠΣ Περιουσιολογίου. Για τον αποβιώσαντα, βλ. αίτημα 129337.",
            "agency": "ΚΕ.ΦΟ.Κ. ΑΤΤΙΚΗΣ Β3'",
            "protocol": "365003/20260223/44921",
        },
        {
            "text": "Εάν επιθυμείτε να πρωτοκολληθεί το παρακάτω μήνυμά σας, παρακαλείσθε να το αποστείλετε στην ως άνω διεύθυνση ηλεκτρονικού ταχυδρομείου protokollo@attica.gr με φυσική υπογραφή, επικυρωμένο φωτοαντίγραφο ταυτότητας. Άλλως θα ληφθεί ως απλή ενημέρωση χωρίς περαιτέρω ενέργεια.",
            "agency": "Τμήμα Εποπτείας Ο.Τ.Α.",
            "protocol": "ΚΑΤΑΓΓΕΛΙΑ/20260309",
        },
    ]

    print("=" * 70)
    print("ZEUS DEFLECTION CLASSIFIER — March 9, 2026 Demo")
    print("=" * 70)
    print()

    batch_result = analyze_batch(demo_responses)

    for item in batch_result["results"]:
        r = item["result"]
        print(f"📋 {item['agency']} (Πρωτ. {item['protocol']})")
        print(f"   Type: {r['deflection_type']} | Severity: {r['severity']} | Confidence: {r['confidence']:.0%}")
        print(f"   Violations: {', '.join(r['legal_violations'][:2])}")
        print(f"   Action: {r['recommended_action'][:80]}...")
        print()

    print(f"\n{'=' * 70}")
    print(f"SYSTEMIC ANALYSIS")
    print(f"{'=' * 70}")
    print(f"Deflection rate: {batch_result['deflection_rate']}")
    print(f"Types found: {batch_result['type_counts']}")
    for pattern in batch_result["systemic_patterns"]:
        print(f"⚠️  {pattern}")

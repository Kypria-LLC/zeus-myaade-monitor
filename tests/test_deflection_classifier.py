"""
Tests for the AI deflection classifier.
Uses real response data from the March 9, 2026 myAADE batch.
"""
import pytest
from deflection_classifier import (
    classify_deflection,
    analyze_batch,
    generate_escalation,
    detect_catch22,
    DeflectionType,
    Severity,
)


# ═══════════════════════════════════════════════════════════════════
# REAL RESPONSE DATA — March 9, 2026
# ═══════════════════════════════════════════════════════════════════

class TestIntimidation:
    """ΚΕΦΟΔΕ Α4' told citizen to stop filing complaints."""

    def test_detects_intimidation(self):
        text = "Παρακαλείσθε να μην επανέρχεστε με καταγγελίες και κατηγορίες."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Α4'")
        assert result is not None
        assert result.deflection_type == DeflectionType.INTIMIDATION
        assert result.severity == Severity.CRITICAL

    def test_intimidation_legal_violations(self):
        text = "Μην επανέρχεστε. Δεν δεχόμαστε άλλες καταγγελίες."
        result = classify_deflection(text)
        assert result is not None
        assert any("GDPR" in v for v in result.legal_violations)
        assert any("2690" in v for v in result.legal_violations)

    def test_not_intimidation_for_normal_text(self):
        text = "Σας ευχαριστούμε για την αναφορά σας. Θα εξετάσουμε το αίτημα."
        result = classify_deflection(text)
        assert result is None or result.deflection_type != DeflectionType.INTIMIDATION


class TestCircularReferral:
    """ΚΕ.Β.ΕΙΣ./ΚΕΦΟΔΕ Α3' referred to 'previous answers'."""

    def test_detects_circular_referral(self):
        text = "Βλ. προηγούμενες απαντήσεις. Η υπηρεσία μας σας έχει ήδη ενημερώσει."
        result = classify_deflection(text, agency="ΚΕ.Β.ΕΙΣ.")
        assert result is not None
        assert result.deflection_type == DeflectionType.CIRCULAR_REFERRAL

    def test_referral_to_other_agency(self):
        text = "Θα πρέπει να απευθυνθείτε στην αρμόδια υπηρεσία."
        result = classify_deflection(text)
        assert result is not None
        assert result.deflection_type == DeflectionType.CIRCULAR_REFERRAL

    def test_not_circular_if_actual_answer_attached(self):
        text = "Σας αποστέλλουμε την απάντηση σε μορφή PDF."
        result = classify_deflection(text)
        assert result is None or result.deflection_type != DeflectionType.CIRCULAR_REFERRAL


class TestPhantomClosure:
    """ΚΕΦΟΔΕ Α3' marked as 'already answered' without substance."""

    def test_detects_phantom_closure(self):
        text = "Το αίτημά σας έχει ήδη απαντηθεί."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Α3'")
        assert result is not None
        assert result.deflection_type == DeflectionType.PHANTOM_CLOSURE
        assert result.severity == Severity.CRITICAL

    def test_archived_without_resolution(self):
        text = "Η υπόθεσή σας αρχειοθετήθηκε. Δεν υφίσταται εκκρεμότητα."
        result = classify_deflection(text)
        assert result is not None
        assert result.deflection_type == DeflectionType.PHANTOM_CLOSURE


class TestScopeDodge:
    """ΚΕΦΟΔΕ Α4' answered only about Greek-source income."""

    def test_detects_scope_dodge(self):
        text = "Όσον αφορά τη φορολόγηση μόνο ελληνικής πηγής (ενοίκια), σας ενημερώνουμε..."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Α4'")
        assert result is not None
        assert result.deflection_type == DeflectionType.SCOPE_DODGE


class TestDocumentTrap:
    """ΚΕΦΟΔΕ Γ1' demands documents that Δήμος Σπετσών blocks."""

    def test_detects_document_trap(self):
        text = (
            "Απαιτούνται τα εξής δικαιολογητικά: Δ210, "
            "Πιστοποιητικό Εγγυτέρων Συγγενών, "
            "Πιστοποιητικό μη Δημοσίευσης Διαθήκης, "
            "Ληξιαρχική Πράξη Θανάτου."
        )
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Γ1'")
        assert result is not None
        assert result.deflection_type == DeflectionType.DOCUMENT_TRAP
        assert result.severity == Severity.CRITICAL
        assert result.confidence >= 0.75  # High confidence — multiple keywords

    def test_high_confidence_on_multiple_matches(self):
        text = "Πρέπει να προσκομίσετε πιστοποιητικό εγγυτέρων συγγενών και Δ210."
        result = classify_deflection(text)
        assert result is not None
        assert result.confidence > 0.5


class TestSystemRedirect:
    """ΚΕ.ΦΟ.Κ. ΑΤΤΙΚΗΣ Β3' said use ΟΠΣ Περιουσιολογίου."""

    def test_detects_system_redirect(self):
        text = "Τροποποιήσεις μόνο μέσω ΟΠΣ Περιουσιολογίου."
        result = classify_deflection(text, agency="ΚΕ.ΦΟ.Κ. ΑΤΤΙΚΗΣ")
        assert result is not None
        assert result.deflection_type == DeflectionType.SYSTEM_REDIRECT


class TestProceduralDeflection:
    """Τμήμα Εποπτείας Ο.Τ.Α. demanded re-submission with signature + ID."""

    def test_detects_procedural_deflection(self):
        text = (
            "Εάν επιθυμείτε να πρωτοκολληθεί το παρακάτω μήνυμά σας, "
            "παρακαλείσθε να το αποστείλετε στην ως άνω διεύθυνση "
            "ηλεκτρονικού ταχυδρομείου protokollo@attica.gr με φυσική υπογραφή, "
            "επικυρωμένο φωτοαντίγραφο ταυτότητας. "
            "Άλλως θα ληφθεί ως απλή ενημέρωση χωρίς περαιτέρω ενέργεια."
        )
        result = classify_deflection(text, agency="Τμήμα Εποπτείας Ο.Τ.Α.")
        assert result is not None
        assert result.deflection_type == DeflectionType.PROCEDURAL_DEFLECTION
        assert result.severity == Severity.HIGH
        assert result.confidence >= 0.7


class TestBatchAnalysis:
    """Test batch analysis of all 7 responses."""

    MARCH9_RESPONSES = [
        {"text": "Μην επανέρχεστε με καταγγελίες.", "agency": "ΚΕΦΟΔΕ Α4'", "protocol": "190731"},
        {"text": "Βλ. προηγούμενες απαντήσεις.", "agency": "ΚΕΦΟΔΕ Α3'", "protocol": "257636"},
        {"text": "Έχει ήδη απαντηθεί.", "agency": "ΚΕΦΟΔΕ Α3'", "protocol": "190736"},
        {"text": "Μόνο ελληνικής πηγής.", "agency": "ΚΕΦΟΔΕ Α4'", "protocol": "190725"},
        {"text": "Απαιτούνται Δ210, Πιστοποιητικό Εγγυτέρων Συγγενών.", "agency": "ΚΕΦΟΔΕ Γ1'", "protocol": "97153"},
        {"text": "Μόνο μέσω ΟΠΣ Περιουσιολογίου.", "agency": "ΚΕ.ΦΟ.Κ.", "protocol": "365003"},
        {"text": "Αποστείλετε στο protokollo@attica.gr με φυσική υπογραφή. Άλλως χωρίς ενέργεια.", "agency": "Ο.Τ.Α.", "protocol": "ΚΑΤΑΓΓΕΛΙΑ"},
    ]

    def test_all_seven_classified(self):
        result = analyze_batch(self.MARCH9_RESPONSES)
        assert result["deflections_found"] == 7
        assert result["deflection_rate"] == "100%"

    def test_systemic_patterns_detected(self):
        result = analyze_batch(self.MARCH9_RESPONSES)
        patterns = result["systemic_patterns"]
        assert any("SYSTEMIC" in p for p in patterns)
        assert any("DIVERSE TACTICS" in p for p in patterns)
        assert any("INTIMIDATION" in p for p in patterns)

    def test_seven_distinct_types(self):
        result = analyze_batch(self.MARCH9_RESPONSES)
        assert len(result["type_counts"]) >= 6  # At least 6 distinct types


class TestCatch22Detection:
    """Test catch-22 chain detection."""

    def test_heir_declaration_catch22(self):
        text = "Απαιτείται Δ210 και Πιστοποιητικό Εγγυτέρων Συγγενών για τον αποβιώσαντα."
        result = detect_catch22(text)
        assert result is not None
        assert "Heir Declaration" in result["chain_name"]

    def test_e9_catch22(self):
        text = "Τροποποιήσεις Ε9 μόνο μέσω ΟΠΣ Περιουσιολογίου για αποβιώσαντα."
        result = detect_catch22(text)
        assert result is not None
        assert "E9" in result["chain_name"]


class TestEscalationGenerator:
    """Test auto-escalation response generation."""

    def test_generates_intimidation_response(self):
        text = "Μην επανέρχεστε με καταγγελίες."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Α4'", protocol="190731")
        assert result is not None
        escalation = generate_escalation(result, protocol="190731", agency="ΚΕΦΟΔΕ Α4'")
        assert "ΚΑΤΑΓΓΕΛΙΑ" in escalation["subject_el"]
        assert "stamatinakyprianou@gmail.com" in escalation["body_el"]
        assert "GDPR" in escalation["body_el"] or "ΓΚΠΔ" in escalation["body_el"]

    def test_generates_document_trap_response(self):
        text = "Απαιτούνται Δ210, Πιστοποιητικό Εγγυτέρων Συγγενών."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Γ1'", protocol="97153")
        assert result is not None
        escalation = generate_escalation(result, protocol="97153", agency="ΚΕΦΟΔΕ Γ1'")
        # Subject has "Φαύλος Κύκλος" and body has "ΦΑΥΛΟ ΚΥΚΛΟ"
        subject_body = escalation["subject_el"] + escalation["body_el"]
        assert "αύλο" in subject_body or "ΦΑΥΛΟ" in subject_body

    def test_escalation_has_english_summary(self):
        text = "Βλ. προηγούμενες απαντήσεις."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ", protocol="257636")
        assert result is not None
        escalation = generate_escalation(result, protocol="257636", agency="ΚΕΦΟΔΕ")
        assert "English Summary" in escalation["body_el"]


class TestGitHubComment:
    """Test GitHub Issue #147 comment generation."""

    def test_generates_markdown_table(self):
        text = "Μην επανέρχεστε."
        result = classify_deflection(text, agency="ΚΕΦΟΔΕ Α4'")
        assert result is not None
        comment = result.to_github_comment(protocol="190731", agency="ΚΕΦΟΔΕ Α4'")
        assert "| Field | Value |" in comment
        assert "INTIMIDATION" in comment
        assert "CRITICAL" in comment
        assert "190731" in comment


class TestCleanResponses:
    """Test that genuine responses are NOT flagged as deflections."""

    def test_genuine_answer_not_flagged(self):
        text = (
            "Σας ενημερώνουμε ότι η αίτησή σας εγκρίθηκε. "
            "Η επιστροφή φόρου ύψους €1.234,56 θα κατατεθεί στον λογαριασμό σας "
            "IBAN GR12 3456 7890 1234 εντός 15 εργασίμων ημερών."
        )
        result = classify_deflection(text)
        assert result is None

    def test_actual_document_provision_not_flagged(self):
        text = "Σας αποστέλλουμε το πιστοποιητικό που ζητήσατε. Επισυνάπτεται."
        result = classify_deflection(text)
        assert result is None

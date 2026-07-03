"""
Fixture-table tests for the deterministic chatbot engine.

These exercise ONLY the pure layer (normalize / match_intent /
suggest_intents / menu_chips + the intent registry) — no database, no
handlers. Run with either:

    python3 -m pytest tests/test_chatbot_engine.py
    python3 tests/test_chatbot_engine.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config_data.intents import INTENTS, MENU, get_intent  # noqa: E402
from app.services.chatbot_engine import (  # noqa: E402
    match_intent,
    menu_chips,
    normalize,
    suggest_intents,
)


def _match(text, role="student"):
    intent = match_intent(normalize(text), role)
    return intent.id if intent else None


# ---------------------------------------------------------------------------
# Fixture table: (message, role, expected intent id). >=5 phrasings per
# implemented data intent, plus key static intents.
# ---------------------------------------------------------------------------
FIXTURES = [
    # fee_balance (student)
    ("What is my fee balance?", "student", "fee_balance"),
    ("how much do I have to pay", "student", "fee_balance"),
    ("due amount", "student", "fee_balance"),
    ("kitna baki hai?", "student", "fee_balance"),
    ("remaining fees please", "student", "fee_balance"),
    ("pending fees", "student", "fee_balance"),
    # next_exam (student)
    ("when is my next exam", "student", "next_exam"),
    ("next exam date?", "student", "next_exam"),
    ("when is my paper", "student", "next_exam"),
    ("upcoming exams", "student", "next_exam"),
    ("exam kab hai", "student", "next_exam"),
    # my_result (student)
    ("show my result", "student", "my_result"),
    ("did i pass?", "student", "my_result"),
    ("my marksheet", "student", "my_result"),
    ("exam results", "student", "my_result"),
    ("what are my marks", "student", "my_result"),
    # my_progress (student)
    ("my course progress", "student", "my_progress"),
    ("how far am I in my course", "student", "my_progress"),
    ("module progress", "student", "my_progress"),
    ("how many modules completed", "student", "my_progress"),
    ("progress", "student", "my_progress"),
    # today_collections (receptionist / manager / director)
    ("today's collections", "receptionist", "today_collections"),
    ("how much collected today", "receptionist", "today_collections"),
    ("collections", "staff_manager", "today_collections"),
    ("aaj ka collection", "institution_director", "today_collections"),
    ("payments received today", "receptionist", "today_collections"),
    # student_count (manager / director)
    ("how many students do we have", "staff_manager", "student_count"),
    ("student count", "staff_manager", "student_count"),
    ("total students", "institution_director", "student_count"),
    ("number of students", "staff_manager", "student_count"),
    ("active students", "institution_director", "student_count"),
    # course_fee (any role)
    ("course fee", "student", "course_fee"),
    ("what is the fee for adca", "student", "course_fee"),
    ("how much does a course cost", "receptionist", "course_fee"),
    ("fee structure", "staff", "course_fee"),
    ("course price", "staff_manager", "course_fee"),
    ("tally fees kitni hai", "student", "course_fee"),
    # static: how_to_register
    ("how do I register", "receptionist", "how_to_register"),
    ("student registration process", "receptionist", "how_to_register"),
    ("how can I enroll", "student", "how_to_register"),
    ("sign up as student", "student", "how_to_register"),
    ("admission process", "receptionist", "how_to_register"),
    # static: course_catalog
    ("what courses are available", "student", "course_catalog"),
    ("course list", "staff", "course_catalog"),
    ("which courses do you have", "student", "course_catalog"),
    ("what can I study", "student", "course_catalog"),
    ("courses", "staff", "course_catalog"),
    # static: how_to_pay
    ("how do I pay my fees", "student", "how_to_pay"),
    ("payment methods", "student", "how_to_pay"),
    ("make a payment", "student", "how_to_pay"),
    ("how to pay", "student", "how_to_pay"),
    ("can I pay by upi", "student", "how_to_pay"),
    # static: exam_process
    ("how do exams work", "staff", "exam_process"),
    ("exam process", "student", "exam_process"),
    ("how to take exam", "student", "exam_process"),
    ("online exam", "staff", "exam_process"),
    ("tell me about exams", "staff", "exam_process"),
    # static: get_certificate
    ("how do I get my certificate", "student", "get_certificate"),
    ("download certificate", "student", "get_certificate"),
    ("when will I get my certificate", "student", "get_certificate"),
    ("certificate", "student", "get_certificate"),
    ("certificate eligibility", "student", "get_certificate"),
    # static: forgot_password
    ("i forgot my password", "student", "forgot_password"),
    ("reset password", "staff", "forgot_password"),
    ("password", "student", "forgot_password"),
    ("how do I change my password", "student", "forgot_password"),
    ("password recovery", "receptionist", "forgot_password"),
    # greetings / courtesy
    ("hi", "student", "greeting"),
    ("hello there", "student", "greeting"),
    ("namaste", "student", "greeting"),
    ("good morning", "staff", "greeting"),
    ("thank you", "student", "thanks"),
    ("thanks a lot", "student", "thanks"),
    ("bye", "student", "goodbye"),
]

# Low-confidence messages -> guided fallback (no intent).
FALLBACK_FIXTURES = [
    ("asdf qwerty zxcv", "student"),
    ("tell me a joke", "student"),
    ("who won the cricket match", "student"),
    ("what is the capital of france", "staff_manager"),
    ("blah", "receptionist"),
    ("", "student"),
]

# Role gating: same words, different role -> must NOT hit the student-only /
# staff-only data intent.
ROLE_MISMATCH_FIXTURES = [
    ("fee balance", "staff_manager", "fee_balance"),
    ("my course progress", "receptionist", "my_progress"),
    ("today's collections", "student", "today_collections"),
    ("student count", "student", "student_count"),
    ("student count", "receptionist", "student_count"),
]


def test_normalize_lowercases_strips_punctuation_and_expands_synonyms():
    assert normalize("When is my EXAM?!") == ["when", "is", "my", "exam"]
    assert normalize("Fees, paper & marksheet") == ["fee", "exam", "result"]
    assert normalize("aaj ka collection") == ["today", "ka", "collection"]
    assert normalize("") == []
    assert normalize("   ") == []


def test_fixture_table():
    failures = []
    for text, role, expected in FIXTURES:
        got = _match(text, role)
        if got != expected:
            failures.append(f"  {text!r} ({role}): expected {expected}, got {got}")
    assert not failures, "Fixture mismatches:\n" + "\n".join(failures)


def test_low_confidence_falls_back():
    failures = []
    for text, role in FALLBACK_FIXTURES:
        got = _match(text, role)
        if got is not None:
            failures.append(f"  {text!r} ({role}): expected fallback, got {got}")
    assert not failures, "Should have fallen back:\n" + "\n".join(failures)


def test_role_gating():
    failures = []
    for text, role, forbidden in ROLE_MISMATCH_FIXTURES:
        got = _match(text, role)
        if got == forbidden:
            failures.append(f"  {text!r} ({role}): must not match {forbidden}")
    assert not failures, "Role gating violated:\n" + "\n".join(failures)


def test_single_token_patterns_require_exact_token():
    # "balanced" must not match the single-token ["balance"] pattern.
    assert _match("balanced diet", "student") is None
    # Two-of-three tokens (0.67) is below the 0.75 threshold.
    assert _match("how much", "student") != "fee_balance"


def test_determinism_same_input_same_intent():
    for _ in range(3):
        assert _match("when is my next exam", "student") == "next_exam"
        assert _match("kitna baki hai", "student") == "fee_balance"


def test_tie_break_prefers_registry_order():
    # "remaining fees for my course" scores 1.0 for both fee_balance
    # (["remaining","fee"]) and course_fee (["course","fee"]); fee_balance
    # is earlier in the registry so it must win.
    assert _match("remaining fees for my course", "student") == "fee_balance"


def test_suggestions_are_role_appropriate_and_capped():
    suggestions = suggest_intents(normalize("fee exam something"), "staff")
    assert len(suggestions) <= 3
    for intent in suggestions:
        assert not intent.roles or "staff" in intent.roles


def test_menu_chips_per_role():
    for role in ("student", "receptionist", "staff_manager",
                 "institution_director", "staff", "super_admin"):
        chips = menu_chips(role)
        assert chips, f"empty menu for {role}"
        for chip in chips:
            intent = get_intent(chip["intent"])
            assert intent is not None
            assert not intent.roles or role in intent.roles
    # student menu leads with live-data intents
    student_ids = [c["intent"] for c in menu_chips("student")]
    assert "fee_balance" in student_ids and "next_exam" in student_ids


def test_registry_is_well_formed():
    seen = set()
    for intent in INTENTS:
        assert intent.id not in seen, f"duplicate intent id {intent.id}"
        seen.add(intent.id)
        assert intent.kind in ("static", "data", "menu")
        assert intent.label
        assert intent.patterns, f"{intent.id} has no patterns"
        if intent.kind == "static":
            assert intent.answer, f"{intent.id} static without answer"
        if intent.kind == "data":
            assert intent.handler, f"{intent.id} data without handler"
        for followup in intent.followups:
            assert get_intent(followup), f"{intent.id} -> unknown followup {followup}"
    for role, ids in MENU.items():
        for intent_id in ids:
            assert get_intent(intent_id), f"menu[{role}] -> unknown intent {intent_id}"


def test_data_intents_have_registered_handlers():
    from app.services.chatbot_engine import HANDLERS

    for intent in INTENTS:
        if intent.kind == "data":
            assert intent.handler in HANDLERS, f"no handler for {intent.id}"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    total = len(tests)
    print(f"\n{total - failed}/{total} tests passed")
    sys.exit(1 if failed else 0)

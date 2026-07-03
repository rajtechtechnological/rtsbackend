"""
Deterministic chatbot engine — normalizer, scorer, dispatcher, data handlers.

Replaces the old FAQ + Gemini hybrid (services/chatbot_service.py). There is
NO LLM anywhere: the same message always produces the same answer, and every
reply carries a `source` tag for traceability.

Matching rules (see docs/04-DETERMINISTIC-CHATBOT.md):
  score(pattern) = |pattern ∩ message_tokens| / |pattern|
  accept a pattern iff score >= 0.75 AND >= 2 tokens matched,
  except single-token patterns which require the token to be present (1.0).
  Intent score = max over its patterns; ties broken by registry order.

Tenant isolation: every data handler filters by the caller's institution_id,
and students can only ever read their own rows — the Student row is resolved
from the authenticated user, never from request input.

The pure matching functions (normalize / match_intent / suggest_intents) do
not touch the database, so they are unit-testable without one; DB model
imports happen lazily inside the handlers.
"""

import re
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.config_data.intents import (
    COURSE_ALIASES,
    INTENTS,
    MENU,
    SYNONYMS,
    Intent,
    get_intent,
)

ACCEPT_THRESHOLD = 0.75
MAX_SUGGESTIONS = 3
MAX_CHIPS = 8

_TOKEN_RE = re.compile(r"[a-z0-9]+")

FALLBACK_REPLY = (
    "I'm not sure I understood that. I can help with these topics — "
    "tap one, or try rephrasing:"
)


# ---------------------------------------------------------------------------
# 1. Normalizer
# ---------------------------------------------------------------------------
def normalize(text: str) -> List[str]:
    """Lowercase, strip punctuation, apply the synonym table. Deterministic."""
    tokens = _TOKEN_RE.findall((text or "").lower())
    return [SYNONYMS.get(token, token) for token in tokens]


# ---------------------------------------------------------------------------
# 2. Deterministic scorer / matcher
# ---------------------------------------------------------------------------
def _pattern_score(pattern, token_set) -> float:
    matched = len(set(pattern) & token_set)
    return matched / len(pattern) if pattern else 0.0


def _pattern_accepted(pattern, token_set) -> bool:
    matched = len(set(pattern) & token_set)
    if len(pattern) == 1:
        return matched == 1  # single-token patterns need an exact token hit
    return matched >= 2 and (matched / len(pattern)) >= ACCEPT_THRESHOLD


def _role_allowed(intent: Intent, role: str) -> bool:
    return not intent.roles or role in intent.roles


def match_intent(tokens: List[str], role: str) -> Optional[Intent]:
    """Best accepted intent for these tokens, or None (guided fallback).

    Deterministic: registry order breaks score ties (strict `>` keeps the
    earlier intent).
    """
    token_set = set(tokens)
    best: Optional[Intent] = None
    best_score = 0.0
    for intent in INTENTS:
        if not _role_allowed(intent, role):
            continue
        for pattern in intent.patterns:
            if not _pattern_accepted(pattern, token_set):
                continue
            score = _pattern_score(pattern, token_set)
            if score > best_score:
                best, best_score = intent, score
    return best


def suggest_intents(tokens: List[str], role: str, limit: int = MAX_SUGGESTIONS) -> List[Intent]:
    """Top fuzzy suggestions (any token overlap) for the guided fallback."""
    token_set = set(tokens)
    scored = []
    for index, intent in enumerate(INTENTS):
        if not _role_allowed(intent, role):
            continue
        if intent.id in ("greeting", "thanks", "goodbye"):
            continue
        best = max((_pattern_score(p, token_set) for p in intent.patterns), default=0.0)
        if best > 0.0:
            scored.append((-best, index, intent))
    scored.sort()
    return [intent for _, _, intent in scored[:limit]]


# ---------------------------------------------------------------------------
# Chips
# ---------------------------------------------------------------------------
def _chip(intent: Intent, entity: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    chip: Dict[str, Any] = {"label": intent.label, "intent": intent.id}
    if entity:
        chip["entity"] = entity
    return chip


def menu_chips(role: str) -> List[Dict[str, Any]]:
    """Role-specific top-level chips (empty state / GET /menu)."""
    chips = []
    for intent_id in MENU.get(role, MENU["default"]):
        intent = get_intent(intent_id)
        if intent is not None and _role_allowed(intent, role):
            chips.append(_chip(intent))
    return chips


def _followup_chips(intent: Intent, role: str) -> List[Dict[str, Any]]:
    chips = []
    for intent_id in intent.followups:
        followup = get_intent(intent_id)
        if followup is not None and _role_allowed(followup, role):
            chips.append(_chip(followup))
    return chips


def _merge_chips(*chip_lists) -> List[Dict[str, Any]]:
    merged, seen = [], set()
    for chips in chip_lists:
        for chip in chips:
            key = (chip["intent"], str(chip.get("entity")))
            if key not in seen:
                seen.add(key)
                merged.append(chip)
    return merged[:MAX_CHIPS]


# ---------------------------------------------------------------------------
# 3. Dispatcher
# ---------------------------------------------------------------------------
def handle_message(
    db,
    user,
    text: Optional[str] = None,
    intent_id: Optional[str] = None,
    entity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Entry point for POST /api/chatbot/message.

    Chip clicks send {intent, entity} and bypass NLP entirely; free text goes
    through normalize -> match_intent -> dispatch.
    """
    role = user.role

    if intent_id:
        intent = get_intent(intent_id)
        if intent is None or not _role_allowed(intent, role):
            return {
                "reply": "That option isn't available for your account.",
                "source": "fallback",
                "chips": menu_chips(role),
            }
        return _dispatch(db, user, intent, entity or {}, tokens=[])

    tokens = normalize(text or "")
    intent = match_intent(tokens, role)
    if intent is None:
        return _fallback(role, tokens)
    return _dispatch(db, user, intent, {}, tokens)


def _fallback(role: str, tokens: List[str]) -> Dict[str, Any]:
    suggestions = [_chip(i) for i in suggest_intents(tokens, role)]
    return {
        "reply": FALLBACK_REPLY,
        "source": "fallback",
        "chips": _merge_chips(suggestions, menu_chips(role)),
    }


def _dispatch(db, user, intent: Intent, entity: Dict[str, Any], tokens: List[str]) -> Dict[str, Any]:
    role = user.role
    if intent.kind == "static":
        chips = _followup_chips(intent, role)
        if intent.id in ("greeting", "thanks") and not chips:
            chips = menu_chips(role)
        return {
            "reply": intent.answer or "",
            "source": f"static:{intent.id}",
            "chips": chips,
        }

    handler = HANDLERS.get(intent.handler or "")
    if handler is None:  # registry misconfiguration — fail deterministically
        return _fallback(role, tokens)
    result = handler(db, user, entity, tokens)
    chips = result.get("chips")
    if chips is None:
        chips = _followup_chips(intent, role)
    return {
        "reply": result["reply"],
        "source": f"data:{intent.id}",
        "chips": chips,
    }


# ---------------------------------------------------------------------------
# 4. Data handlers — whitelisted, tenant-scoped queries.
#    Isolation is inlined: always filter by user.institution_id; students'
#    rows are resolved from the authenticated user only.
# ---------------------------------------------------------------------------
def _money(amount) -> str:
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0
    if value == int(value):
        return f"₹{int(value):,}"
    return f"₹{value:,.2f}"


def _own_student_row(db, user):
    """Resolve the caller's own Student row. Never accepts a student id from
    input — chatbot users can only ever see their own data."""
    from app.models.student import Student

    if user.institution_id is None:
        return None
    return (
        db.query(Student)
        .filter(
            Student.user_id == user.id,
            Student.institution_id == user.institution_id,
        )
        .first()
    )


_NO_STUDENT = {
    "reply": "I couldn't find your student record. Please contact your institution's front desk."
}


def _h_fee_balance(db, user, entity, tokens):
    from sqlalchemy import func

    from app.models.course import Course
    from app.models.fee_payment import FeePayment
    from app.models.student_course import StudentCourse

    student = _own_student_row(db, user)
    if student is None:
        return dict(_NO_STUDENT)

    enrollments = (
        db.query(StudentCourse, Course)
        .join(Course, StudentCourse.course_id == Course.id)
        .filter(StudentCourse.student_id == student.id)
        .order_by(StudentCourse.enrollment_date)
        .all()
    )
    if not enrollments:
        return {"reply": "You are not enrolled in any course yet."}

    lines = []
    for _, course in enrollments:
        total = float(course.fee_amount or 0)
        paid = float(
            db.query(func.coalesce(func.sum(FeePayment.amount), 0))
            .filter(
                FeePayment.student_id == student.id,
                FeePayment.course_id == course.id,
            )
            .scalar()
            or 0
        )
        balance = max(total - paid, 0.0)
        lines.append(
            f"You've paid {_money(paid)} of {_money(total)} for {course.name}. "
            f"Balance: {_money(balance)}."
        )
    return {"reply": "\n".join(lines)}


def _h_next_exam(db, user, entity, tokens):
    from app.models.batch import Batch
    from app.models.exam import Exam, ExamSchedule

    student = _own_student_row(db, user)
    if student is None:
        return dict(_NO_STUDENT)

    # Batch targeting is first-class now (F-08): a schedule matches iff it
    # targets the student's batch_id.
    query = (
        db.query(ExamSchedule, Exam)
        .join(Exam, ExamSchedule.exam_id == Exam.id)
        .filter(
            ExamSchedule.institution_id == user.institution_id,
            ExamSchedule.batch_id == student.batch_id,
            ExamSchedule.is_active.is_(True),
            ExamSchedule.scheduled_date >= date.today(),
        )
    )

    row = query.order_by(ExamSchedule.scheduled_date, ExamSchedule.start_time).first()
    if row is None:
        return {"reply": "No upcoming exams are scheduled for your batch."}

    schedule, exam = row
    when = schedule.scheduled_date.strftime("%d %b %Y")
    start = schedule.start_time.strftime("%I:%M %p").lstrip("0")
    end = schedule.end_time.strftime("%I:%M %p").lstrip("0")
    batch_row = db.query(Batch).filter(Batch.id == schedule.batch_id).first()
    batch = batch_row.name if batch_row else "-"
    return {
        "reply": f"Your next exam is **{exam.title}** on {when}, {start}–{end} (batch {batch})."
    }


def _h_my_result(db, user, entity, tokens):
    from app.models.exam import Exam, ExamAttempt

    student = _own_student_row(db, user)
    if student is None:
        return dict(_NO_STUDENT)

    row = (
        db.query(ExamAttempt, Exam)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            ExamAttempt.student_id == student.id,
            Exam.institution_id == user.institution_id,
            ExamAttempt.status.in_(["submitted", "timed_out", "verified"]),
        )
        .order_by(ExamAttempt.created_at.desc())
        .first()
    )
    if row is None:
        return {"reply": "You haven't completed any exam yet."}

    attempt, exam = row
    if attempt.is_verified:
        status = "Passed" if attempt.passed else "Not passed"
        pct = f" ({attempt.percentage:.0f}%)" if attempt.percentage is not None else ""
        score = (
            f" Score: {attempt.obtained_marks}/{attempt.total_marks}{pct}."
            if attempt.obtained_marks is not None
            else ""
        )
        return {"reply": f"{exam.title}: {status}.{score}"}
    return {"reply": f"{exam.title}: submitted, awaiting verification by staff."}


def _h_my_progress(db, user, entity, tokens):
    from sqlalchemy import func

    from app.models.course import Course
    from app.models.course_module import CourseModule, StudentModuleProgress
    from app.models.student_course import StudentCourse

    student = _own_student_row(db, user)
    if student is None:
        return dict(_NO_STUDENT)

    enrollments = (
        db.query(StudentCourse, Course)
        .join(Course, StudentCourse.course_id == Course.id)
        .filter(StudentCourse.student_id == student.id)
        .all()
    )
    if not enrollments:
        return {"reply": "You are not enrolled in any course yet."}

    lines = []
    for _, course in enrollments:
        total = (
            db.query(func.count(CourseModule.id))
            .filter(CourseModule.course_id == course.id, CourseModule.is_active.is_(True))
            .scalar()
            or 0
        )
        done = (
            db.query(func.count(StudentModuleProgress.id))
            .filter(
                StudentModuleProgress.student_id == student.id,
                StudentModuleProgress.course_id == course.id,
                StudentModuleProgress.status == "completed",
            )
            .scalar()
            or 0
        )
        pct = round(done / total * 100) if total else 0
        lines.append(f"{course.name}: {done}/{total} modules ({pct}%).")
    return {"reply": "\n".join(lines)}


def _h_today_collections(db, user, entity, tokens):
    from sqlalchemy import func

    from app.models.fee_payment import FeePayment
    from app.models.student import Student

    if user.institution_id is None:
        return {"reply": "Collections are tracked per institution — this account has no institution."}

    total, count = (
        db.query(
            func.coalesce(func.sum(FeePayment.amount), 0),
            func.count(FeePayment.id),
        )
        .join(Student, FeePayment.student_id == Student.id)
        .filter(
            Student.institution_id == user.institution_id,
            FeePayment.paid_at == date.today(),
        )
        .one()
    )
    if not count:
        return {"reply": "No payments have been collected yet today."}
    receipts = "receipt" if count == 1 else "receipts"
    return {"reply": f"{_money(total)} collected today across {count} {receipts}."}


def _h_student_count(db, user, entity, tokens):
    from sqlalchemy import func

    from app.models.student import Student

    if user.institution_id is None:
        return {"reply": "Student counts are per institution — this account has no institution."}

    total = (
        db.query(func.count(Student.id))
        .filter(Student.institution_id == user.institution_id)
        .scalar()
        or 0
    )
    month_start = date.today().replace(day=1)
    this_month = (
        db.query(func.count(Student.id))
        .filter(
            Student.institution_id == user.institution_id,
            Student.enrollment_date >= month_start,
        )
        .scalar()
        or 0
    )
    return {"reply": f"{total} active students, {this_month} enrolled this month."}


# Tokens too generic to identify a course by name.
_COURSE_GENERIC_TOKENS = {
    "course", "fee", "cost", "price", "much", "how", "what", "is", "the",
    "of", "for", "a", "an", "in", "and", "duration", "structure", "hai",
    "ka", "ki", "tell", "me", "about", "long", "my",
}


def _visible_courses(db, user):
    """Institution's own courses + global templates (institution_id IS NULL).
    Never another institution's rows."""
    from sqlalchemy import or_

    from app.models.course import Course

    query = db.query(Course)
    if user.institution_id is not None:
        query = query.filter(
            or_(
                Course.institution_id == user.institution_id,
                Course.institution_id.is_(None),
            )
        )
    else:
        query = query.filter(Course.institution_id.is_(None))
    courses = query.order_by(Course.name).all()

    # Prefer the institution's own copy when a global template shares its name.
    by_name = {}
    for course in courses:
        key = (course.name or "").strip().lower()
        current = by_name.get(key)
        if current is None or (current.institution_id is None and course.institution_id is not None):
            by_name[key] = course
    return list(by_name.values())


def _resolve_courses(courses, tokens):
    """Deterministic fuzzy course-name resolution from message tokens."""
    wanted = set()
    for token in tokens:
        if token in _COURSE_GENERIC_TOKENS or len(token) < 2:
            continue
        wanted.add(token)
        alias = COURSE_ALIASES.get(token)
        if alias:
            wanted.add(alias)
    if not wanted:
        return []
    matches = []
    for course in courses:
        name_tokens = set(_TOKEN_RE.findall((course.name or "").lower()))
        if name_tokens & wanted:
            matches.append(course)
    return matches


def _course_fee_reply(course):
    parts = [f"**{course.name}**: fee {_money(course.fee_amount)}"]
    if course.duration_months:
        parts.append(f"duration {course.duration_months} months")
    return ", ".join(parts) + "."


def _course_chips(courses):
    return [
        {"label": c.name, "intent": "course_fee", "entity": {"course_id": str(c.id)}}
        for c in courses[:MAX_CHIPS]
    ]


def _h_course_fee(db, user, entity, tokens):
    courses = _visible_courses(db, user)
    if not courses:
        return {"reply": "No courses are configured for your institution yet."}

    # Chip click: {intent: "course_fee", entity: {course_id}} — no NLP at all.
    course_id = (entity or {}).get("course_id")
    if course_id:
        try:
            wanted_id = UUID(str(course_id))
        except (ValueError, AttributeError, TypeError):
            wanted_id = None
        course = next((c for c in courses if c.id == wanted_id), None)
        if course is not None:
            return {"reply": _course_fee_reply(course)}
        return {"reply": "Which course do you mean?", "chips": _course_chips(courses)}

    matches = _resolve_courses(courses, tokens)
    if len(matches) == 1:
        return {"reply": _course_fee_reply(matches[0])}
    ambiguous = matches if len(matches) > 1 else courses
    return {"reply": "Which course do you mean?", "chips": _course_chips(ambiguous)}


HANDLERS = {
    "fee_balance": _h_fee_balance,
    "next_exam": _h_next_exam,
    "my_result": _h_my_result,
    "my_progress": _h_my_progress,
    "today_collections": _h_today_collections,
    "student_count": _h_student_count,
    "course_fee": _h_course_fee,
}

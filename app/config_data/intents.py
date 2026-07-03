"""
Deterministic chatbot intent registry — the single source of truth.

Each Intent is matched against normalized message tokens by
app.services.chatbot_engine. No AI/LLM is involved anywhere.

kind:
  "static" -> canned answer (ported from faq_config.py)
  "data"   -> whitelisted, tenant-scoped DB query (handler name resolved
              in chatbot_engine.HANDLERS)
  "menu"   -> reserved for menu-only entries

roles: empty tuple = any authenticated role may ask.
patterns: token lists matched order-independently against the normalized
          message (see chatbot_engine.normalize / match_intent).
followups: intent ids rendered as chips after the answer (role-filtered).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from app.config_data.faq_config import FAQ_DATABASE

# ---------------------------------------------------------------------------
# Synonym / normalization table (applied token-by-token after lowercasing
# and punctuation stripping, BEFORE matching). Keep keys and values lowercase.
# ---------------------------------------------------------------------------
SYNONYMS = {
    # fees / money
    "fees": "fee",
    "fess": "fee",
    "shulk": "fee",
    "paisa": "fee",
    "paise": "fee",
    "paid": "pay",
    "payments": "payment",
    "receipts": "receipt",
    "recipt": "receipt",
    # exams
    "exams": "exam",
    "examination": "exam",
    "examinations": "exam",
    "paper": "exam",
    "papers": "exam",
    "test": "exam",
    "tests": "exam",
    "pariksha": "exam",
    # results
    "results": "result",
    "marksheet": "result",
    "marksheets": "result",
    "score": "result",
    "scores": "result",
    "grade": "result",
    "grades": "result",
    "parinam": "result",
    # courses / modules
    "courses": "course",
    "modules": "module",
    "lessons": "lesson",
    "syllabus": "course",
    # certificates
    "certificates": "certificate",
    "cert": "certificate",
    "certs": "certificate",
    "certification": "certificate",
    "certifications": "certificate",
    # people / counts
    "students": "student",
    "staffs": "staff",
    # registration
    "registration": "register",
    "registrations": "register",
    "registered": "register",
    "signup": "register",
    "enrol": "enroll",
    "enrolment": "enroll",
    "enrollment": "enroll",
    "enrolled": "enroll",
    "admissions": "admission",
    # scheduling / time
    "schedules": "schedule",
    "scheduled": "schedule",
    "timetable": "schedule",
    "dates": "date",
    "aaj": "today",
    "kab": "when",
    # collections
    "collections": "collection",
    "collected": "collection",
    # progress
    "completed": "complete",
    "completion": "complete",
    # auth
    "passwords": "password",
    "pwd": "password",
    "passwd": "password",
    "signin": "login",
    "logins": "login",
    # misc
    "methods": "method",
    "kitna": "much",
    "kitni": "much",
    "roles": "role",
    "permissions": "permission",
    "types": "type",
    "questions": "question",
    "balances": "balance",
    "batches": "batch",
    "attendence": "attendance",
    "madat": "madad",
}

# Aliases used only for course-name entity resolution (course_fee intent).
# alias token -> token expected to appear in the course name.
COURSE_ALIASES = {
    "account": "tally",
    "accounting": "tally",
    "accounts": "tally",
    "office": "doarm",
    "automation": "doarm",
    "hardware": "hdit",
    "networking": "hdit",
    "network": "hdit",
}


@dataclass(frozen=True)
class Intent:
    id: str
    kind: str  # "static" | "data" | "menu"
    label: str  # chip label
    roles: Tuple[str, ...] = ()  # empty = any role
    patterns: Tuple[Tuple[str, ...], ...] = ()
    handler: Optional[str] = None  # key into chatbot_engine.HANDLERS (kind="data")
    answer: Optional[str] = None  # canned reply (kind="static")
    followups: Tuple[str, ...] = ()


# Canned answers ported from faq_config.py (kept as the text source).
_FAQ_ANSWER = {f["id"]: f["answer"] for f in FAQ_DATABASE}

STUDENT = ("student",)
COLLECTION_ROLES = ("receptionist", "staff_manager", "institution_director", "super_admin")
COUNT_ROLES = ("staff_manager", "institution_director", "super_admin")


def _p(*patterns):
    return tuple(tuple(p) for p in patterns)


# ---------------------------------------------------------------------------
# Registry. ORDER MATTERS: earlier intents win score ties.
# Greetings first, then data intents (live answers beat generic FAQ),
# then static FAQ intents.
# ---------------------------------------------------------------------------
INTENTS: List[Intent] = [
    # ---- courtesy -----------------------------------------------------------
    Intent(
        id="greeting",
        kind="static",
        label="Say hello",
        patterns=_p(["hi"], ["hii"], ["hello"], ["hey"], ["namaste"], ["namaskar"],
                    ["pranam"], ["good", "morning"], ["good", "afternoon"],
                    ["good", "evening"], ["whats", "up"]),
        answer=(
            "Hello! I'm Raj, the RTS assistant. I answer from your institution's "
            "records — pick a topic below or type a question."
        ),
    ),
    Intent(
        id="thanks",
        kind="static",
        label="Thanks",
        patterns=_p(["thanks"], ["thank", "you"], ["thankyou"], ["thx"],
                    ["dhanyavad"], ["shukriya"]),
        answer="You're welcome! Anything else I can help you with?",
    ),
    Intent(
        id="goodbye",
        kind="static",
        label="Goodbye",
        patterns=_p(["bye"], ["goodbye"], ["good", "bye"], ["see", "you"],
                    ["alvida"], ["take", "care"]),
        answer="Goodbye! Come back any time you have a question.",
    ),

    # ---- data intents (tenant-scoped live answers) --------------------------
    Intent(
        id="fee_balance",
        kind="data",
        label="My fee balance",
        roles=STUDENT,
        patterns=_p(["fee", "balance"], ["balance"], ["due", "amount"],
                    ["fee", "due"], ["remaining", "fee"], ["pending", "fee"],
                    ["how", "much", "pay"], ["baki"], ["owe"], ["fee", "left"]),
        handler="fee_balance",
        followups=("how_to_pay", "payment_history"),
    ),
    Intent(
        id="next_exam",
        kind="data",
        label="My next exam",
        roles=STUDENT,
        patterns=_p(["next", "exam"], ["when", "exam"], ["exam", "date"],
                    ["exam", "schedule"], ["upcoming", "exam"], ["exam", "today"],
                    ["my", "exam"]),
        handler="next_exam",
        followups=("exam_process", "my_result"),
    ),
    Intent(
        id="my_result",
        kind="data",
        label="My results",
        roles=STUDENT,
        patterns=_p(["my", "result"], ["result"], ["exam", "result"],
                    ["did", "i", "pass"], ["pass", "fail"], ["my", "marks"],
                    ["result", "verified"]),
        handler="my_result",
        followups=("next_exam", "my_progress"),
    ),
    Intent(
        id="my_progress",
        kind="data",
        label="My course progress",
        roles=STUDENT,
        patterns=_p(["my", "progress"], ["progress"], ["course", "progress"],
                    ["module", "progress"], ["how", "far", "course"],
                    ["module", "complete"], ["how", "many", "module"]),
        handler="my_progress",
        followups=("my_result", "get_certificate"),
    ),
    Intent(
        id="today_collections",
        kind="data",
        label="Today's collections",
        roles=COLLECTION_ROLES,
        patterns=_p(["today", "collection"], ["collection"], ["today", "payment"],
                    ["payment", "received", "today"], ["today", "fee"],
                    ["cash", "today"]),
        handler="today_collections",
        followups=("student_count", "payment_history"),
    ),
    Intent(
        id="student_count",
        kind="data",
        label="Student count",
        roles=COUNT_ROLES,
        patterns=_p(["how", "many", "student"], ["student", "count"],
                    ["total", "student"], ["number", "student"],
                    ["active", "student"], ["student", "enroll", "month"]),
        handler="student_count",
        followups=("today_collections",),
    ),
    Intent(
        id="course_fee",
        kind="data",
        label="Course fees",
        patterns=_p(["course", "fee"], ["fee", "structure"], ["much", "fee"],
                    ["how", "much", "course"], ["price"], ["cost"],
                    ["course", "duration"], ["adca"], ["dca"], ["hdit"],
                    ["doarm"], ["tally"]),
        handler="course_fee",
        followups=("course_catalog", "how_to_pay"),
    ),

    # ---- static intents (ported from faq_config.py) -------------------------
    Intent(
        id="how_to_register",
        kind="static",
        label="How to register",
        patterns=_p(["how", "register"], ["register"], ["enroll"], ["sign", "up"],
                    ["become", "student"], ["admission"], ["register", "student"],
                    ["new", "student"]),
        answer=_FAQ_ANSWER["reg_001"],
        followups=("student_id_format", "course_catalog"),
    ),
    Intent(
        id="student_id_format",
        kind="static",
        label="Student ID format",
        patterns=_p(["student", "id"], ["id", "format"], ["id", "generated"],
                    ["id", "structure"], ["id", "mean"]),
        answer=_FAQ_ANSWER["reg_002"],
        followups=("how_to_register",),
    ),
    Intent(
        id="course_catalog",
        kind="static",
        label="Available courses",
        patterns=_p(["course", "available"], ["course", "list"], ["which", "course"],
                    ["what", "course"], ["course"], ["study"], ["course", "option"],
                    ["course", "offer"]),
        answer=_FAQ_ANSWER["course_001"],
        followups=("course_fee", "how_to_register"),
    ),
    Intent(
        id="how_to_pay",
        kind="static",
        label="How to pay fees",
        patterns=_p(["how", "pay"], ["pay", "fee"], ["payment", "method"],
                    ["make", "payment"], ["payment", "process"], ["upi"],
                    ["pay", "online"]),
        answer=_FAQ_ANSWER["pay_001"],
        followups=("payment_history", "fee_balance"),
    ),
    Intent(
        id="payment_history",
        kind="static",
        label="Payment history",
        patterns=_p(["payment", "history"], ["view", "payment"],
                    ["payment", "record"], ["payment", "status"],
                    ["my", "payment"], ["receipt"]),
        answer=_FAQ_ANSWER["pay_002"],
        followups=("how_to_pay",),
    ),
    Intent(
        id="exam_process",
        kind="static",
        label="How exams work",
        patterns=_p(["how", "exam"], ["exam", "work"], ["exam", "process"],
                    ["online", "exam"], ["exam", "system"], ["take", "exam"],
                    ["exam"]),
        answer=_FAQ_ANSWER["exam_001"],
        followups=("passing_marks", "next_exam"),
    ),
    Intent(
        id="passing_marks",
        kind="static",
        label="Passing marks",
        patterns=_p(["passing", "marks"], ["pass", "marks"], ["minimum", "marks"],
                    ["passing", "percentage"], ["pass", "criteria"],
                    ["marks", "pass"]),
        answer=_FAQ_ANSWER["exam_002"],
        followups=("exam_process", "my_result"),
    ),
    Intent(
        id="get_certificate",
        kind="static",
        label="Get my certificate",
        patterns=_p(["certificate"], ["get", "certificate"],
                    ["download", "certificate"], ["when", "certificate"],
                    ["certificate", "eligibility"], ["certificate", "verify"]),
        answer=_FAQ_ANSWER["cert_001"],
        followups=("my_progress", "get_support"),
    ),
    Intent(
        id="attendance_tracking",
        kind="static",
        label="Attendance",
        patterns=_p(["attendance"], ["check", "attendance"],
                    ["attendance", "record"], ["my", "attendance"],
                    ["view", "attendance"], ["attendance", "percentage"]),
        answer=_FAQ_ANSWER["attend_001"],
        followups=("get_support",),
    ),
    Intent(
        id="forgot_password",
        kind="static",
        label="Forgot password",
        patterns=_p(["forgot", "password"], ["reset", "password"], ["password"],
                    ["password", "recovery"], ["change", "password"],
                    ["cant", "login"]),
        answer=_FAQ_ANSWER["login_001"],
        followups=("login_credentials", "get_support"),
    ),
    Intent(
        id="login_credentials",
        kind="static",
        label="Login help",
        patterns=_p(["login"], ["how", "login"], ["login", "details"],
                    ["login", "credentials"], ["username"], ["sign", "in"],
                    ["credentials"]),
        answer=_FAQ_ANSWER["login_002"],
        followups=("forgot_password",),
    ),
    Intent(
        id="dashboard_features",
        kind="static",
        label="Dashboard features",
        patterns=_p(["dashboard"], ["dashboard", "feature"], ["what", "dashboard"],
                    ["my", "dashboard"], ["dashboard", "access"]),
        answer=_FAQ_ANSWER["dash_001"],
        followups=("track_progress",),
    ),
    Intent(
        id="user_roles",
        kind="static",
        label="User roles",
        patterns=_p(["role"], ["user", "role"], ["permission"], ["who", "can"],
                    ["user", "type"], ["role", "permission"]),
        answer=_FAQ_ANSWER["role_001"],
        followups=("get_support",),
    ),
    Intent(
        id="get_support",
        kind="static",
        label="Get help",
        patterns=_p(["help"], ["support"], ["contact", "support"],
                    ["need", "assistance"], ["technical", "support"],
                    ["help", "desk"], ["madad"]),
        answer=_FAQ_ANSWER["support_001"],
    ),
    Intent(
        id="track_progress",
        kind="static",
        label="Track progress",
        patterns=_p(["track", "progress"], ["view", "progress"],
                    ["progress", "status"], ["complete", "status"],
                    ["track", "learning"]),
        answer=_FAQ_ANSWER["progress_001"],
        followups=("get_certificate",),
    ),
]

INTENT_INDEX = {intent.id: intent for intent in INTENTS}


def get_intent(intent_id: str) -> Optional[Intent]:
    return INTENT_INDEX.get(intent_id)


# ---------------------------------------------------------------------------
# Role-specific top-level menu (GET /api/chatbot/menu and guided fallback).
# ---------------------------------------------------------------------------
MENU = {
    "student": ("fee_balance", "next_exam", "my_result", "my_progress",
                "course_fee", "get_certificate"),
    "receptionist": ("today_collections", "course_fee", "how_to_pay",
                     "how_to_register"),
    "staff_manager": ("today_collections", "student_count", "course_fee",
                      "exam_process"),
    "institution_director": ("student_count", "today_collections", "course_fee",
                             "course_catalog"),
    "staff": ("exam_process", "attendance_tracking", "course_catalog",
              "get_support"),
    "super_admin": ("student_count", "course_catalog", "course_fee",
                    "user_roles"),
    "default": ("course_catalog", "course_fee", "exam_process", "get_support"),
}

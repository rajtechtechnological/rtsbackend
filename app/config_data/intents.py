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
label_hi / answer_hi: Hindi equivalents used when lang="hi".
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
    "shulka": "fee",
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
    "pareeksha": "exam",
    # results
    "results": "result",
    "marksheet": "result",
    "marksheets": "result",
    "score": "result",
    "scores": "result",
    "grade": "result",
    "grades": "result",
    "parinam": "result",
    "parinam": "result",
    "ank": "result",
    # courses / modules
    "courses": "course",
    "modules": "module",
    "lessons": "lesson",
    "syllabus": "course",
    "kors": "course",
    # certificates
    "certificates": "certificate",
    "cert": "certificate",
    "certs": "certificate",
    "certification": "certificate",
    "certifications": "certificate",
    "praman": "certificate",
    "pramanpatra": "certificate",
    # people / counts
    "students": "student",
    "staffs": "staff",
    "chatra": "student",
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
    "namankan": "enroll",
    # scheduling / time
    "schedules": "schedule",
    "scheduled": "schedule",
    "timetable": "schedule",
    "dates": "date",
    "aaj": "today",
    "kab": "when",
    "samay": "schedule",
    # collections
    "collections": "collection",
    "collected": "collection",
    "vasuli": "collection",
    # progress
    "completed": "complete",
    "completion": "complete",
    "pragati": "progress",
    # auth
    "passwords": "password",
    "pwd": "password",
    "passwd": "password",
    "signin": "login",
    "logins": "login",
    "pasword": "password",
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
    "sahayata": "madad",
    "upasthiti": "attendance",
    "baaki": "balance",
    "baki": "balance",
    "jankari": "info",
    "jankar": "info",
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
    label: str  # chip label (English)
    label_hi: str = ""  # chip label (Hindi)
    roles: Tuple[str, ...] = ()  # empty = any role
    patterns: Tuple[Tuple[str, ...], ...] = ()
    handler: Optional[str] = None  # key into chatbot_engine.HANDLERS (kind="data")
    answer: Optional[str] = None  # canned reply English (kind="static")
    answer_hi: Optional[str] = None  # canned reply Hindi (kind="static")
    followups: Tuple[str, ...] = ()
    public: bool = False  # reachable from the unauthenticated /public endpoints


# Canned answers ported from faq_config.py (kept as the text source).
_FAQ_ANSWER = {f["id"]: f["answer"] for f in FAQ_DATABASE}
_FAQ_ANSWER_HI = {f["id"]: f.get("answer_hi", f["answer"]) for f in FAQ_DATABASE}

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
        label_hi="नमस्ते",
        patterns=_p(["hi"], ["hii"], ["hello"], ["hey"], ["namaste"], ["namaskar"],
                    ["pranam"], ["good", "morning"], ["good", "afternoon"],
                    ["good", "evening"], ["whats", "up"]),
        answer=(
            "Hello! I'm Raj, the RTS assistant. I answer from your institution's "
            "records — pick a topic below or type a question."
        ),
        answer_hi=(
            "नमस्ते! मैं राज हूँ, RTS सहायक। मैं आपकी संस्था के रिकॉर्ड से उत्तर देता हूँ — "
            "नीचे कोई विषय चुनें या अपना प्रश्न टाइप करें।"
        ),
        public=True,
    ),
    Intent(
        id="thanks",
        kind="static",
        label="Thanks",
        label_hi="धन्यवाद",
        patterns=_p(["thanks"], ["thank", "you"], ["thankyou"], ["thx"],
                    ["dhanyavad"], ["shukriya"]),
        answer="You're welcome! Anything else I can help you with?",
        answer_hi="आपका स्वागत है! क्या मैं किसी और चीज़ में आपकी मदद कर सकता हूँ?",
        public=True,
    ),
    Intent(
        id="goodbye",
        kind="static",
        label="Goodbye",
        label_hi="अलविदा",
        patterns=_p(["bye"], ["goodbye"], ["good", "bye"], ["see", "you"],
                    ["alvida"], ["take", "care"]),
        answer="Goodbye! Come back any time you have a question.",
        answer_hi="अलविदा! जब भी कोई प्रश्न हो, वापस आएं।",
        public=True,
    ),

    # ---- data intents (tenant-scoped live answers) --------------------------
    Intent(
        id="fee_balance",
        kind="data",
        label="My fee balance",
        label_hi="मेरा फ़ीस बैलेंस",
        roles=STUDENT,
        patterns=_p(["fee", "balance"], ["balance"], ["due", "amount"],
                    ["fee", "due"], ["remaining", "fee"], ["pending", "fee"],
                    ["how", "much", "pay"], ["baki"], ["owe"], ["fee", "left"],
                    ["baaki"], ["kitna", "fee"], ["fee", "baki"]),
        handler="fee_balance",
        followups=("how_to_pay", "payment_history"),
    ),
    Intent(
        id="next_exam",
        kind="data",
        label="My next exam",
        label_hi="मेरी अगली परीक्षा",
        roles=STUDENT,
        patterns=_p(["next", "exam"], ["when", "exam"], ["exam", "date"],
                    ["exam", "schedule"], ["upcoming", "exam"], ["exam", "today"],
                    ["my", "exam"], ["pariksha", "kab"], ["agli", "pariksha"]),
        handler="next_exam",
        followups=("exam_process", "my_result"),
    ),
    Intent(
        id="my_result",
        kind="data",
        label="My results",
        label_hi="मेरे परिणाम",
        roles=STUDENT,
        patterns=_p(["my", "result"], ["result"], ["exam", "result"],
                    ["did", "i", "pass"], ["pass", "fail"], ["my", "marks"],
                    ["result", "verified"], ["parinam"], ["ank"]),
        handler="my_result",
        followups=("next_exam", "my_progress"),
    ),
    Intent(
        id="my_progress",
        kind="data",
        label="My course progress",
        label_hi="मेरी कोर्स प्रगति",
        roles=STUDENT,
        patterns=_p(["my", "progress"], ["progress"], ["course", "progress"],
                    ["module", "progress"], ["how", "far", "course"],
                    ["module", "complete"], ["how", "many", "module"],
                    ["pragati"], ["kitna", "complete"]),
        handler="my_progress",
        followups=("my_result", "get_certificate"),
    ),
    Intent(
        id="today_collections",
        kind="data",
        label="Today's collections",
        label_hi="आज की वसूली",
        roles=COLLECTION_ROLES,
        patterns=_p(["today", "collection"], ["collection"], ["today", "payment"],
                    ["payment", "received", "today"], ["today", "fee"],
                    ["cash", "today"], ["vasuli"], ["aaj", "collection"]),
        handler="today_collections",
        followups=("student_count", "payment_history"),
    ),
    Intent(
        id="student_count",
        kind="data",
        label="Student count",
        label_hi="छात्र संख्या",
        roles=COUNT_ROLES,
        patterns=_p(["how", "many", "student"], ["student", "count"],
                    ["total", "student"], ["number", "student"],
                    ["active", "student"], ["student", "enroll", "month"],
                    ["kitne", "student"], ["chatra", "sankhya"]),
        handler="student_count",
        followups=("today_collections",),
    ),
    Intent(
        id="course_fee",
        kind="data",
        label="Course fees",
        label_hi="कोर्स फ़ीस",
        patterns=_p(["course", "fee"], ["fee", "structure"], ["much", "fee"],
                    ["how", "much", "course"], ["price"], ["cost"],
                    ["course", "duration"], ["adca"], ["dca"], ["hdit"],
                    ["doarm"], ["tally"], ["shulk"], ["kitna", "course"]),
        handler="course_fee",
        followups=("course_catalog", "how_to_pay"),
        public=True,
    ),

    # ---- static intents (ported from faq_config.py) -------------------------
    Intent(
        id="how_to_register",
        kind="static",
        label="How to register",
        label_hi="पंजीकरण कैसे करें",
        patterns=_p(["how", "register"], ["register"], ["enroll"], ["sign", "up"],
                    ["become", "student"], ["admission"], ["register", "student"],
                    ["new", "student"], ["namankan"], ["admission", "kaise"]),
        answer=_FAQ_ANSWER["reg_001"],
        answer_hi=_FAQ_ANSWER_HI["reg_001"],
        followups=("student_id_format", "course_catalog"),
        public=True,
    ),
    Intent(
        id="student_id_format",
        kind="static",
        label="Student ID format",
        label_hi="छात्र ID प्रारूप",
        patterns=_p(["student", "id"], ["id", "format"], ["id", "generated"],
                    ["id", "structure"], ["id", "mean"]),
        answer=_FAQ_ANSWER["reg_002"],
        answer_hi=_FAQ_ANSWER_HI["reg_002"],
        followups=("how_to_register",),
    ),
    Intent(
        id="course_catalog",
        kind="static",
        label="Available courses",
        label_hi="उपलब्ध कोर्स",
        patterns=_p(["course", "available"], ["course", "list"], ["which", "course"],
                    ["what", "course"], ["course"], ["study"], ["course", "option"],
                    ["course", "offer"], ["kaunsa", "course"], ["koi", "course"]),
        answer=_FAQ_ANSWER["course_001"],
        answer_hi=_FAQ_ANSWER_HI["course_001"],
        followups=("course_fee", "how_to_register"),
        public=True,
    ),
    Intent(
        id="how_to_pay",
        kind="static",
        label="How to pay fees",
        label_hi="फ़ीस कैसे भरें",
        patterns=_p(["how", "pay"], ["pay", "fee"], ["payment", "method"],
                    ["make", "payment"], ["payment", "process"], ["upi"],
                    ["pay", "online"], ["fee", "kaise", "bhare"], ["fee", "jama"]),
        answer=_FAQ_ANSWER["pay_001"],
        answer_hi=_FAQ_ANSWER_HI["pay_001"],
        followups=("payment_history", "fee_balance"),
    ),
    Intent(
        id="payment_history",
        kind="static",
        label="Payment history",
        label_hi="भुगतान इतिहास",
        patterns=_p(["payment", "history"], ["view", "payment"],
                    ["payment", "record"], ["payment", "status"],
                    ["my", "payment"], ["receipt"], ["rasid"], ["bhugtan"]),
        answer=_FAQ_ANSWER["pay_002"],
        answer_hi=_FAQ_ANSWER_HI["pay_002"],
        followups=("how_to_pay",),
    ),
    Intent(
        id="exam_process",
        kind="static",
        label="How exams work",
        label_hi="परीक्षा कैसे होती है",
        patterns=_p(["how", "exam"], ["exam", "work"], ["exam", "process"],
                    ["online", "exam"], ["exam", "system"], ["take", "exam"],
                    ["exam"], ["pariksha", "kaise"]),
        answer=_FAQ_ANSWER["exam_001"],
        answer_hi=_FAQ_ANSWER_HI["exam_001"],
        followups=("passing_marks", "next_exam"),
    ),
    Intent(
        id="passing_marks",
        kind="static",
        label="Passing marks",
        label_hi="उत्तीर्ण अंक",
        patterns=_p(["passing", "marks"], ["pass", "marks"], ["minimum", "marks"],
                    ["passing", "percentage"], ["pass", "criteria"],
                    ["marks", "pass"], ["pass", "kitna"], ["uttiranank"]),
        answer=_FAQ_ANSWER["exam_002"],
        answer_hi=_FAQ_ANSWER_HI["exam_002"],
        followups=("exam_process", "my_result"),
    ),
    Intent(
        id="get_certificate",
        kind="static",
        label="Get my certificate",
        label_hi="मेरा प्रमाण पत्र",
        patterns=_p(["certificate"], ["get", "certificate"],
                    ["download", "certificate"], ["when", "certificate"],
                    ["certificate", "eligibility"], ["certificate", "verify"],
                    ["pramanpatra"], ["praman", "patra"]),
        answer=_FAQ_ANSWER["cert_001"],
        answer_hi=_FAQ_ANSWER_HI["cert_001"],
        followups=("my_progress", "get_support"),
    ),
    Intent(
        id="attendance_tracking",
        kind="static",
        label="Attendance",
        label_hi="उपस्थिति",
        patterns=_p(["attendance"], ["check", "attendance"],
                    ["attendance", "record"], ["my", "attendance"],
                    ["view", "attendance"], ["attendance", "percentage"],
                    ["upasthiti"], ["hazri"]),
        answer=_FAQ_ANSWER["attend_001"],
        answer_hi=_FAQ_ANSWER_HI["attend_001"],
        followups=("get_support",),
    ),
    Intent(
        id="forgot_password",
        kind="static",
        label="Forgot password",
        label_hi="पासवर्ड भूल गए",
        patterns=_p(["forgot", "password"], ["reset", "password"], ["password"],
                    ["password", "recovery"], ["change", "password"],
                    ["cant", "login"], ["pasword", "bhul"], ["password", "reset"]),
        answer=_FAQ_ANSWER["login_001"],
        answer_hi=_FAQ_ANSWER_HI["login_001"],
        followups=("login_credentials", "get_support"),
    ),
    Intent(
        id="login_credentials",
        kind="static",
        label="Login help",
        label_hi="लॉगिन सहायता",
        patterns=_p(["login"], ["how", "login"], ["login", "details"],
                    ["login", "credentials"], ["username"], ["sign", "in"],
                    ["credentials"], ["login", "kaise"]),
        answer=_FAQ_ANSWER["login_002"],
        answer_hi=_FAQ_ANSWER_HI["login_002"],
        followups=("forgot_password",),
    ),
    Intent(
        id="dashboard_features",
        kind="static",
        label="Dashboard features",
        label_hi="डैशबोर्ड विशेषताएं",
        patterns=_p(["dashboard"], ["dashboard", "feature"], ["what", "dashboard"],
                    ["my", "dashboard"], ["dashboard", "access"]),
        answer=_FAQ_ANSWER["dash_001"],
        answer_hi=_FAQ_ANSWER_HI["dash_001"],
        followups=("track_progress",),
    ),
    Intent(
        id="user_roles",
        kind="static",
        label="User roles",
        label_hi="उपयोगकर्ता भूमिकाएं",
        patterns=_p(["role"], ["user", "role"], ["permission"], ["who", "can"],
                    ["user", "type"], ["role", "permission"]),
        answer=_FAQ_ANSWER["role_001"],
        answer_hi=_FAQ_ANSWER_HI["role_001"],
        followups=("get_support",),
    ),
    Intent(
        id="get_support",
        kind="static",
        label="Get help",
        label_hi="सहायता लें",
        patterns=_p(["help"], ["support"], ["contact", "support"],
                    ["need", "assistance"], ["technical", "support"],
                    ["help", "desk"], ["madad"], ["sahayata"]),
        answer=_FAQ_ANSWER["support_001"],
        answer_hi=_FAQ_ANSWER_HI["support_001"],
    ),
    Intent(
        id="track_progress",
        kind="static",
        label="Track progress",
        label_hi="प्रगति देखें",
        patterns=_p(["track", "progress"], ["view", "progress"],
                    ["progress", "status"], ["complete", "status"],
                    ["track", "learning"], ["pragati", "dekho"]),
        answer=_FAQ_ANSWER["progress_001"],
        answer_hi=_FAQ_ANSWER_HI["progress_001"],
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

# Empty-state chips for the unauthenticated /public endpoints. Kept separate
# from MENU (which is role-keyed and assumes a logged-in user) — every id
# here must also carry public=True on its Intent, checked in chatbot_engine.
PUBLIC_MENU = ("course_catalog", "course_fee", "how_to_register")

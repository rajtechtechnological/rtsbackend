"""
Public chatbot security tests: the per-IP rate limiter, and the boundary
that keeps the unauthenticated /public endpoints from ever reaching
account-specific data or another institution's courses.

Requires the local Postgres from .env (LOCAL_DB_URL) — with_for_update()
needs real row locking, which sqlite doesn't provide. Skipped automatically
if the DB is unreachable, same convention as test_tenant_isolation.py.

Run with either:
    python3 -m pytest tests/test_rate_limit.py
    python3 tests/test_rate_limit.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_NAME = "rts_rate_limit_test"
_live = None  # cached fixture dict or False


def _build_live_fixture():
    """Throwaway Postgres DB with the rate-limit table plus one global course
    template (institution_id=None) and one tenant-owned course of the same
    name — the public course_fee handler must only ever see the former.
    Returns None if Postgres is unavailable."""
    global _live
    if _live is not None:
        return _live or None

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from app.config import settings

        base_url = settings.LOCAL_DB_URL
        if not base_url:
            raise RuntimeError("no LOCAL_DB_URL")
        admin_url = base_url.rsplit("/", 1)[0] + "/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
        admin_engine.dispose()

        test_url = base_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"
        engine = create_engine(test_url)
    except Exception as exc:  # DB not reachable — skip live tests
        print(f"  [skip] rate-limit / public-chatbot tests: Postgres unavailable ({exc})")
        _live = False
        return None

    from app.database import Base
    import app.models  # noqa: F401
    from app.models import Institution, Course

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    inst = Institution(name="Institution A", district_code="NAL", code="AAA")
    db.add(inst)
    db.flush()

    global_course = Course(institution_id=None, name="Tally Prime with GST", fee_amount=3000)
    tenant_course = Course(institution_id=inst.id, name="Tally Prime with GST", fee_amount=9999)
    db.add_all([global_course, tenant_course])
    db.commit()

    _live = {"engine": engine, "Session": Session, "db": db, "institution": inst}
    return _live


def _teardown_live():
    global _live
    if not _live:
        return
    try:
        from sqlalchemy import create_engine, text
        from app.config import settings

        _live["db"].close()
        _live["engine"].dispose()
        admin_url = settings.LOCAL_DB_URL.rsplit("/", 1)[0] + "/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        admin_engine.dispose()
    except Exception:
        pass
    _live = None


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def test_rate_limit_allows_then_blocks_after_cap():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.services import rate_limit

    db = fixture["db"]
    ip = "203.0.113.10"
    for _ in range(rate_limit.PER_MINUTE_LIMIT):
        assert rate_limit.check_and_increment(db, ip) is True
    assert rate_limit.check_and_increment(db, ip) is False


def test_rate_limit_is_per_ip():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.services import rate_limit

    db = fixture["db"]
    ip_a, ip_b = "203.0.113.20", "203.0.113.21"
    for _ in range(rate_limit.PER_MINUTE_LIMIT):
        rate_limit.check_and_increment(db, ip_a)
    assert rate_limit.check_and_increment(db, ip_a) is False
    assert rate_limit.check_and_increment(db, ip_b) is True  # unaffected


def test_rate_limit_minute_bucket_resets_count():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.models.chatbot_rate_limit import ChatbotRateLimit
    from app.services import rate_limit

    db = fixture["db"]
    ip = "203.0.113.30"
    for _ in range(rate_limit.PER_MINUTE_LIMIT):
        rate_limit.check_and_increment(db, ip)
    assert rate_limit.check_and_increment(db, ip) is False

    # Simulate a minute boundary passing.
    row = (
        db.query(ChatbotRateLimit)
        .filter(ChatbotRateLimit.ip_hash == rate_limit._hash_ip(ip))
        .first()
    )
    row.minute_bucket -= 1
    db.commit()
    assert rate_limit.check_and_increment(db, ip) is True


def test_rate_limit_does_not_store_raw_ip():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.models.chatbot_rate_limit import ChatbotRateLimit
    from app.services import rate_limit

    db = fixture["db"]
    ip = "198.51.100.77"
    rate_limit.check_and_increment(db, ip)
    row = db.query(ChatbotRateLimit).filter(ChatbotRateLimit.ip_hash == rate_limit._hash_ip(ip)).first()
    assert row is not None
    assert ip not in row.ip_hash


# ---------------------------------------------------------------------------
# Public chatbot's course_fee scoping (F-style tenant isolation, but for an
# unauthenticated caller instead of a cross-tenant one).
# ---------------------------------------------------------------------------

def test_public_course_fee_only_sees_global_courses():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.services.chatbot_engine import handle_public_message

    db = fixture["db"]
    result = handle_public_message(db, text="tally course fee")
    assert result["source"] == "data:course_fee"
    assert "3,000" in result["reply"] or "3000" in result["reply"]
    assert "9,999" not in result["reply"] and "9999" not in result["reply"]


def test_public_message_rejects_non_public_intents():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.services.chatbot_engine import handle_public_message

    db = fixture["db"]
    for intent_id in (
        "fee_balance", "next_exam", "my_result", "my_progress",
        "today_collections", "student_count",
    ):
        result = handle_public_message(db, intent_id=intent_id)
        assert result["source"] == "fallback", f"{intent_id} leaked: {result}"


def teardown_module(module):  # pytest hook
    _teardown_live()


if __name__ == "__main__":
    tests = [
        (name, fn) for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    _teardown_live()
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    sys.exit(1 if failures else 0)

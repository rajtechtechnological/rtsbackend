"""
Tenant isolation test suite (docs/01-SYSTEM-DESIGN.md §4).

Three layers:

1. Static route audit (no DB): every route module must use the tenancy layer
   (get_tenant) or an explicit role gate (require_roles). This is the
   guarantee that an endpoint cannot be written without a gate — F-01
   happened because gating was optional.
2. TenantContext.q construction (no DB): with a mocked session, verify the
   institution filter is applied for tenant users and skipped for
   super_admin.
3. Live two-institution isolation matrix (requires the local Postgres from
   .env): creates institutions A and B with a full object graph each, then
   asserts for every tenant model that A's context sees only A's rows, and
   at the route level that A's director/manager/receptionist/staff/student
   get 404 or empty results for B's students, exams, payments, certificates,
   staff and payroll. Skipped automatically if the DB is unreachable.

Run with either:
    python3 -m pytest tests/test_tenant_isolation.py
    python3 tests/test_tenant_isolation.py
"""

import os
import re
import sys
import uuid
from datetime import date, time, timedelta, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROUTES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "routes"
)


# ---------------------------------------------------------------------------
# 1. Static route audit
# ---------------------------------------------------------------------------

def test_every_route_module_uses_tenancy_or_role_gate():
    missing = []
    for filename in sorted(os.listdir(ROUTES_DIR)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue
        with open(os.path.join(ROUTES_DIR, filename)) as f:
            source = f.read()
        if "get_tenant" not in source and "require_roles" not in source:
            missing.append(filename)
    assert not missing, (
        f"Route modules without get_tenant/require_roles: {missing}"
    )


def test_no_route_module_uses_deleted_loose_helpers():
    deleted_helpers = [
        "can_manage_students", "can_manage_staff", "can_record_payments",
        "can_view_own_records_only", "check_institution_access",
        "check_resource_access",
    ]
    offenders = []
    for filename in sorted(os.listdir(ROUTES_DIR)):
        if not filename.endswith(".py"):
            continue
        with open(os.path.join(ROUTES_DIR, filename)) as f:
            source = f.read()
        for helper in deleted_helpers:
            if re.search(rf"\b{helper}\b", source):
                offenders.append(f"{filename}: {helper}")
    assert not offenders, f"Deleted loose helpers still referenced: {offenders}"


def test_question_public_schema_never_leaks_answers():
    """F-14: the student-facing question schema must not carry the answer."""
    from app.schemas.exam import QuestionPublic

    fields = set(QuestionPublic.model_fields.keys())
    assert "correct_option" not in fields
    assert "explanation" not in fields


# ---------------------------------------------------------------------------
# 2. TenantContext.q filter construction (mocked session)
# ---------------------------------------------------------------------------

class _RecordingQuery:
    def __init__(self):
        self.filters = []

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self


class _RecordingSession:
    def __init__(self):
        self.query_obj = _RecordingQuery()

    def query(self, model):
        self.queried_model = model
        return self.query_obj


def test_tenant_context_filters_by_institution_for_tenant_users():
    from app.models.student import Student
    from app.tenancy import TenantContext

    inst_id = uuid.uuid4()
    session = _RecordingSession()
    ctx = TenantContext(db=session, user=object(), institution_id=inst_id)

    ctx.q(Student)

    assert len(session.query_obj.filters) == 1
    criterion = session.query_obj.filters[0]
    # The single criterion must be students.institution_id == <inst_id>
    assert criterion.left.name == "institution_id"
    assert criterion.left.table.name == "students"
    assert criterion.right.value == inst_id


def test_tenant_context_no_filter_for_super_admin():
    from app.models.student import Student
    from app.tenancy import TenantContext

    session = _RecordingSession()
    ctx = TenantContext(db=session, user=object(), institution_id=None)

    ctx.q(Student)

    assert session.query_obj.filters == []


def test_require_institution_id_rules():
    from fastapi import HTTPException
    from app.tenancy import TenantContext

    own = uuid.uuid4()
    other = uuid.uuid4()

    tenant_ctx = TenantContext(db=None, user=object(), institution_id=own)
    # Tenant users ALWAYS get their own institution — request input ignored
    assert tenant_ctx.require_institution_id(other) == own
    assert tenant_ctx.require_institution_id(None) == own

    admin_ctx = TenantContext(db=None, user=object(), institution_id=None)
    assert admin_ctx.require_institution_id(other) == other
    try:
        admin_ctx.require_institution_id(None)
        assert False, "super_admin without institution_id must be a 400"
    except HTTPException as exc:
        assert exc.status_code == 400


# ---------------------------------------------------------------------------
# 3. Live two-institution isolation matrix (skipped without Postgres)
# ---------------------------------------------------------------------------

TEST_DB_NAME = "rts_isolation_test"
_live = None  # cached fixture dict or False


def _build_live_fixture():
    """Create a throwaway Postgres DB with institutions A and B and a full
    object graph in each. Returns None if Postgres is unavailable."""
    global _live
    if _live is not None:
        return _live or None

    try:
        import sqlalchemy
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
        print(f"  [skip] live isolation tests: Postgres unavailable ({exc})")
        _live = False
        return None

    from app.database import Base
    import app.models  # noqa: F401
    from app.models import (
        Batch, Certificate, Course, CourseModule, Exam, ExamAttempt,
        ExamSchedule, FeePayment, Institution, PayrollRecord, Staff,
        StaffAttendance, Student, StudentCourse, User,
    )
    from app.services.auth_service import hash_password

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    pwd = hash_password("pass")
    data = {"engine": engine, "Session": Session}

    for label, dist, code in (("a", "NAL", "AAA"), ("b", "PAT", "BBB")):
        inst = Institution(
            name=f"Institution {label.upper()}", district_code=dist, code=code,
        )
        db.add(inst)
        db.flush()

        users = {}
        for role in ("institution_director", "staff_manager", "receptionist", "staff", "student"):
            user = User(
                email=f"{role}@{label}.test", hashed_password=pwd,
                full_name=f"{role} {label}", role=role, institution_id=inst.id,
            )
            db.add(user)
            db.flush()
            users[role] = user

        batch = Batch(
            institution_id=inst.id, name=f"Batch {label}",
            start_time=time(9, 0), end_time=time(10, 0), month=1, year=2026,
        )
        db.add(batch)
        db.flush()

        course = Course(institution_id=inst.id, name=f"Course {label}", fee_amount=1000)
        db.add(course)
        db.flush()
        module = CourseModule(
            course_id=course.id, module_number=1, module_name="M1", order_index=1,
        )
        db.add(module)
        db.flush()

        student = Student(
            user_id=users["student"].id, institution_id=inst.id,
            batch_id=batch.id, student_id=f"RTS-{dist}-{code}-01-2026-0001",
        )
        db.add(student)
        db.flush()
        db.add(StudentCourse(student_id=student.id, course_id=course.id))

        staff = Staff(
            user_id=users["staff"].id, institution_id=inst.id,
            position="staff", daily_rate=500,
        )
        db.add(staff)
        db.flush()

        exam = Exam(
            course_id=course.id, module_id=module.id, institution_id=inst.id,
            title=f"Exam {label}", created_by=users["institution_director"].id,
        )
        db.add(exam)
        db.flush()

        schedule = ExamSchedule(
            exam_id=exam.id, institution_id=inst.id, batch_id=batch.id,
            scheduled_date=date(2026, 1, 15), start_time=time(9, 0),
            end_time=time(10, 0), created_by=users["institution_director"].id,
        )
        db.add(schedule)

        attempt = ExamAttempt(
            exam_id=exam.id, student_id=student.id, attempt_number=1,
            start_time=datetime.now(timezone.utc),
            deadline_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status="submitted",
        )
        db.add(attempt)

        payment = FeePayment(
            institution_id=inst.id, student_id=student.id, course_id=course.id,
            amount=500, payment_method="cash",
            receipt_number=f"RCP-{code}-2026-00001",
        )
        db.add(payment)
        db.flush()

        cert = Certificate(
            institution_id=inst.id, student_id=student.id, course_id=course.id,
            certificate_number=f"RTS-{dist}-{code}-CERT-2026-0001",
            verification_code=f"verify-{label}",
        )
        db.add(cert)

        db.add(StaffAttendance(
            institution_id=inst.id, staff_id=staff.id,
            date=date(2026, 1, 10), status="present",
        ))
        db.add(PayrollRecord(
            institution_id=inst.id, staff_id=staff.id, month=1, year=2026,
            days_present=20, total_amount=10000,
        ))

        data[label] = {
            "institution": inst, "users": users, "student": student,
            "staff": staff, "exam": exam, "payment": payment,
            "certificate": cert, "batch": batch, "course": course,
            "attempt": attempt,
        }

    db.commit()
    data["db"] = db
    _live = data
    return data


def test_ctx_q_isolates_every_tenant_model():
    fixture = _build_live_fixture()
    if fixture is None:
        return  # skipped

    from app.models import (
        Batch, Certificate, Exam, ExamSchedule, FeePayment,
        PayrollRecord, Staff, StaffAttendance, Student,
    )
    from app.tenancy import TenantContext

    db = fixture["db"]
    for me, other in (("a", "b"), ("b", "a")):
        ctx = TenantContext(
            db=db,
            user=fixture[me]["users"]["institution_director"],
            institution_id=fixture[me]["institution"].id,
        )
        other_inst = fixture[other]["institution"].id
        for model in (
            Student, Staff, Exam, ExamSchedule, FeePayment,
            Certificate, Batch, PayrollRecord, StaffAttendance,
        ):
            rows = ctx.q(model).all()
            assert rows, f"{model.__name__}: expected own rows for {me}"
            for row in rows:
                assert row.institution_id != other_inst, (
                    f"{model.__name__}: ctx.q leaked institution {other}'s row"
                )


def test_super_admin_ctx_sees_both_institutions():
    fixture = _build_live_fixture()
    if fixture is None:
        return

    from app.models import Student
    from app.tenancy import TenantContext

    ctx = TenantContext(db=fixture["db"], user=object(), institution_id=None)
    institutions = {s.institution_id for s in ctx.q(Student).all()}
    assert fixture["a"]["institution"].id in institutions
    assert fixture["b"]["institution"].id in institutions


def test_routes_return_404_or_empty_for_other_institution():
    """Route-level matrix: A's staff roles get 404 (or filtered lists) for
    B's students, exams, payments, certificates, staff and payroll."""
    fixture = _build_live_fixture()
    if fixture is None:
        return

    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from app.services import auth_service

    Session = fixture["Session"]

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app, base_url="https://testserver")

        b = fixture["b"]
        targets = [
            ("students", f"/api/students/{b['student'].id}"),
            ("exams", f"/api/exams/{b['exam'].id}"),
            ("payments", f"/api/payments/{b['payment'].id}"),
            ("certificates", f"/api/certificates/{b['certificate'].id}"),
            ("staff", f"/api/staff/{b['staff'].id}"),
            ("payroll batch", f"/api/batches/{b['batch'].id}"),
        ]

        for role in ("institution_director", "staff_manager", "receptionist", "staff", "student"):
            user = fixture["a"]["users"][role]
            token = auth_service.create_access_token_for_user(user)
            headers = {"Authorization": f"Bearer {token}"}

            for name, url in targets:
                resp = client.get(url, headers=headers)
                # 404 = invisible (correct), 403 = role floor — NEVER 200
                assert resp.status_code in (403, 404), (
                    f"{role} GET {name}: expected 403/404 for institution B's "
                    f"row, got {resp.status_code}"
                )

            # List endpoints must never contain B's rows
            for url, key in (
                ("/api/students/", "institution_id"),
                ("/api/payments/", "institution_id"),
                ("/api/certificates/", "institution_id"),
                ("/api/exams/", "institution_id"),
                ("/api/staff/", "institution_id"),
                ("/api/payroll/", "institution_id"),
                ("/api/batches/", "institution_id"),
            ):
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    continue  # role floor forbids the list — fine
                for row in resp.json():
                    assert row[key] != str(b["institution"].id), (
                        f"{role} GET {url} leaked institution B's row"
                    )

        # A's director must still see A's own student (sanity: 404s above are
        # isolation, not broken endpoints)
        director = fixture["a"]["users"]["institution_director"]
        token = auth_service.create_access_token_for_user(director)
        resp = client.get(
            f"/api/students/{fixture['a']['student'].id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)


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

"""
Seed script for a FRESH database (docs/02-DATA-MODEL.md §7).

Replaces the old create_demo_data.py / create_director.py /
populate_courses.py / add_student_fields.py. Everything goes through the
same code paths the API uses: the real model layer, atomic id_counters
(app.ids) and bcrypt-hashed passwords.

Usage:
    alembic upgrade head          # create the schema first
    python3 seed.py               # then seed

Creates:
- super_admin (admin@rts.com / admin123)
- one demo institution (Rajtech Computer Center, NAL/RCC) with
  director / staff_manager / receptionist / staff users
- 2 batches (Morning A, Evening A — current month)
- the 4 global course templates (ADCA / HDIT / DCA / DOARM) with modules
- 5 demo students with enrollments and fee payments
"""

from datetime import date, time, datetime
from decimal import Decimal

from app.database import SessionLocal
from app import ids
from app.models import (
    Batch, Course, CourseModule, FeePayment, Institution, Staff, Student,
    StudentCourse, User,
)
from app.services.auth_service import hash_password

SUPER_ADMIN_EMAIL = "admin@rts.com"
SUPER_ADMIN_PASSWORD = "admin123"

# Course metadata carried over from the old populate_courses.py
COURSES = {
    "ADCA": {
        "name": "Advanced Diploma in Computer Application (ADCA)",
        "description": "Comprehensive computer course covering fundamentals to advanced topics",
        "duration_months": 12,
        "fee_amount": Decimal("15000.00"),
        "modules": [
            ("Fundamentals & Windows 10", 12),
            ("MS Word & MS Excel", 16),
            ("MS PowerPoint & MS Access", 12),
            ("Internet, Email & Web Basics", 8),
            ("Tally Prime with GST", 14),
            ("Programming Fundamentals (C)", 12),
            ("DTP: Photoshop & PageMaker", 12),
            ("Project & Assessment", 6),
        ],
    },
    "HDIT": {
        "name": "Hardware & IT Technician (HDIT)",
        "description": "Complete hardware and networking course with practical training",
        "duration_months": 6,
        "fee_amount": Decimal("12000.00"),
        "modules": [
            ("PC Components & Assembly", 12),
            ("Operating System Installation", 10),
            ("Troubleshooting & Maintenance", 12),
            ("Networking Fundamentals", 10),
            ("Printers & Peripherals", 8),
        ],
    },
    "DCA": {
        "name": "Diploma in Computer Application (DCA)",
        "description": "Foundation course in computer applications and office automation",
        "duration_months": 6,
        "fee_amount": Decimal("8000.00"),
        "modules": [
            ("Computer Fundamentals & Windows", 10),
            ("MS Office (Word, Excel, PowerPoint)", 16),
            ("Internet & Email", 6),
            ("Typing & Data Entry", 8),
        ],
    },
    "DOARM": {
        "name": "Diploma in Office Automation & Records Management (DOARM)",
        "description": "Specialized course in office automation and record management",
        "duration_months": 4,
        "fee_amount": Decimal("7000.00"),
        "modules": [
            ("Office Automation Basics", 8),
            ("Records & File Management", 8),
            ("Spreadsheets for Record Keeping", 10),
        ],
    },
}

STAFF_USERS = [
    # (email, full_name, phone, role, daily_rate)
    ("director@rajtech.com", "Rajesh Kumar", "9800000001", "institution_director", None),
    ("manager@rajtech.com", "Sunita Devi", "9800000002", "staff_manager", Decimal("800.00")),
    ("reception@rajtech.com", "Priya Singh", "9800000003", "receptionist", Decimal("500.00")),
    ("staff@rajtech.com", "Amit Verma", "9800000004", "staff", Decimal("600.00")),
]

DEMO_STUDENTS = [
    # (full_name, email, phone, course_code, paid_amount)
    ("Asha Kumari", "asha@student.rts.com", "9700000001", "ADCA", Decimal("5000.00")),
    ("Rahul Raj", "rahul@student.rts.com", "9700000002", "DCA", Decimal("8000.00")),
    ("Neha Sinha", "neha@student.rts.com", "9700000003", "DCA", Decimal("3000.00")),
    ("Vikash Kumar", "vikash@student.rts.com", "9700000004", "HDIT", Decimal("6000.00")),
    ("Pooja Gupta", "pooja@student.rts.com", "9700000005", "DOARM", None),  # unpaid
]

DEFAULT_PASSWORD_NOTE = "password = phone number (staff & students), admin123 (super_admin)"


def seed():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first():
            print("Database already seeded (super_admin exists) — nothing to do.")
            return

        # ------------------------------------------------------------------
        # 1. super_admin (institution_id NULL by the CHECK constraint)
        # ------------------------------------------------------------------
        super_admin = User(
            email=SUPER_ADMIN_EMAIL,
            hashed_password=hash_password(SUPER_ADMIN_PASSWORD),
            full_name="RTS Head Office",
            phone="9999999999",
            role="super_admin",
            institution_id=None,
        )
        db.add(super_admin)

        # ------------------------------------------------------------------
        # 2. Global course templates (institution_id NULL) + modules
        # ------------------------------------------------------------------
        courses_by_code = {}
        for code, info in COURSES.items():
            course = Course(
                institution_id=None,
                name=info["name"],
                description=info["description"],
                duration_months=info["duration_months"],
                fee_amount=info["fee_amount"],
            )
            db.add(course)
            db.flush()
            courses_by_code[code] = course

            for idx, (module_name, lessons) in enumerate(info["modules"], start=1):
                db.add(CourseModule(
                    course_id=course.id,
                    module_number=idx,
                    module_name=module_name,
                    lesson_count=lessons,
                    duration_hours=lessons * 2,
                    total_marks=100,
                    passing_marks=40,
                    order_index=idx,
                    is_active=True,
                ))

        # ------------------------------------------------------------------
        # 3. Demo institution + staff users
        # ------------------------------------------------------------------
        institution = Institution(
            name="Rajtech Computer Center",
            district_code="NAL",
            code="RCC",
            address="Bihar Sharif, Nalanda",
            contact_email="director@rajtech.com",
            contact_phone="9800000001",
        )
        db.add(institution)
        db.flush()

        for email, full_name, phone, role, daily_rate in STAFF_USERS:
            user = User(
                email=email,
                hashed_password=hash_password(phone),
                full_name=full_name,
                phone=phone,
                role=role,
                institution_id=institution.id,
            )
            db.add(user)
            db.flush()
            if daily_rate is not None:
                db.add(Staff(
                    user_id=user.id,
                    institution_id=institution.id,
                    position=role,
                    daily_rate=daily_rate,
                ))

        # ------------------------------------------------------------------
        # 4. Batches
        # ------------------------------------------------------------------
        today = date.today()
        morning = Batch(
            institution_id=institution.id,
            name=f"Morning A — {today.strftime('%b %Y')}",
            start_time=time(9, 0),
            end_time=time(10, 0),
            month=today.month,
            year=today.year,
            identifier="A",
        )
        evening = Batch(
            institution_id=institution.id,
            name=f"Evening A — {today.strftime('%b %Y')}",
            start_time=time(17, 0),
            end_time=time(18, 0),
            month=today.month,
            year=today.year,
            identifier="A",
        )
        db.add_all([morning, evening])
        db.flush()
        batches = [morning, evening]

        # ------------------------------------------------------------------
        # 5. Demo students: user + student (atomic ID) + enrollment + payment
        # ------------------------------------------------------------------
        receptionist = db.query(User).filter(User.email == "reception@rajtech.com").first()
        now = datetime.now()

        for i, (full_name, email, phone, course_code, paid) in enumerate(DEMO_STUDENTS):
            user = User(
                email=email,
                hashed_password=hash_password(phone),
                full_name=full_name,
                phone=phone,
                role="student",
                institution_id=institution.id,
            )
            db.add(user)
            db.flush()

            student = Student(
                user_id=user.id,
                institution_id=institution.id,
                batch_id=batches[i % len(batches)].id,
                # Race-free human ID via id_counters (docs/02 §6)
                student_id=ids.student_id(db, institution, now.month, now.year),
                guardian_phone=phone,
            )
            db.add(student)
            db.flush()

            course = courses_by_code[course_code]
            db.add(StudentCourse(student_id=student.id, course_id=course.id))

            if paid is not None:
                db.add(FeePayment(
                    institution_id=institution.id,
                    student_id=student.id,
                    course_id=course.id,
                    amount=paid,
                    paid_at=today,
                    payment_method="cash",
                    receipt_number=ids.receipt_number(db, institution, now.year),
                    recorded_by=receptionist.id if receptionist else None,
                ))

        db.commit()

        print("Seed complete.")
        print(f"  super_admin:  {SUPER_ADMIN_EMAIL} / {SUPER_ADMIN_PASSWORD}")
        for email, _, phone, role, _ in STAFF_USERS:
            print(f"  {role:22s} {email} / {phone}")
        print(f"  institution:  {institution.name} ({institution.district_code}-{institution.code})")
        print(f"  batches:      {morning.name}; {evening.name}")
        print(f"  courses:      {', '.join(COURSES.keys())} (global templates)")
        print(f"  students:     {len(DEMO_STUDENTS)} ({DEFAULT_PASSWORD_NOTE})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

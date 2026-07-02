"""
Script to create demo users for testing
Creates: Super Admin, Institution, Director, Accountant, Receptionist, Staff, and Student
"""

from app.database import SessionLocal
from app.models.user import User
from app.models.institution import Institution
from app.models.student import Student
from app.models.staff import Staff
from app.models.course import Course
from app.models.student_course import StudentCourse
from app.models.course_module import StudentModuleProgress, CourseModule
from app.services.auth_service import hash_password
from datetime import date, datetime
import uuid

def create_demo_data():
    """Create all demo users and data"""
    db = SessionLocal()

    try:
        print("🚀 Starting demo data creation...\n")

        # ============ 1. Create Super Admin (Director) ============
        print("1️⃣  Creating Super Admin...")
        super_admin_email = "director@rajtech.com"
        super_admin = db.query(User).filter(User.email == super_admin_email).first()

        if not super_admin:
            super_admin = User(
                id=uuid.uuid4(),
                email=super_admin_email,
                hashed_password=hash_password("director123"),
                full_name="System Director",
                phone="+91 9876543210",
                role="super_admin",
                institution_id=None,
                is_active=True
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"   ✅ Super Admin created")
            print(f"      Email: {super_admin_email}")
            print(f"      Password: director123\n")
        else:
            print(f"   ℹ️  Super Admin already exists\n")

        # ============ 2. Create Demo Institution ============
        print("2️⃣  Creating Demo Institution...")
        demo_institution = db.query(Institution).filter(
            Institution.name == "Demo Raj Technical Institute"
        ).first()

        if not demo_institution:
            demo_institution = Institution(
                id=uuid.uuid4(),
                name="Demo Raj Technical Institute",
                district_code="DEMO",
                address="123 Demo Street, Test City, 123456",
                contact_email="demo@rajtech.com",
                contact_phone="+91 9876543211",
                created_at=datetime.utcnow()
            )
            db.add(demo_institution)
            db.commit()
            db.refresh(demo_institution)
            print(f"   ✅ Institution created")
            print(f"      Name: {demo_institution.name}")
            print(f"      District Code: {demo_institution.district_code}\n")
        else:
            print(f"   ℹ️  Institution already exists\n")

        # ============ 3. Create Institution Director ============
        print("3️⃣  Creating Institution Director...")
        director_email = "director.demo@rajtech.com"
        director_user = db.query(User).filter(User.email == director_email).first()

        if not director_user:
            director_user = User(
                id=uuid.uuid4(),
                email=director_email,
                hashed_password=hash_password("director123"),
                full_name="Demo Institution Director",
                phone="+91 9876543212",
                role="institution_director",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(director_user)
            db.commit()
            db.refresh(director_user)

            # Update institution with director
            demo_institution.director_id = director_user.id
            db.commit()

            print(f"   ✅ Institution Director created")
            print(f"      Email: {director_email}")
            print(f"      Password: director123\n")
        else:
            print(f"   ℹ️  Institution Director already exists\n")

        # ============ 4. Create Accountant ============
        print("4️⃣  Creating Accountant...")
        accountant_email = "accountant@rajtech.com"
        accountant_user = db.query(User).filter(User.email == accountant_email).first()

        if not accountant_user:
            accountant_user = User(
                id=uuid.uuid4(),
                email=accountant_email,
                hashed_password=hash_password("accountant123"),
                full_name="Demo Accountant",
                phone="+91 9876543213",
                role="accountant",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(accountant_user)
            db.commit()
            db.refresh(accountant_user)

            accountant_staff = Staff(
                id=uuid.uuid4(),
                user_id=accountant_user.id,
                institution_id=demo_institution.id,
                position="Senior Accountant",
                daily_rate=500.0,
                joining_date=date.today()
            )
            db.add(accountant_staff)
            db.commit()

            print(f"   ✅ Accountant created")
            print(f"      Email: {accountant_email}")
            print(f"      Password: accountant123\n")
        else:
            print(f"   ℹ️  Accountant already exists\n")

        # ============ 5. Create Receptionist ============
        print("5️⃣  Creating Receptionist...")
        receptionist_email = "receptionist@rajtech.com"
        receptionist_user = db.query(User).filter(User.email == receptionist_email).first()

        if not receptionist_user:
            receptionist_user = User(
                id=uuid.uuid4(),
                email=receptionist_email,
                hashed_password=hash_password("receptionist123"),
                full_name="Demo Receptionist",
                phone="+91 9876543214",
                role="receptionist",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(receptionist_user)
            db.commit()
            db.refresh(receptionist_user)

            receptionist_staff = Staff(
                id=uuid.uuid4(),
                user_id=receptionist_user.id,
                institution_id=demo_institution.id,
                position="Front Desk Receptionist",
                daily_rate=300.0,
                joining_date=date.today()
            )
            db.add(receptionist_staff)
            db.commit()

            print(f"   ✅ Receptionist created")
            print(f"      Email: {receptionist_email}")
            print(f"      Password: receptionist123\n")
        else:
            print(f"   ℹ️  Receptionist already exists\n")

        # ============ 6. Create Staff Manager ============
        print("6️⃣  Creating Staff Manager...")
        manager_email = "manager@rajtech.com"
        manager_user = db.query(User).filter(User.email == manager_email).first()

        if not manager_user:
            manager_user = User(
                id=uuid.uuid4(),
                email=manager_email,
                hashed_password=hash_password("manager123"),
                full_name="Demo Staff Manager",
                phone="+91 9876543215",
                role="staff_manager",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(manager_user)
            db.commit()
            db.refresh(manager_user)

            manager_staff = Staff(
                id=uuid.uuid4(),
                user_id=manager_user.id,
                institution_id=demo_institution.id,
                position="Operations Manager",
                daily_rate=600.0,
                joining_date=date.today()
            )
            db.add(manager_staff)
            db.commit()

            print(f"   ✅ Staff Manager created")
            print(f"      Email: {manager_email}")
            print(f"      Password: manager123\n")
        else:
            print(f"   ℹ️  Staff Manager already exists\n")

        # ============ 7. Create Regular Staff ============
        print("7️⃣  Creating Regular Staff...")
        staff_email = "staff@rajtech.com"
        staff_user = db.query(User).filter(User.email == staff_email).first()

        if not staff_user:
            staff_user = User(
                id=uuid.uuid4(),
                email=staff_email,
                hashed_password=hash_password("staff123"),
                full_name="Demo Staff Member",
                phone="+91 9876543216",
                role="staff",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(staff_user)
            db.commit()
            db.refresh(staff_user)

            staff_member = Staff(
                id=uuid.uuid4(),
                user_id=staff_user.id,
                institution_id=demo_institution.id,
                position="Teaching Staff",
                daily_rate=400.0,
                joining_date=date.today()
            )
            db.add(staff_member)
            db.commit()

            print(f"   ✅ Regular Staff created")
            print(f"      Email: {staff_email}")
            print(f"      Password: staff123\n")
        else:
            print(f"   ℹ️  Regular Staff already exists\n")

        # ============ 8. Create Student ============
        print("8️⃣  Creating Demo Student...")
        student_email = "student@rajtech.com"
        student_user = db.query(User).filter(User.email == student_email).first()

        if not student_user:
            student_user = User(
                id=uuid.uuid4(),
                email=student_email,
                hashed_password=hash_password("student123"),
                full_name="Demo Student",
                phone="+91 9876543217",
                role="student",
                institution_id=demo_institution.id,
                is_active=True
            )
            db.add(student_user)
            db.commit()
            db.refresh(student_user)

            # Generate student ID
            student_count = db.query(Student).filter(
                Student.institution_id == demo_institution.id
            ).count()
            student_id = f"RTS-{demo_institution.district_code}-{date.today().strftime('%m-%Y')}-{str(student_count + 1).zfill(4)}"

            demo_student = Student(
                id=uuid.uuid4(),
                user_id=student_user.id,
                institution_id=demo_institution.id,
                student_id=student_id,
                date_of_birth=date(2000, 1, 1),
                father_name="Demo Father",
                guardian_name="Demo Guardian",
                guardian_phone="+91 9876543218",
                address="456 Student Street, Test City, 123456",
                aadhar_number="123456789012",
                apaar_id="APAAR123456789",
                last_qualification="12th Pass",
                # Batch Information
                batch_time="10AM-11AM",
                batch_month=date.today().strftime("%m"),  # Current month
                batch_year=str(date.today().year),  # Current year
                batch_identifier="A",
                enrollment_date=date.today()
            )
            db.add(demo_student)
            db.commit()
            db.refresh(demo_student)

            print(f"   ✅ Student created")
            print(f"      Email: {student_email}")
            print(f"      Password: student123")
            print(f"      Student ID: {student_id}")
            print(f"      APAAR ID: APAAR123456789")
            print(f"      Batch: 10AM-11AM | {date.today().strftime('%B %Y')} (A)\n")

            # ============ 9. Enroll Student in DCA Course ============
            print("9️⃣  Enrolling student in DCA course...")
            # Try to find DCA course with different search patterns
            dca_course = db.query(Course).filter(
                Course.name.ilike("%Diploma in Computer Application%")
            ).first()

            if not dca_course:
                dca_course = db.query(Course).filter(
                    Course.name.ilike("%DCA%")
                ).first()

            # If still not found, get any available course
            if not dca_course:
                dca_course = db.query(Course).first()

            if dca_course:
                # Check if already enrolled
                existing_enrollment = db.query(StudentCourse).filter(
                    StudentCourse.student_id == demo_student.id,
                    StudentCourse.course_id == dca_course.id
                ).first()

                if not existing_enrollment:
                    enrollment = StudentCourse(
                        id=uuid.uuid4(),
                        student_id=demo_student.id,
                        course_id=dca_course.id,
                        enrollment_date=date.today(),
                        status="active"
                    )
                    db.add(enrollment)
                    db.commit()
                    db.refresh(enrollment)

                    print(f"   ✅ Student enrolled in {dca_course.name}")

                    # ============ 10. Initialize Module Progress ============
                    print("🔟 Initializing module progress...")
                    modules = db.query(CourseModule).filter(
                        CourseModule.course_id == dca_course.id,
                        CourseModule.is_active == True
                    ).order_by(CourseModule.order_index).all()

                    if modules:
                        for module in modules:
                            existing_progress = db.query(StudentModuleProgress).filter(
                                StudentModuleProgress.student_id == demo_student.id,
                                StudentModuleProgress.module_id == module.id
                            ).first()

                            if not existing_progress:
                                progress = StudentModuleProgress(
                                    id=uuid.uuid4(),
                                    student_id=demo_student.id,
                                    course_id=dca_course.id,
                                    module_id=module.id,
                                    enrollment_id=enrollment.id,
                                    status='not_started'
                                )
                                db.add(progress)

                        db.commit()
                        print(f"   ✅ Initialized progress for {len(modules)} modules\n")
                    else:
                        print(f"   ⚠️  No modules found for {dca_course.name}\n")
                else:
                    print(f"   ℹ️  Student already enrolled in {dca_course.name}\n")
            else:
                print(f"   ⚠️  No courses found in database!")
                print(f"   💡 Run 'python populate_courses.py --yes' to add courses first\n")
        else:
            print(f"   ℹ️  Student already exists\n")

        print("=" * 60)
        print("✅ Demo data creation complete!\n")
        print("📋 Created Users Summary:")
        print("=" * 60)
        print("\n🔐 Login Credentials:\n")
        print("1. Super Admin:")
        print("   Email: director@rajtech.com")
        print("   Password: director123")
        print("   Role: super_admin\n")

        print("2. Institution Director:")
        print("   Email: director.demo@rajtech.com")
        print("   Password: director123")
        print("   Role: institution_director\n")

        print("3. Accountant:")
        print("   Email: accountant@rajtech.com")
        print("   Password: accountant123")
        print("   Role: accountant\n")

        print("4. Receptionist:")
        print("   Email: receptionist@rajtech.com")
        print("   Password: receptionist123")
        print("   Role: receptionist\n")

        print("5. Staff Manager:")
        print("   Email: manager@rajtech.com")
        print("   Password: manager123")
        print("   Role: staff_manager\n")

        print("6. Regular Staff:")
        print("   Email: staff@rajtech.com")
        print("   Password: staff123")
        print("   Role: staff\n")

        print("7. Student:")
        print("   Email: student@rajtech.com")
        print("   Password: student123")
        print("   Role: student")
        if 'demo_student' in locals():
            print(f"   Student ID: {demo_student.student_id}")
            print(f"   APAAR ID: {demo_student.apaar_id}")
            print(f"   Batch: {demo_student.batch_time} | {demo_student.batch_month}/{demo_student.batch_year} ({demo_student.batch_identifier})")
            print(f"   Enrolled in: DCA course\n")

        print("=" * 60)
        print("\n⚠️  IMPORTANT: Change these passwords after first login!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error creating demo data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 DEMO DATA CREATION SCRIPT")
    print("=" * 60)
    print("\nThis script will create the following demo accounts:")
    print("  • Super Admin (Director)")
    print("  • Demo Institution")
    print("  • Institution Director")
    print("  • Accountant")
    print("  • Receptionist")
    print("  • Staff Manager")
    print("  • Regular Staff")
    print("  • Student (enrolled in DCA course)")
    print("\n" + "=" * 60 + "\n")

    create_demo_data()

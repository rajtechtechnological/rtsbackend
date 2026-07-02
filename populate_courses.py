"""
Script to populate courses and modules from the Excel syllabus file.
Run this script to add ADCA, HDIT, DCA, and DOARM courses with their modules.
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal, engine, Base
from app.models.course import Course
from app.models.course_module import CourseModule
import sys
from pathlib import Path

# Excel file path
EXCEL_PATH = "/Users/keshavraj/Downloads/SYLLABUS OF HDIT.xlsx"


def read_course_from_sheet(sheet_name: str, excel_file: str) -> dict:
    """Read course data from a specific sheet"""
    try:
        # Read the sheet
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Remove completely empty rows
        df = df.dropna(how='all')

        modules = []
        current_module = None
        module_number = 0
        lesson_count = 0
        module_lessons = []

        for idx, row in df.iterrows():
            # Convert row to string to check for module headers
            row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])

            # Check if this is a module header (contains "Module" or "MODULE")
            if 'module' in row_str.lower() or 'MODULE' in row_str:
                # Save previous module if exists
                if current_module:
                    modules.append({
                        'module_number': module_number,
                        'module_name': current_module,
                        'description': '\n'.join(module_lessons),
                        'lesson_count': lesson_count
                    })

                # Start new module
                module_number += 1
                current_module = row_str.strip()
                lesson_count = 0
                module_lessons = []

            elif current_module:
                # This is a lesson/topic under current module
                # Get the first non-empty value as lesson name
                lesson = None
                for col in df.columns:
                    if pd.notna(row[col]) and str(row[col]).strip():
                        lesson = str(row[col]).strip()
                        break

                if lesson and lesson.lower() not in ['module', 'nan']:
                    module_lessons.append(lesson)
                    lesson_count += 1

        # Don't forget the last module
        if current_module:
            modules.append({
                'module_number': module_number,
                'module_name': current_module,
                'description': '\n'.join(module_lessons),
                'lesson_count': lesson_count
            })

        return modules

    except Exception as e:
        print(f"Error reading sheet {sheet_name}: {e}")
        return []


def get_course_info(course_code: str) -> dict:
    """Get course metadata based on course code"""
    courses_info = {
        'ADCA': {
            'name': 'Advanced Diploma in Computer Application (ADCA)',
            'description': 'Comprehensive computer course covering fundamentals to advanced topics',
            'duration_months': 12,
            'fee_amount': 15000.00
        },
        'HDIT': {
            'name': 'Hardware & IT Technician (HDIT)',
            'description': 'Complete hardware and networking course with practical training',
            'duration_months': 6,
            'fee_amount': 12000.00
        },
        'DCA': {
            'name': 'Diploma in Computer Application (DCA)',
            'description': 'Foundation course in computer applications and office automation',
            'duration_months': 6,
            'fee_amount': 8000.00
        },
        'DOARM': {
            'name': 'Diploma in Office Automation & Records Management (DOARM)',
            'description': 'Specialized course in office automation and record management',
            'duration_months': 4,
            'fee_amount': 7000.00
        }
    }
    return courses_info.get(course_code, {})


def populate_courses_and_modules():
    """Main function to populate courses and modules"""

    # Check if Excel file exists
    if not Path(EXCEL_PATH).exists():
        print(f"❌ Excel file not found at: {EXCEL_PATH}")
        print("Please update the EXCEL_PATH variable in this script.")
        return

    print(f"📖 Reading courses from: {EXCEL_PATH}\n")

    # Create database session
    db = SessionLocal()

    try:
        # Read all sheets from Excel
        excel_file = pd.ExcelFile(EXCEL_PATH)
        sheet_names = excel_file.sheet_names

        print(f"Found {len(sheet_names)} sheets in Excel file")
        print(f"Sheets: {', '.join(sheet_names)}\n")

        # Map sheet names to course codes
        # You may need to adjust these based on actual sheet names
        sheet_to_course = {}
        for sheet in sheet_names:
            sheet_upper = sheet.upper()
            if 'ADCA' in sheet_upper:
                sheet_to_course[sheet] = 'ADCA'
            elif 'HDIT' in sheet_upper:
                sheet_to_course[sheet] = 'HDIT'
            elif 'DCA' in sheet_upper and 'ADCA' not in sheet_upper:
                sheet_to_course[sheet] = 'DCA'
            elif 'DOARM' in sheet_upper:
                sheet_to_course[sheet] = 'DOARM'

        if not sheet_to_course:
            print("⚠️  Could not identify course sheets. Found sheets:", sheet_names)
            print("Please manually map sheet names to course codes in the script.")
            return

        print(f"Identified courses: {list(sheet_to_course.values())}\n")
        print("=" * 60)

        for sheet_name, course_code in sheet_to_course.items():
            print(f"\n📚 Processing {course_code} from sheet: {sheet_name}")

            # Get course info
            course_info = get_course_info(course_code)
            if not course_info:
                print(f"⚠️  No metadata found for {course_code}, skipping...")
                continue

            # Check if course already exists
            existing_course = db.query(Course).filter(
                Course.name == course_info['name']
            ).first()

            if existing_course:
                print(f"✓ Course '{course_info['name']}' already exists (ID: {existing_course.id})")
                course = existing_course
            else:
                # Create new course (institution_id=None for global courses)
                course = Course(
                    institution_id=None,  # Global course, not tied to specific institution
                    name=course_info['name'],
                    description=course_info['description'],
                    duration_months=course_info['duration_months'],
                    fee_amount=course_info['fee_amount']
                )
                db.add(course)
                db.commit()
                db.refresh(course)
                print(f"✓ Created course: {course_info['name']} (ID: {course.id})")

            # Read modules from Excel
            modules_data = read_course_from_sheet(sheet_name, EXCEL_PATH)

            if not modules_data:
                print(f"⚠️  No modules found for {course_code}")
                continue

            print(f"  Found {len(modules_data)} modules")

            # Create modules
            created_count = 0
            for idx, module_data in enumerate(modules_data):
                # Check if module already exists
                existing_module = db.query(CourseModule).filter(
                    CourseModule.course_id == course.id,
                    CourseModule.module_number == module_data['module_number']
                ).first()

                if existing_module:
                    print(f"  - Module {module_data['module_number']}: Already exists")
                    continue

                # Create new module
                module = CourseModule(
                    course_id=course.id,
                    module_number=module_data['module_number'],
                    module_name=module_data['module_name'],
                    description=module_data['description'],
                    lesson_count=module_data['lesson_count'],
                    duration_hours=module_data['lesson_count'] * 2,  # Estimate: 2 hours per lesson
                    total_marks=100,
                    passing_marks=40,
                    order_index=idx + 1,
                    has_online_test=False,  # Will be enabled in future
                    is_active=True
                )
                db.add(module)
                created_count += 1
                print(f"  ✓ Module {module_data['module_number']}: {module_data['module_name']} ({module_data['lesson_count']} lessons)")

            db.commit()
            print(f"\n  Summary: Created {created_count} new modules for {course_code}")

        print("\n" + "=" * 60)
        print("\n✅ Course and module population complete!")

        # Print summary statistics
        total_courses = db.query(Course).count()
        total_modules = db.query(CourseModule).count()

        print(f"\n📊 Database Statistics:")
        print(f"   Total Courses: {total_courses}")
        print(f"   Total Modules: {total_modules}")

        # Print breakdown by course
        print(f"\n📋 Modules by Course:")
        for sheet_name, course_code in sheet_to_course.items():
            course_info = get_course_info(course_code)
            course = db.query(Course).filter(Course.name == course_info['name']).first()
            if course:
                module_count = db.query(CourseModule).filter(CourseModule.course_id == course.id).count()
                total_lessons = db.query(CourseModule).filter(CourseModule.course_id == course.id).with_entities(
                    func.sum(CourseModule.lesson_count)
                ).scalar() or 0
                print(f"   {course_code}: {module_count} modules, {total_lessons} total lessons")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Course & Module Population Script")
    print("=" * 60)

    # Check for --yes flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--yes', '-y']:
        populate_courses_and_modules()
    else:
        # Confirm before proceeding
        print("\nThis script will:")
        print("1. Read course data from the Excel file")
        print("2. Create courses (ADCA, HDIT, DCA, DOARM) if they don't exist")
        print("3. Create modules for each course based on the syllabus")
        print("\nExisting data will not be duplicated.\n")
        print("Run with --yes flag to skip this prompt: python populate_courses.py --yes\n")

        try:
            response = input("Do you want to proceed? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                populate_courses_and_modules()
            else:
                print("\n❌ Operation cancelled.")
        except EOFError:
            print("\n❌ Cannot read input in non-interactive mode. Use --yes flag.")

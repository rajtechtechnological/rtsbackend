"""
Migration script to add new fields to students table:
- father_name
- aadhar_number
- last_qualification
"""

from sqlalchemy import text
from app.database import engine

def add_student_fields():
    """Add new columns to students table"""

    migrations = [
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS father_name VARCHAR;",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS aadhar_number VARCHAR;",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS last_qualification VARCHAR;",
    ]

    print("🔄 Adding new fields to students table...\n")

    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                print(f"✅ Executed: {migration}")
            except Exception as e:
                print(f"⚠️  {migration}")
                print(f"   Error: {e}\n")

    print("\n✅ Migration complete!")
    print("\nNew fields added to students table:")
    print("  - father_name (VARCHAR)")
    print("  - aadhar_number (VARCHAR)")
    print("  - last_qualification (VARCHAR)")

if __name__ == "__main__":
    add_student_fields()

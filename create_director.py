"""
Script to create a director user account in the database
Run this after setting up the database and tables
"""

from app.database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
import uuid

def create_director():
    """Create a fixed director account"""
    db = SessionLocal()

    try:
        # Check if director already exists
        existing = db.query(User).filter(User.email == "director@rajtech.com").first()

        if existing:
            print("❌ Director account already exists!")
            print(f"Email: {existing.email}")
            print(f"Role: {existing.role}")
            return

        # Create director user
        director = User(
            id=uuid.uuid4(),
            email="director@rajtech.com",
            hashed_password=hash_password("director123"),  # Password: director123
            full_name="System Director",
            phone="+91 9876543210",
            role="super_admin",
            institution_id=None,  # Director manages all institutions
            is_active=True
        )

        db.add(director)
        db.commit()
        db.refresh(director)

        print("✅ Director account created successfully!")
        print(f"📧 Email: director@rajtech.com")
        print(f"🔑 Password: director123")
        print(f"👤 Role: super_admin")
        print(f"🆔 ID: {director.id}")
        print("\n⚠️  IMPORTANT: Change this password after first login!")

    except Exception as e:
        print(f"❌ Error creating director: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating director account...\n")
    create_director()

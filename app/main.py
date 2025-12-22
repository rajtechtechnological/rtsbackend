from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.config import settings
from pathlib import Path

# Import routes (we'll create these next)
from app.routes import auth, institutions, students, courses, staff, attendance, payroll, certificates

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Education Management API",
    description="Multi-tenant education management platform API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for local file storage
if settings.USE_LOCAL_STORAGE:
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(institutions.router, prefix="/api/institutions", tags=["Institutions"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(staff.router, prefix="/api/staff", tags=["Staff"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["Certificates"])


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Education Management API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "local" if settings.USE_LOCAL_DB else "supabase",
        "storage": "local" if settings.USE_LOCAL_STORAGE else "cloudinary"
    }

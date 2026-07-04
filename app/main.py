from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from pathlib import Path

# Import routes
from app.routes import auth, institutions, students, courses, staff, attendance, payroll, certificates, dashboard, payments, course_modules
from app.routes import exams, student_exams, exam_verification, chatbot, batches

# NOTE (F-09): no Base.metadata.create_all here. The schema is created by
# Alembic only: `alembic upgrade head` against a fresh database.

# Initialize FastAPI app
app = FastAPI(
    title="Education Management API",
    description="Multi-tenant education management platform API",
    version="1.0.0"
)

# Configure CORS - MUST be before route includes.
# FRONTEND_URL covers the split deployment (frontend and backend on different
# origins). In the RECOMMENDED prod setup the Next.js app proxies /api/*
# to this backend via a rewrite (see docs/07-DEPLOYMENT.md), so every request
# is same-origin and CORS never comes into play — this list is then inert.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",  # Add port 3002
        "http://localhost:3003",
        settings.FRONTEND_URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files directory for LOCAL file storage only (dev).
# In prod (USE_LOCAL_STORAGE=false on Vercel) there is no writable disk and
# uploads live in Supabase Storage, served directly from its CDN — this mount
# must not exist there (docs/01 §2).
if settings.USE_LOCAL_STORAGE:
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(institutions.router, prefix="/api/institutions", tags=["Institutions"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(batches.router, prefix="/api/batches", tags=["Batches"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(staff.router, prefix="/api/staff", tags=["Staff"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["Certificates"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(course_modules.router, prefix="/api", tags=["Course Modules"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])
app.include_router(student_exams.router, prefix="/api/student/exams", tags=["Student Exams"])
app.include_router(exam_verification.router, prefix="/api/exams/attempts", tags=["Exam Verification"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Education Management API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe. Also the target of the weekly Vercel cron
    (vercel.json) that keeps the Supabase free project from pausing after
    ~7 days of inactivity (docs/01 §2)."""
    return {
        "status": "healthy",
        "database": "supabase" if settings.DATABASE_URL else "local",
        "storage": "local" if settings.USE_LOCAL_STORAGE else "supabase"
    }

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

_IS_PROD = settings.ENVIRONMENT == "production"

# Initialize FastAPI app. The interactive docs expose the full API surface,
# so they are dev-only.
app = FastAPI(
    title="Education Management API",
    description="Multi-tenant education management platform API",
    version="1.0.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if _IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Configure CORS - MUST be before route includes.
# FRONTEND_URL covers the split deployment (frontend and backend on different
# origins). In the RECOMMENDED prod setup the Next.js app proxies /api/*
# to this backend via a rewrite (see docs/07-DEPLOYMENT.md), so every request
# is same-origin and CORS never comes into play — this list is then inert.
# Dev origins are only allowed outside production.
_cors_origins = [settings.FRONTEND_URL] if _IS_PROD else [
    "http://localhost:3000",
    "http://localhost:3100",  # run-dev.sh default
    settings.FRONTEND_URL,
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in _cors_origins if o],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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

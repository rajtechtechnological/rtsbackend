"""
Dashboard stats. super_admin gets cross-franchise analytics; everyone else
gets their own institution only (scoped via TenantContext).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from decimal import Decimal

from app.dependencies import require_roles, ALL_STAFF_ROLES
from app.models.course import Course
from app.models.fee_payment import FeePayment
from app.models.institution import Institution
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.models.user import User
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


@router.get(
    "/stats",
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_dashboard_stats(ctx: TenantContext = Depends(get_tenant)):
    """
    Dashboard statistics based on role:
    - super_admin: stats across all franchises
    - institution roles: stats for their own institution
    """
    db = ctx.db

    if ctx.institution_id is None:
        # super_admin: cross-franchise analytics
        total_franchises = db.query(func.count(Institution.id)).scalar() or 0

        prev_month_franchises = db.query(func.count(Institution.id)).filter(
            Institution.created_at < datetime.now() - timedelta(days=30)
        ).scalar() or 0
        franchise_trend = round(((total_franchises - prev_month_franchises) / max(prev_month_franchises, 1)) * 100, 1) if prev_month_franchises > 0 else 0

        current_month = datetime.now().month
        current_year = datetime.now().year
        total_revenue = db.query(func.sum(FeePayment.amount)).filter(
            extract('month', FeePayment.paid_at) == current_month,
            extract('year', FeePayment.paid_at) == current_year,
        ).scalar() or Decimal(0)

        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_revenue = db.query(func.sum(FeePayment.amount)).filter(
            extract('month', FeePayment.paid_at) == prev_month,
            extract('year', FeePayment.paid_at) == prev_year,
        ).scalar() or Decimal(1)
        revenue_trend = round(((float(total_revenue) - float(prev_revenue)) / float(prev_revenue)) * 100, 1) if float(prev_revenue) > 0 else 0

        active_courses = db.query(func.count(Course.id)).scalar() or 0
        prev_month_courses = db.query(func.count(Course.id)).filter(
            Course.created_at < datetime.now() - timedelta(days=30)
        ).scalar() or 0
        courses_trend = round(((active_courses - prev_month_courses) / max(prev_month_courses, 1)) * 100, 1) if prev_month_courses > 0 else 0

        total_enrollments = db.query(func.count(StudentCourse.id)).scalar() or 0
        prev_month_enrollments = db.query(func.count(StudentCourse.id)).filter(
            StudentCourse.enrollment_date < datetime.now() - timedelta(days=30)
        ).scalar() or 0
        enrollments_trend = round(((total_enrollments - prev_month_enrollments) / max(prev_month_enrollments, 1)) * 100, 1) if prev_month_enrollments > 0 else 0

        popular_courses = db.query(
            Course.name,
            Institution.name.label('franchise_name'),
            func.count(StudentCourse.id).label('enrollment_count'),
        ).join(
            StudentCourse, Course.id == StudentCourse.course_id
        ).join(
            Institution, Course.institution_id == Institution.id
        ).group_by(
            Course.id, Course.name, Institution.name
        ).order_by(
            func.count(StudentCourse.id).desc()
        ).limit(3).all()

        popular_courses_data = [
            {
                "course": course.name,
                "franchise": course.franchise_name,
                "enrollments": course.enrollment_count,
                "trend": round((course.enrollment_count / max(total_enrollments, 1)) * 100, 1),
            }
            for course in popular_courses
        ]

        # fee_payments now carries institution_id directly (docs/02)
        revenue_by_franchise = db.query(
            Institution.name,
            func.sum(FeePayment.amount).label('revenue'),
        ).join(
            FeePayment, Institution.id == FeePayment.institution_id
        ).filter(
            extract('month', FeePayment.paid_at) == current_month,
            extract('year', FeePayment.paid_at) == current_year,
        ).group_by(
            Institution.id, Institution.name
        ).order_by(
            func.sum(FeePayment.amount).desc()
        ).limit(4).all()

        total_franchise_revenue = sum(float(f.revenue) for f in revenue_by_franchise)
        revenue_by_franchise_data = [
            {
                "name": franchise.name,
                "revenue": float(franchise.revenue),
                "percentage": round((float(franchise.revenue) / max(total_franchise_revenue, 1)) * 100, 1),
            }
            for franchise in revenue_by_franchise
        ]

        return {
            "stats": [
                {
                    "title": "Total Franchises",
                    "value": str(total_franchises),
                    "description": "Active locations",
                    "trend": {"value": franchise_trend, "isPositive": franchise_trend >= 0},
                },
                {
                    "title": "Total Revenue",
                    "value": f"₹{float(total_revenue) / 100000:.1f}L",
                    "description": "This month",
                    "trend": {"value": revenue_trend, "isPositive": revenue_trend >= 0},
                },
                {
                    "title": "Active Courses",
                    "value": str(active_courses),
                    "description": "Across all franchises",
                    "trend": {"value": courses_trend, "isPositive": courses_trend >= 0},
                },
                {
                    "title": "Total Enrollments",
                    "value": str(total_enrollments),
                    "description": "Students enrolled",
                    "trend": {"value": enrollments_trend, "isPositive": enrollments_trend >= 0},
                },
            ],
            "popularCourses": popular_courses_data,
            "revenueByFranchise": revenue_by_franchise_data,
        }

    # Institution roles: own institution only
    institution_id = ctx.institution_id

    total_students = ctx.q(Student).count()

    prev_month_students = ctx.q(Student).filter(
        Student.enrollment_date < datetime.now() - timedelta(days=30)
    ).count()
    students_trend = round(((total_students - prev_month_students) / max(prev_month_students, 1)) * 100, 1) if prev_month_students > 0 else 0

    total_staff = db.query(func.count(User.id)).filter(
        User.institution_id == institution_id,
        User.role == 'staff',
    ).scalar() or 0

    active_courses = db.query(func.count(Course.id)).filter(
        Course.institution_id == institution_id
    ).scalar() or 0

    current_month = datetime.now().month
    current_year = datetime.now().year
    revenue = ctx.q(FeePayment).with_entities(func.sum(FeePayment.amount)).filter(
        extract('month', FeePayment.paid_at) == current_month,
        extract('year', FeePayment.paid_at) == current_year,
    ).scalar() or Decimal(0)

    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    prev_revenue = ctx.q(FeePayment).with_entities(func.sum(FeePayment.amount)).filter(
        extract('month', FeePayment.paid_at) == prev_month,
        extract('year', FeePayment.paid_at) == prev_year,
    ).scalar() or Decimal(1)
    revenue_trend = round(((float(revenue) - float(prev_revenue)) / float(prev_revenue)) * 100, 1) if float(prev_revenue) > 0 else 0

    recent_enrollments = db.query(
        User.full_name,
        Course.name.label('course_name'),
        StudentCourse.enrollment_date,
    ).join(
        Student, User.id == Student.user_id
    ).join(
        StudentCourse, Student.id == StudentCourse.student_id
    ).join(
        Course, StudentCourse.course_id == Course.id
    ).filter(
        Student.institution_id == institution_id
    ).order_by(
        StudentCourse.enrollment_date.desc()
    ).limit(3).all()

    recent_enrollments_data = [
        {
            "student_name": enrollment.full_name,
            "course": enrollment.course_name,
            "time_ago": _get_time_ago(enrollment.enrollment_date),
        }
        for enrollment in recent_enrollments
    ]

    return {
        "stats": [
            {
                "title": "Total Students",
                "value": str(total_students),
                "description": "Active enrollments",
                "trend": {"value": students_trend, "isPositive": students_trend >= 0},
            },
            {
                "title": "Total Staff",
                "value": str(total_staff),
                "description": "Active members",
                "trend": None,
            },
            {
                "title": "Active Courses",
                "value": str(active_courses),
                "description": "Available courses",
                "trend": None,
            },
            {
                "title": "Revenue",
                "value": f"₹{float(revenue) / 100000:.1f}L",
                "description": "This month",
                "trend": {"value": revenue_trend, "isPositive": revenue_trend >= 0},
            },
        ],
        "recentEnrollments": recent_enrollments_data,
    }


def _get_time_ago(date):
    """Human-readable time ago"""
    if not date:
        return "Unknown"

    now = datetime.now().date()
    delta = now - date

    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"

"""
Exam verification (staff_manager+ only, router-level gate). Attempts carry no
institution_id — they are scoped through their parent exam (docs/01 §4).
The attempt state machine is driven by `status`: verification moves
submitted/timed_out -> verified (is_verified/verified_* kept for audit).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.dependencies import require_roles, MANAGER_ROLES
from app.models.exam import Exam, ExamAttempt, StudentAnswer
from app.models.student import Student
from app.schemas.exam import (
    ExamAttemptResponse, ExamAttemptDetailResponse,
    ExamVerifyRequest, RetakeAllowRequest, StudentAnswerResponse,
)
from app.tenancy import TenantContext, get_tenant

router = APIRouter(dependencies=[Depends(require_roles(MANAGER_ROLES))])

# Attempt statuses that are finished but not yet verified
COMPLETED_STATUSES = ["submitted", "timed_out"]


def _attempt_query(ctx: TenantContext):
    """ExamAttempt scoped through its parent exam's institution."""
    query = ctx.db.query(ExamAttempt).join(Exam, ExamAttempt.exam_id == Exam.id)
    if ctx.institution_id is not None:
        query = query.filter(Exam.institution_id == ctx.institution_id)
    return query


def _get_attempt_or_404(ctx: TenantContext, attempt_id: UUID, options=()) -> ExamAttempt:
    query = _attempt_query(ctx)
    for opt in options:
        query = query.options(opt)
    attempt = query.filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


def _mark_verified(attempt: ExamAttempt, ctx: TenantContext, notes: Optional[str] = None) -> None:
    attempt.status = "verified"
    attempt.is_verified = True
    attempt.verified_by = ctx.user.id
    attempt.verified_at = datetime.now(timezone.utc)
    if notes is not None:
        attempt.verification_notes = notes


# ============ Pending Verifications ============

@router.get("/pending", response_model=List[ExamAttemptDetailResponse])
def get_pending_verifications(
    exam_id: Optional[UUID] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """All finished-but-unverified attempts in the caller's institution."""
    query = _attempt_query(ctx).options(
        joinedload(ExamAttempt.exam),
        joinedload(ExamAttempt.student).joinedload(Student.user),
        joinedload(ExamAttempt.answers),
    ).filter(ExamAttempt.status.in_(COMPLETED_STATUSES))

    if exam_id:
        query = query.filter(ExamAttempt.exam_id == exam_id)

    attempts = query.order_by(ExamAttempt.end_time.desc()).all()

    return [
        ExamAttemptDetailResponse(
            id=attempt.id,
            exam_id=attempt.exam_id,
            student_id=attempt.student_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            start_time=attempt.start_time,
            deadline_at=attempt.deadline_at,
            end_time=attempt.end_time,
            total_marks=attempt.total_marks,
            obtained_marks=attempt.obtained_marks,
            percentage=attempt.percentage,
            passed=attempt.passed,
            total_answered=attempt.total_answered or 0,
            correct_answers=attempt.correct_answers,
            is_verified=attempt.is_verified,
            verified_at=attempt.verified_at,
            created_at=attempt.created_at,
            exam_title=attempt.exam.title if attempt.exam else None,
            student_name=attempt.student.user.full_name if attempt.student and attempt.student.user else None,
            student_email=attempt.student.user.email if attempt.student and attempt.student.user else None,
            answers=[StudentAnswerResponse.model_validate(a) for a in attempt.answers],
        )
        for attempt in attempts
    ]


# ============ Statistics ============

@router.get("/statistics")
def get_verification_statistics(ctx: TenantContext = Depends(get_tenant)):
    """Exam verification statistics for the caller's institution."""
    pending = _attempt_query(ctx).filter(
        ExamAttempt.status.in_(COMPLETED_STATUSES)
    ).count()

    today = datetime.now(timezone.utc).date()
    verified_today = _attempt_query(ctx).filter(
        ExamAttempt.status == "verified",
        func.date(ExamAttempt.verified_at) == today,
    ).count()

    verified_attempts = _attempt_query(ctx).filter(
        ExamAttempt.status == "verified"
    ).all()
    total_verified = len(verified_attempts)
    passed_count = sum(1 for a in verified_attempts if a.passed)
    pass_rate = (passed_count / total_verified * 100) if total_verified else 0
    avg_score = (
        sum(a.percentage or 0 for a in verified_attempts) / total_verified
        if total_verified else 0
    )

    return {
        "pending_verification": pending,
        "verified_today": verified_today,
        "total_verified": total_verified,
        "pass_rate": round(pass_rate, 1),
        "average_score": round(avg_score, 1),
    }


# ============ Review Attempt ============

@router.get("/{attempt_id}/review")
def review_attempt(
    attempt_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Detailed review of an attempt with all questions and answers
    (manager-only — this is the one place correct answers are shown)."""
    attempt = _get_attempt_or_404(
        ctx, attempt_id,
        options=(
            joinedload(ExamAttempt.exam).joinedload(Exam.course),
            joinedload(ExamAttempt.exam).joinedload(Exam.module),
            joinedload(ExamAttempt.student).joinedload(Student.user),
            joinedload(ExamAttempt.answers).joinedload(StudentAnswer.question),
        ),
    )

    questions_review = []
    for ans in sorted(attempt.answers, key=lambda a: a.question.order_index if a.question else 0):
        if not ans.question:
            continue
        q = ans.question
        questions_review.append({
            "question_id": str(q.id),
            "order_index": q.order_index,
            "question_text": q.question_text,
            "image_url": q.image_url,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_option": q.correct_option,
            "marks": q.marks,
            "explanation": q.explanation,
            "selected_option": ans.selected_option,
            "is_correct": ans.is_correct,
            "marks_obtained": ans.marks_obtained,
            "marked_for_review": ans.marked_for_review,
            "answered_at": ans.answered_at.isoformat() if ans.answered_at else None,
        })

    time_taken_minutes = None
    if attempt.end_time and attempt.start_time:
        time_taken_minutes = int((attempt.end_time - attempt.start_time).total_seconds() / 60)

    return {
        "attempt": {
            "id": str(attempt.id),
            "exam_id": str(attempt.exam_id),
            "exam_title": attempt.exam.title,
            "course_name": attempt.exam.course.name if attempt.exam.course else None,
            "module_name": attempt.exam.module.module_name if attempt.exam.module else None,
            "student_id": str(attempt.student_id),
            "student_name": attempt.student.user.full_name if attempt.student and attempt.student.user else None,
            "student_email": attempt.student.user.email if attempt.student and attempt.student.user else None,
            "attempt_number": attempt.attempt_number,
            "status": attempt.status,
            "start_time": attempt.start_time.isoformat(),
            "deadline_at": attempt.deadline_at.isoformat() if attempt.deadline_at else None,
            "end_time": attempt.end_time.isoformat() if attempt.end_time else None,
            "time_taken_minutes": time_taken_minutes,
            "total_questions": len(attempt.question_order or []),
            "total_answered": attempt.total_answered,
            "correct_answers": attempt.correct_answers,
            "total_marks": attempt.total_marks,
            "obtained_marks": attempt.obtained_marks,
            "percentage": attempt.percentage,
            "passed": attempt.passed,
            "passing_marks": attempt.exam.passing_marks,
            "is_verified": attempt.is_verified,
            "verified_at": attempt.verified_at.isoformat() if attempt.verified_at else None,
            "verification_notes": attempt.verification_notes,
        },
        "questions": questions_review,
    }


# ============ Verify Attempt ============

@router.post("/{attempt_id}/verify", response_model=ExamAttemptResponse)
def verify_attempt(
    attempt_id: UUID,
    request: ExamVerifyRequest,
    ctx: TenantContext = Depends(get_tenant),
):
    """Verify an attempt and release results to the student."""
    attempt = _get_attempt_or_404(ctx, attempt_id)

    if attempt.status == "in_progress":
        raise HTTPException(status_code=400, detail="Cannot verify an in-progress exam")
    if attempt.status == "verified":
        raise HTTPException(status_code=400, detail="Attempt already verified")

    _mark_verified(attempt, ctx, request.notes)

    ctx.db.commit()
    ctx.db.refresh(attempt)
    return attempt


# ============ Allow Retake ============

@router.post("/{attempt_id}/allow-retake", response_model=ExamAttemptResponse)
def allow_retake(
    attempt_id: UUID,
    request: RetakeAllowRequest,
    ctx: TenantContext = Depends(get_tenant),
):
    """Allow a student to retake an exam (verifies the attempt if needed)."""
    attempt = _get_attempt_or_404(ctx, attempt_id)

    if attempt.status == "in_progress":
        raise HTTPException(status_code=400, detail="Cannot allow retake for an in-progress exam")

    attempt.retake_allowed = True
    attempt.retake_allowed_by = ctx.user.id
    attempt.retake_allowed_at = datetime.now(timezone.utc)

    if attempt.status != "verified":
        _mark_verified(attempt, ctx, request.notes)

    ctx.db.commit()
    ctx.db.refresh(attempt)
    return attempt


# ============ Bulk Verify ============

@router.post("/verify-bulk")
def verify_bulk(
    attempt_ids: List[UUID],
    ctx: TenantContext = Depends(get_tenant),
):
    """Verify multiple attempts at once (out-of-tenant IDs are skipped)."""
    verified_count = 0
    for attempt_id in attempt_ids:
        attempt = _attempt_query(ctx).filter(ExamAttempt.id == attempt_id).first()
        if not attempt or attempt.status not in COMPLETED_STATUSES:
            continue

        _mark_verified(attempt, ctx)
        verified_count += 1

    ctx.db.commit()
    return {"verified_count": verified_count, "total_requested": len(attempt_ids)}

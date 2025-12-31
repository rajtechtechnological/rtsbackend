from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.exam import Exam, Question, ExamAttempt, StudentAnswer
from app.schemas.exam import (
    ExamAttemptResponse, ExamAttemptDetailResponse,
    ExamVerifyRequest, RetakeAllowRequest, StudentAnswerResponse
)
from app.dependencies import get_current_user, check_resource_access

router = APIRouter()

MANAGER_ROLES = ["super_admin", "institution_director", "staff_manager"]


def require_manager(user: User):
    """Ensure user has manager-level access"""
    if user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can access this resource"
        )


# ============ Pending Verifications ============

@router.get("/pending", response_model=List[ExamAttemptDetailResponse])
def get_pending_verifications(
    exam_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all exam attempts pending verification"""
    require_manager(current_user)

    query = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam),
        joinedload(ExamAttempt.student).joinedload(Student.user),
        joinedload(ExamAttempt.answers)
    ).filter(
        ExamAttempt.status.in_(['completed', 'submitted', 'timed_out']),
        ExamAttempt.is_verified == False
    )

    # Filter by institution
    if current_user.role != "super_admin":
        query = query.join(Exam).filter(Exam.institution_id == current_user.institution_id)

    if exam_id:
        query = query.filter(ExamAttempt.exam_id == exam_id)

    attempts = query.order_by(ExamAttempt.end_time.desc()).all()

    result = []
    for attempt in attempts:
        result.append(ExamAttemptDetailResponse(
            id=attempt.id,
            exam_id=attempt.exam_id,
            student_id=attempt.student_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            start_time=attempt.start_time,
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
            answers=[StudentAnswerResponse.model_validate(a) for a in attempt.answers]
        ))

    return result


# ============ Review Attempt ============

@router.get("/{attempt_id}/review")
def review_attempt(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed review of an exam attempt with all questions and answers"""
    require_manager(current_user)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam).joinedload(Exam.course),
        joinedload(ExamAttempt.exam).joinedload(Exam.module),
        joinedload(ExamAttempt.student).joinedload(Student.user),
        joinedload(ExamAttempt.answers).joinedload(StudentAnswer.question)
    ).filter(ExamAttempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, attempt.exam.institution_id)

    # Build detailed response with questions
    questions_review = []
    for ans in sorted(attempt.answers, key=lambda a: a.question.order_index if a.question else 0):
        if not ans.question:
            continue

        q = ans.question
        questions_review.append({
            "question_id": str(q.id),
            "order_index": q.order_index,
            "question_text": q.question_text,
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
            "answered_at": ans.answered_at.isoformat() if ans.answered_at else None
        })

    # Calculate time taken
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
            "verification_notes": attempt.verification_notes
        },
        "questions": questions_review
    }


# ============ Verify Attempt ============

@router.post("/{attempt_id}/verify", response_model=ExamAttemptResponse)
def verify_attempt(
    attempt_id: UUID,
    request: ExamVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify an exam attempt and release results to student"""
    require_manager(current_user)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam)
    ).filter(ExamAttempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, attempt.exam.institution_id)

    if attempt.status not in ['completed', 'submitted', 'timed_out']:
        raise HTTPException(status_code=400, detail="Cannot verify an in-progress exam")

    if attempt.is_verified:
        raise HTTPException(status_code=400, detail="Attempt already verified")

    attempt.is_verified = True
    attempt.verified_by = current_user.id
    attempt.verified_at = datetime.now()
    attempt.verification_notes = request.notes

    db.commit()
    db.refresh(attempt)

    return attempt


# ============ Allow Retake ============

@router.post("/{attempt_id}/allow-retake", response_model=ExamAttemptResponse)
def allow_retake(
    attempt_id: UUID,
    request: RetakeAllowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow a student to retake an exam"""
    require_manager(current_user)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam)
    ).filter(ExamAttempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, attempt.exam.institution_id)

    if attempt.status not in ['completed', 'submitted', 'timed_out']:
        raise HTTPException(status_code=400, detail="Cannot allow retake for an in-progress exam")

    attempt.retake_allowed = True
    attempt.retake_allowed_by = current_user.id
    attempt.retake_allowed_at = datetime.now()

    # Also verify if not already verified
    if not attempt.is_verified:
        attempt.is_verified = True
        attempt.verified_by = current_user.id
        attempt.verified_at = datetime.now()
        attempt.verification_notes = request.notes

    db.commit()
    db.refresh(attempt)

    return attempt


# ============ Bulk Verify ============

@router.post("/verify-bulk")
def verify_bulk(
    attempt_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify multiple exam attempts at once"""
    require_manager(current_user)

    verified_count = 0
    for attempt_id in attempt_ids:
        attempt = db.query(ExamAttempt).options(
            joinedload(ExamAttempt.exam)
        ).filter(ExamAttempt.id == attempt_id).first()

        if not attempt:
            continue

        if current_user.role != "super_admin":
            if attempt.exam.institution_id != current_user.institution_id:
                continue

        if attempt.status not in ['completed', 'submitted', 'timed_out']:
            continue

        if attempt.is_verified:
            continue

        attempt.is_verified = True
        attempt.verified_by = current_user.id
        attempt.verified_at = datetime.now()
        verified_count += 1

    db.commit()

    return {"verified_count": verified_count, "total_requested": len(attempt_ids)}


# ============ Statistics ============

@router.get("/statistics")
def get_verification_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get exam verification statistics"""
    require_manager(current_user)

    base_query = db.query(ExamAttempt).join(Exam)

    if current_user.role != "super_admin":
        base_query = base_query.filter(Exam.institution_id == current_user.institution_id)

    # Pending verification count
    pending = base_query.filter(
        ExamAttempt.status.in_(['completed', 'submitted', 'timed_out']),
        ExamAttempt.is_verified == False
    ).count()

    # Verified today
    today = datetime.now().date()
    verified_today = base_query.filter(
        ExamAttempt.is_verified == True,
        func.date(ExamAttempt.verified_at) == today
    ).count()

    # Total verified
    total_verified = base_query.filter(ExamAttempt.is_verified == True).count()

    # Pass rate (verified only)
    verified_attempts = base_query.filter(ExamAttempt.is_verified == True).all()
    passed_count = sum(1 for a in verified_attempts if a.passed)
    pass_rate = (passed_count / len(verified_attempts) * 100) if verified_attempts else 0

    # Average score (verified only)
    avg_score = sum(a.percentage or 0 for a in verified_attempts) / len(verified_attempts) if verified_attempts else 0

    return {
        "pending_verification": pending,
        "verified_today": verified_today,
        "total_verified": total_verified,
        "pass_rate": round(pass_rate, 1),
        "average_score": round(avg_score, 1)
    }

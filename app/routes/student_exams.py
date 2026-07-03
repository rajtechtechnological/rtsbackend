"""
Student-facing exam endpoints.

Security invariants kept from the hotfix commit and hardened here:
- F-02: every exam/attempt query is filtered by the student's institution
  (global courses share course_ids across institutions).
- F-13: exam timing is server-authoritative. The deadline is persisted on
  the attempt as `deadline_at` (= DB now() + duration, computed at start);
  every answer save and the final submit are rejected past
  deadline_at + 30s grace, and the attempt is marked timed_out.
  `time_remaining_seconds` is a display hint only.
- F-14: questions are serialized ONLY through QuestionPublic — never
  correct_option/explanation.
- Batch targeting (F-08): a schedule matches iff schedule.batch_id equals
  the student's batch_id.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta, timezone
import random

from app.dependencies import require_roles
from app.models.exam import Exam, Question, ExamSchedule, ExamAttempt, StudentAnswer
from app.models.fee_payment import FeePayment
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.schemas.exam import (
    AvailableExamResponse, ExamAttemptStart, ExamAttemptState,
    ExamAttemptResponse, ExamResultResponse, AnswerSubmit, QuestionPublic,
)
from app.tenancy import TenantContext, get_tenant

router = APIRouter(dependencies=[Depends(require_roles(["student"]))])

# Grace period after the server-computed deadline (F-13). Never derived from
# any client-provided time.
EXAM_DEADLINE_GRACE_SECONDS = 30

COMPLETED_STATUSES = ["submitted", "timed_out", "verified"]


def _db_now(db: Session) -> datetime:
    """Database timestamps are the only clock (docs/01 §2)."""
    now = db.execute(select(func.now())).scalar()
    if isinstance(now, datetime):
        return now
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime, reference: datetime) -> datetime:
    """Align tz-awareness so DB-loaded and computed datetimes compare safely."""
    if reference.tzinfo is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    if reference.tzinfo is None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _expire_attempt(attempt: ExamAttempt, db: Session) -> None:
    """Grade whatever answers exist and mark the attempt timed out (F-13)."""
    attempt.status = "timed_out"
    attempt.end_time = _db_now(db)
    _calculate_results(attempt, db)
    db.commit()


def get_own_student(ctx: TenantContext) -> Student:
    """The caller's own Student row — never resolved from request input."""
    student = ctx.q(Student).filter(Student.user_id == ctx.user.id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource",
        )
    return student


def check_payment_status(student_id: UUID, course_id: UUID, db: Session) -> bool:
    """Has the student made any payment for the course?"""
    payment = db.query(FeePayment).filter(
        FeePayment.student_id == student_id,
        FeePayment.course_id == course_id,
    ).first()
    return payment is not None


def check_exam_schedule(
    exam: Exam, student: Student, db: Session
) -> Tuple[bool, Optional[ExamSchedule], str]:
    """Is the exam scheduled for the student's batch right now?"""
    now = _db_now(db)
    today = now.date()
    current_time = now.time()

    # Tenant isolation (F-02) + batch targeting (F-08): the schedule must
    # belong to the student's institution AND target the student's batch.
    schedule = db.query(ExamSchedule).filter(
        ExamSchedule.exam_id == exam.id,
        ExamSchedule.institution_id == student.institution_id,
        ExamSchedule.batch_id == student.batch_id,
        ExamSchedule.is_active == True,  # noqa: E712
        ExamSchedule.scheduled_date == today,
    ).first()

    if not schedule:
        future_schedule = db.query(ExamSchedule).filter(
            ExamSchedule.exam_id == exam.id,
            ExamSchedule.institution_id == student.institution_id,
            ExamSchedule.batch_id == student.batch_id,
            ExamSchedule.is_active == True,  # noqa: E712
            ExamSchedule.scheduled_date > today,
        ).order_by(ExamSchedule.scheduled_date).first()

        if future_schedule:
            return False, None, f"Exam scheduled for {future_schedule.scheduled_date}"
        return False, None, "Exam not scheduled for your batch"

    if current_time < schedule.start_time:
        return False, schedule, f"Exam starts at {schedule.start_time.strftime('%I:%M %p')}"
    if current_time > schedule.end_time:
        return False, schedule, "Exam time has ended"

    return True, schedule, ""


def shuffle_options(question: Question) -> Dict[str, Any]:
    """Shuffle options and return mapping"""
    options = [
        ("A", question.option_a),
        ("B", question.option_b),
        ("C", question.option_c),
        ("D", question.option_d),
    ]
    random.shuffle(options)

    option_map = {}
    shuffled = {}
    for i, (orig_key, value) in enumerate(options):
        new_key = chr(65 + i)  # A, B, C, D
        option_map[new_key] = orig_key
        shuffled[f"option_{new_key.lower()}"] = value

    return {"options": shuffled, "map": option_map}


def _student_attempts_query(db: Session, student: Student):
    """Attempts scoped via the institution's exams (F-02)."""
    return (
        db.query(ExamAttempt)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            ExamAttempt.student_id == student.id,
            Exam.institution_id == student.institution_id,
        )
    )


# ============ Available Exams ============

@router.get("/available", response_model=List[AvailableExamResponse])
def get_available_exams(ctx: TenantContext = Depends(get_tenant)):
    """All available exams for the student."""
    db = ctx.db
    student = get_own_student(ctx)

    enrollments = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.status == "active",
    ).all()
    course_ids = [e.course_id for e in enrollments]
    if not course_ids:
        return []

    # Tenant isolation (F-02): global courses share course_ids across
    # institutions, so exams MUST also be filtered by institution.
    exams = db.query(Exam).options(
        joinedload(Exam.course),
        joinedload(Exam.module),
    ).filter(
        Exam.course_id.in_(course_ids),
        Exam.institution_id == student.institution_id,
        Exam.is_active == True,  # noqa: E712
    ).all()

    result = []
    for exam in exams:
        has_payment = check_payment_status(student.id, exam.course_id, db)
        is_scheduled, schedule, schedule_message = check_exam_schedule(exam, student, db)

        attempts = _student_attempts_query(db, student).filter(
            ExamAttempt.exam_id == exam.id
        ).all()

        previous_attempts = len(attempts)
        completed_attempts = [a for a in attempts if a.status in COMPLETED_STATUSES]

        is_locked = True
        lock_reason = None
        can_retake = False

        if not has_payment:
            lock_reason = "Payment pending"
        elif not is_scheduled:
            lock_reason = schedule_message
        elif completed_attempts:
            if exam.allow_retakes:
                if exam.max_retakes == 0 or previous_attempts < exam.max_retakes:
                    last_attempt = max(completed_attempts, key=lambda a: a.created_at)
                    if last_attempt.retake_allowed:
                        is_locked = False
                        can_retake = True
                    else:
                        lock_reason = "Awaiting retake permission"
                else:
                    lock_reason = "Maximum retakes reached"
            else:
                lock_reason = "Exam already completed"
        else:
            is_locked = False  # new attempt or resume

        best_score = None
        if completed_attempts:
            best = max(completed_attempts, key=lambda a: a.percentage or 0)
            if best.status == "verified":
                best_score = best.percentage

        result.append(AvailableExamResponse(
            exam_id=exam.id,
            exam_title=exam.title,
            course_id=exam.course_id,
            course_name=exam.course.name if exam.course else "",
            module_id=exam.module_id,
            module_name=exam.module.module_name if exam.module else "",
            total_questions=exam.total_questions,
            duration_minutes=exam.duration_minutes,
            passing_marks=exam.passing_marks,
            is_locked=is_locked,
            lock_reason=lock_reason,
            schedule_id=schedule.id if schedule else None,
            scheduled_date=schedule.scheduled_date if schedule else None,
            start_time=schedule.start_time if schedule else None,
            end_time=schedule.end_time if schedule else None,
            previous_attempts=previous_attempts,
            can_retake=can_retake,
            best_score=best_score,
        ))

    return result


# ============ Start/Resume Exam ============

@router.post("/{exam_id}/start", response_model=ExamAttemptStart)
def start_exam(
    exam_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Start a new exam attempt or resume an existing one."""
    db = ctx.db
    student = get_own_student(ctx)

    # Tenant isolation (F-02): exam must belong to the student's institution
    exam = db.query(Exam).options(joinedload(Exam.questions)).filter(
        Exam.id == exam_id,
        Exam.institution_id == student.institution_id,
        Exam.is_active == True,  # noqa: E712
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    enrollment = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.course_id == exam.course_id,
        StudentCourse.status == "active",
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    if not check_payment_status(student.id, exam.course_id, db):
        raise HTTPException(status_code=403, detail="Payment required to take this exam")

    is_scheduled, schedule, message = check_exam_schedule(exam, student, db)
    if not is_scheduled:
        raise HTTPException(status_code=403, detail=message)

    existing_attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam.id,
        ExamAttempt.student_id == student.id,
        ExamAttempt.status == "in_progress",
    ).first()

    if existing_attempt:
        # Resume — deadline_at is authoritative (F-13), never client time
        attempt = existing_attempt
        now = _db_now(db)
        deadline = _as_aware(attempt.deadline_at, now)

        if now > deadline:
            _expire_attempt(attempt, db)
            raise HTTPException(status_code=400, detail="Exam time has expired")

        attempt.time_remaining_seconds = int((deadline - now).total_seconds())
        db.commit()
    else:
        completed_count = _student_attempts_query(db, student).filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.status.in_(COMPLETED_STATUSES),
        ).count()

        if completed_count > 0:
            if not exam.allow_retakes:
                raise HTTPException(status_code=403, detail="Exam already completed, retakes not allowed")
            if exam.max_retakes > 0 and completed_count >= exam.max_retakes:
                raise HTTPException(status_code=403, detail="Maximum retake attempts reached")

            last_attempt = _student_attempts_query(db, student).filter(
                ExamAttempt.exam_id == exam.id
            ).order_by(ExamAttempt.created_at.desc()).first()
            if last_attempt and not last_attempt.retake_allowed:
                raise HTTPException(status_code=403, detail="Awaiting retake permission from manager")

        active_questions = [q for q in exam.questions if q.is_active]
        if not active_questions:
            raise HTTPException(status_code=400, detail="No questions available in this exam")

        question_ids = [str(q.id) for q in active_questions]
        if exam.shuffle_questions:
            random.shuffle(question_ids)

        answer_order = {}
        if exam.shuffle_options:
            for q in active_questions:
                answer_order[str(q.id)] = shuffle_options(q)["map"]

        # F-13: deadline computed from the DB clock and PERSISTED at creation
        now = _db_now(db)
        attempt = ExamAttempt(
            exam_id=exam.id,
            student_id=student.id,
            schedule_id=schedule.id if schedule else None,
            attempt_number=completed_count + 1,
            start_time=now,
            deadline_at=now + timedelta(minutes=exam.duration_minutes),
            question_order=question_ids,
            answer_order=answer_order,
            time_remaining_seconds=exam.duration_minutes * 60,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        for q_id in question_ids:
            db.add(StudentAnswer(attempt_id=attempt.id, question_id=UUID(q_id)))
        db.commit()

    # Build question list using QuestionPublic (F-14): correct_option and
    # explanation must never reach the student here.
    questions_data = []
    question_order = attempt.question_order or []
    answer_order = attempt.answer_order or {}

    questions_by_id = {
        str(q.id): q for q in exam.questions if str(q.id) in set(question_order)
    }
    for i, q_id in enumerate(question_order):
        question = questions_by_id.get(q_id)
        if not question:
            continue

        q_data = {
            "id": str(question.id),
            "index": i,
            "question_text": question.question_text,
            "image_url": question.image_url,
            "marks": question.marks,
        }

        if q_id in answer_order:
            opt_map = answer_order[q_id]
            for new_key, orig_key in opt_map.items():
                q_data[f"option_{new_key.lower()}"] = getattr(question, f"option_{orig_key.lower()}")
        else:
            q_data["option_a"] = question.option_a
            q_data["option_b"] = question.option_b
            q_data["option_c"] = question.option_c
            q_data["option_d"] = question.option_d

        questions_data.append(QuestionPublic(**q_data))

    return ExamAttemptStart(
        attempt_id=attempt.id,
        exam_id=exam.id,
        exam_title=exam.title,
        duration_minutes=exam.duration_minutes,
        total_questions=len(questions_data),
        start_time=attempt.start_time,
        end_time=attempt.deadline_at,
        deadline=attempt.deadline_at,
        questions=questions_data,
    )


# ============ Get Attempt State ============

def _get_own_attempt(db: Session, student: Student, attempt_id: UUID, options=()) -> ExamAttempt:
    """Attempt owned by this student, scoped via the institution's exam
    (F-02). Anything else is a 404."""
    query = _student_attempts_query(db, student)
    for opt in options:
        query = query.options(opt)
    attempt = query.filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


@router.get("/attempts/{attempt_id}", response_model=ExamAttemptState)
def get_attempt_state(
    attempt_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Current state of an in-progress attempt."""
    db = ctx.db
    student = get_own_student(ctx)
    attempt = _get_own_attempt(
        db, student, attempt_id,
        options=(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.answers)),
    )

    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Exam is {attempt.status}")

    # Server-authoritative time remaining (F-13)
    now = _db_now(db)
    deadline = _as_aware(attempt.deadline_at, now)
    remaining = max(0, int((deadline - now).total_seconds()))

    answers = {}
    marked_for_review = []
    for ans in attempt.answers:
        answers[str(ans.question_id)] = ans.selected_option
        if ans.marked_for_review:
            marked_for_review.append(str(ans.question_id))

    return ExamAttemptState(
        attempt_id=attempt.id,
        exam_id=attempt.exam_id,
        exam_title=attempt.exam.title,
        status=attempt.status,
        current_question_index=0,
        total_questions=len(attempt.question_order or []),
        time_remaining_seconds=remaining,
        deadline=attempt.deadline_at,
        answers=answers,
        marked_for_review=marked_for_review,
    )


# ============ Submit Answer (Auto-save) ============

@router.post("/attempts/{attempt_id}/answer")
def submit_answer(
    attempt_id: UUID,
    answer_data: AnswerSubmit,
    ctx: TenantContext = Depends(get_tenant),
):
    """Save an answer (auto-save). Rejected past deadline_at + grace (F-13)."""
    db = ctx.db
    student = get_own_student(ctx)
    attempt = _get_own_attempt(db, student, attempt_id)

    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Cannot modify {attempt.status} exam")

    now = _db_now(db)
    deadline = _as_aware(attempt.deadline_at, now)
    if now > deadline + timedelta(seconds=EXAM_DEADLINE_GRACE_SECONDS):
        _expire_attempt(attempt, db)
        raise HTTPException(status_code=400, detail="Exam time has expired")

    answer = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt.id,
        StudentAnswer.question_id == answer_data.question_id,
    ).first()
    if not answer:
        # Only questions that belong to this attempt may be answered
        if str(answer_data.question_id) not in (attempt.question_order or []):
            raise HTTPException(status_code=404, detail="Question not part of this attempt")
        answer = StudentAnswer(attempt_id=attempt.id, question_id=answer_data.question_id)
        db.add(answer)

    # Map shuffled option back to the original
    selected = answer_data.selected_option
    if selected and attempt.answer_order:
        q_id = str(answer_data.question_id)
        if q_id in attempt.answer_order:
            selected = attempt.answer_order[q_id].get(selected, selected)

    answer.selected_option = selected
    answer.marked_for_review = answer_data.marked_for_review
    answer.answered_at = now

    remaining = max(0, int((deadline - now).total_seconds()))
    attempt.time_remaining_seconds = remaining  # display hint only

    db.commit()
    return {"status": "saved", "time_remaining": remaining}


# ============ Submit Exam ============

@router.post("/attempts/{attempt_id}/submit", response_model=ExamAttemptResponse)
def submit_exam(
    attempt_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Submit the exam for grading. Rejected past deadline_at + grace (F-13)."""
    db = ctx.db
    student = get_own_student(ctx)
    attempt = _get_own_attempt(
        db, student, attempt_id,
        options=(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.answers)),
    )

    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Exam is already {attempt.status}")

    now = _db_now(db)
    deadline = _as_aware(attempt.deadline_at, now)
    if now > deadline + timedelta(seconds=EXAM_DEADLINE_GRACE_SECONDS):
        _expire_attempt(attempt, db)
        raise HTTPException(status_code=400, detail="Exam time has expired")

    attempt.status = "submitted"
    attempt.end_time = now

    _calculate_results(attempt, db)

    db.commit()
    db.refresh(attempt)
    return attempt


def _calculate_results(attempt: ExamAttempt, db: Session):
    """Grade the attempt after submission/expiry."""
    exam = attempt.exam
    answers = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt.id
    ).all()

    question_ids = [a.question_id for a in answers]
    questions = {
        q.id: q
        for q in db.query(Question).filter(Question.id.in_(question_ids)).all()
    } if question_ids else {}

    total_marks = 0
    obtained_marks = 0
    correct_count = 0
    answered_count = 0

    for ans in answers:
        question = questions.get(ans.question_id)
        if not question:
            continue

        total_marks += question.marks

        if ans.selected_option:
            answered_count += 1
            if ans.selected_option == question.correct_option:
                ans.is_correct = True
                ans.marks_obtained = question.marks
                obtained_marks += question.marks
                correct_count += 1
            else:
                ans.is_correct = False
                ans.marks_obtained = 0

    attempt.total_marks = total_marks
    attempt.obtained_marks = obtained_marks
    attempt.correct_answers = correct_count
    attempt.total_answered = answered_count

    if total_marks > 0:
        attempt.percentage = (obtained_marks / total_marks) * 100
        attempt.passed = attempt.percentage >= exam.passing_marks
    else:
        attempt.percentage = 0
        attempt.passed = False

    # show_result_immediately => auto-verified (state machine: -> verified)
    if exam.show_result_immediately:
        attempt.status = "verified"
        attempt.is_verified = True
        attempt.verified_at = _db_now(db)


# ============ Get Results ============

@router.get("/results", response_model=List[ExamResultResponse])
def get_my_results(ctx: TenantContext = Depends(get_tenant)):
    """All VERIFIED exam results for the student (F-02 scoped)."""
    db = ctx.db
    student = get_own_student(ctx)

    attempts = (
        _student_attempts_query(db, student)
        .options(
            joinedload(ExamAttempt.exam).joinedload(Exam.course),
            joinedload(ExamAttempt.exam).joinedload(Exam.module),
        )
        .filter(ExamAttempt.status == "verified")
        .order_by(ExamAttempt.created_at.desc())
        .all()
    )

    results = []
    for attempt in attempts:
        duration_taken = None
        if attempt.end_time and attempt.start_time:
            duration_taken = int((attempt.end_time - attempt.start_time).total_seconds() / 60)

        results.append(ExamResultResponse(
            attempt_id=attempt.id,
            exam_id=attempt.exam_id,
            exam_title=attempt.exam.title,
            course_name=attempt.exam.course.name if attempt.exam.course else "",
            module_name=attempt.exam.module.module_name if attempt.exam.module else "",
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            start_time=attempt.start_time,
            end_time=attempt.end_time,
            duration_taken_minutes=duration_taken,
            total_questions=len(attempt.question_order or []),
            total_answered=attempt.total_answered or 0,
            correct_answers=attempt.correct_answers or 0,
            total_marks=attempt.total_marks or 0,
            obtained_marks=attempt.obtained_marks or 0,
            percentage=attempt.percentage or 0,
            passed=attempt.passed or False,
            is_verified=attempt.is_verified,
            verified_at=attempt.verified_at,
        ))

    return results

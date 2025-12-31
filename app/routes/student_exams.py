from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta, date, time
import random
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.exam import Exam, Question, ExamSchedule, ExamAttempt, StudentAnswer
from app.models.student_course import StudentCourse
from app.models.fee_payment import FeePayment
from app.schemas.exam import (
    AvailableExamResponse, ExamAttemptStart, ExamAttemptState,
    ExamAttemptResponse, ExamResultResponse, AnswerSubmit
)
from app.dependencies import get_current_user

router = APIRouter()


def get_student_from_user(user: User, db: Session) -> Student:
    """Get student record from user"""
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource"
        )
    return student


def check_payment_status(student_id: UUID, course_id: UUID, db: Session) -> bool:
    """Check if student has made any payment for the course"""
    payment = db.query(FeePayment).filter(
        FeePayment.student_id == student_id,
        FeePayment.course_id == course_id
    ).first()
    return payment is not None


def check_exam_schedule(exam: Exam, student: Student, db: Session) -> tuple[bool, Optional[ExamSchedule], str]:
    """Check if exam is scheduled for student's batch and current time"""
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    # Find matching schedule for student's batch
    schedule_query = db.query(ExamSchedule).filter(
        ExamSchedule.exam_id == exam.id,
        ExamSchedule.is_active == True,
        ExamSchedule.batch_time == student.batch_time,
        ExamSchedule.scheduled_date == today
    )

    # Optionally filter by batch identifier if student has one
    if student.batch_identifier:
        schedule_query = schedule_query.filter(
            (ExamSchedule.batch_identifier == student.batch_identifier) |
            (ExamSchedule.batch_identifier.is_(None))
        )

    schedule = schedule_query.first()

    if not schedule:
        # Check if there's a future schedule
        future_schedule = db.query(ExamSchedule).filter(
            ExamSchedule.exam_id == exam.id,
            ExamSchedule.is_active == True,
            ExamSchedule.batch_time == student.batch_time,
            ExamSchedule.scheduled_date > today
        ).order_by(ExamSchedule.scheduled_date).first()

        if future_schedule:
            return False, None, f"Exam scheduled for {future_schedule.scheduled_date}"
        return False, None, "Exam not scheduled for your batch"

    # Check if within time window
    if current_time < schedule.start_time:
        return False, schedule, f"Exam starts at {schedule.start_time.strftime('%I:%M %p')}"
    if current_time > schedule.end_time:
        return False, schedule, "Exam time has ended"

    return True, schedule, ""


def shuffle_options(question: Question) -> Dict[str, Any]:
    """Shuffle options and return mapping"""
    options = [
        ('A', question.option_a),
        ('B', question.option_b),
        ('C', question.option_c),
        ('D', question.option_d)
    ]
    random.shuffle(options)

    # Create mapping from new position to original
    option_map = {}
    shuffled_options = {}
    for i, (orig_key, value) in enumerate(options):
        new_key = chr(65 + i)  # A, B, C, D
        option_map[new_key] = orig_key
        shuffled_options[f'option_{new_key.lower()}'] = value

    return {
        'options': shuffled_options,
        'map': option_map
    }


# ============ Available Exams ============

@router.get("/available", response_model=List[AvailableExamResponse])
def get_available_exams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available exams for the student"""
    student = get_student_from_user(current_user, db)

    # Get student's enrolled courses
    enrollments = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.status == 'active'
    ).all()

    course_ids = [e.course_id for e in enrollments]

    if not course_ids:
        return []

    # Get all active exams for enrolled courses
    exams = db.query(Exam).options(
        joinedload(Exam.course),
        joinedload(Exam.module)
    ).filter(
        Exam.course_id.in_(course_ids),
        Exam.is_active == True
    ).all()

    result = []
    for exam in exams:
        # Check payment status
        has_payment = check_payment_status(student.id, exam.course_id, db)

        # Check schedule
        is_scheduled, schedule, schedule_message = check_exam_schedule(exam, student, db)

        # Check previous attempts
        attempts = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.student_id == student.id
        ).all()

        previous_attempts = len(attempts)
        completed_attempts = [a for a in attempts if a.status in ['completed', 'submitted', 'timed_out']]

        # Determine if can take exam
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
                    # Check if retake is allowed by manager
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
            # Check for in-progress attempt
            in_progress = [a for a in attempts if a.status == 'in_progress']
            if in_progress:
                is_locked = False  # Can resume
            else:
                is_locked = False

        # Get best score
        best_score = None
        if completed_attempts:
            best = max(completed_attempts, key=lambda a: a.percentage or 0)
            if best.is_verified:
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
            best_score=best_score
        ))

    return result


# ============ Start/Resume Exam ============

@router.post("/{exam_id}/start", response_model=ExamAttemptStart)
def start_exam(
    exam_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new exam attempt or resume an existing one"""
    student = get_student_from_user(current_user, db)

    exam = db.query(Exam).options(
        joinedload(Exam.questions)
    ).filter(Exam.id == exam_id, Exam.is_active == True).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Check enrollment
    enrollment = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.course_id == exam.course_id,
        StudentCourse.status == 'active'
    ).first()

    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # Check payment
    if not check_payment_status(student.id, exam.course_id, db):
        raise HTTPException(status_code=403, detail="Payment required to take this exam")

    # Check schedule
    is_scheduled, schedule, message = check_exam_schedule(exam, student, db)
    if not is_scheduled:
        raise HTTPException(status_code=403, detail=message)

    # Check for existing in-progress attempt
    existing_attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == student.id,
        ExamAttempt.status == 'in_progress'
    ).first()

    if existing_attempt:
        # Resume existing attempt
        attempt = existing_attempt

        # Calculate remaining time
        elapsed = (datetime.now() - attempt.start_time).total_seconds()
        time_limit = exam.duration_minutes * 60
        remaining = max(0, time_limit - elapsed)

        if remaining <= 0:
            # Time expired, auto-submit
            attempt.status = 'timed_out'
            attempt.end_time = datetime.now()
            _calculate_results(attempt, db)
            db.commit()
            raise HTTPException(status_code=400, detail="Exam time has expired")

        attempt.time_remaining_seconds = int(remaining)
        db.commit()
    else:
        # Check if can start new attempt
        completed_attempts = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == student.id,
            ExamAttempt.status.in_(['completed', 'submitted', 'timed_out'])
        ).count()

        if completed_attempts > 0:
            if not exam.allow_retakes:
                raise HTTPException(status_code=403, detail="Exam already completed, retakes not allowed")

            if exam.max_retakes > 0 and completed_attempts >= exam.max_retakes:
                raise HTTPException(status_code=403, detail="Maximum retake attempts reached")

            # Check if retake is allowed by manager
            last_attempt = db.query(ExamAttempt).filter(
                ExamAttempt.exam_id == exam_id,
                ExamAttempt.student_id == student.id
            ).order_by(ExamAttempt.created_at.desc()).first()

            if last_attempt and not last_attempt.retake_allowed:
                raise HTTPException(status_code=403, detail="Awaiting retake permission from manager")

        # Create new attempt
        active_questions = [q for q in exam.questions if q.is_active]
        if not active_questions:
            raise HTTPException(status_code=400, detail="No questions available in this exam")

        # Randomize questions if enabled
        question_ids = [str(q.id) for q in active_questions]
        if exam.shuffle_questions:
            random.shuffle(question_ids)

        # Randomize options if enabled
        answer_order = {}
        if exam.shuffle_options:
            for q in active_questions:
                shuffled = shuffle_options(q)
                answer_order[str(q.id)] = shuffled['map']

        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=student.id,
            schedule_id=schedule.id if schedule else None,
            attempt_number=completed_attempts + 1,
            question_order=question_ids,
            answer_order=answer_order,
            time_remaining_seconds=exam.duration_minutes * 60
        )

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Create empty answer records for all questions
        for q_id in question_ids:
            answer = StudentAnswer(
                attempt_id=attempt.id,
                question_id=UUID(q_id)
            )
            db.add(answer)

        db.commit()

    # Build question list for response (without correct answers)
    questions_data = []
    question_order = attempt.question_order or []
    answer_order = attempt.answer_order or {}

    for i, q_id in enumerate(question_order):
        question = db.query(Question).filter(Question.id == UUID(q_id)).first()
        if not question:
            continue

        q_data = {
            'id': str(question.id),
            'index': i,
            'question_text': question.question_text,
            'marks': question.marks
        }

        # Apply shuffled options or original
        if q_id in answer_order:
            # Reverse map to get options in shuffled order
            opt_map = answer_order[q_id]
            for new_key, orig_key in opt_map.items():
                orig_option = getattr(question, f'option_{orig_key.lower()}')
                q_data[f'option_{new_key.lower()}'] = orig_option
        else:
            q_data['option_a'] = question.option_a
            q_data['option_b'] = question.option_b
            q_data['option_c'] = question.option_c
            q_data['option_d'] = question.option_d

        questions_data.append(q_data)

    end_time = attempt.start_time + timedelta(minutes=exam.duration_minutes)

    return ExamAttemptStart(
        attempt_id=attempt.id,
        exam_id=exam.id,
        exam_title=exam.title,
        duration_minutes=exam.duration_minutes,
        total_questions=len(questions_data),
        start_time=attempt.start_time,
        end_time=end_time,
        questions=questions_data
    )


# ============ Get Attempt State ============

@router.get("/attempts/{attempt_id}", response_model=ExamAttemptState)
def get_attempt_state(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current state of an exam attempt"""
    student = get_student_from_user(current_user, db)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam),
        joinedload(ExamAttempt.answers)
    ).filter(
        ExamAttempt.id == attempt_id,
        ExamAttempt.student_id == student.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if attempt.status != 'in_progress':
        raise HTTPException(status_code=400, detail=f"Exam is {attempt.status}")

    # Calculate time remaining
    elapsed = (datetime.now() - attempt.start_time).total_seconds()
    time_limit = attempt.exam.duration_minutes * 60
    remaining = max(0, int(time_limit - elapsed))

    # Build answers dict
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
        answers=answers,
        marked_for_review=marked_for_review
    )


# ============ Submit Answer (Auto-save) ============

@router.post("/attempts/{attempt_id}/answer")
def submit_answer(
    attempt_id: UUID,
    answer_data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit/save an answer for a question (auto-save)"""
    student = get_student_from_user(current_user, db)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam)
    ).filter(
        ExamAttempt.id == attempt_id,
        ExamAttempt.student_id == student.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if attempt.status != 'in_progress':
        raise HTTPException(status_code=400, detail=f"Cannot modify {attempt.status} exam")

    # Check time
    elapsed = (datetime.now() - attempt.start_time).total_seconds()
    if elapsed > attempt.exam.duration_minutes * 60:
        attempt.status = 'timed_out'
        attempt.end_time = datetime.now()
        _calculate_results(attempt, db)
        db.commit()
        raise HTTPException(status_code=400, detail="Exam time has expired")

    # Find or create answer record
    answer = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt_id,
        StudentAnswer.question_id == answer_data.question_id
    ).first()

    if not answer:
        answer = StudentAnswer(
            attempt_id=attempt_id,
            question_id=answer_data.question_id
        )
        db.add(answer)

    # Map shuffled option back to original if needed
    selected = answer_data.selected_option
    if selected and attempt.answer_order:
        q_id = str(answer_data.question_id)
        if q_id in attempt.answer_order:
            opt_map = attempt.answer_order[q_id]
            selected = opt_map.get(selected, selected)

    answer.selected_option = selected
    answer.marked_for_review = answer_data.marked_for_review
    answer.answered_at = datetime.now()

    # Update time remaining
    remaining = max(0, int(attempt.exam.duration_minutes * 60 - elapsed))
    attempt.time_remaining_seconds = remaining

    db.commit()

    return {"status": "saved", "time_remaining": remaining}


# ============ Submit Exam ============

@router.post("/attempts/{attempt_id}/submit", response_model=ExamAttemptResponse)
def submit_exam(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit the exam for grading"""
    student = get_student_from_user(current_user, db)

    attempt = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam),
        joinedload(ExamAttempt.answers)
    ).filter(
        ExamAttempt.id == attempt_id,
        ExamAttempt.student_id == student.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if attempt.status != 'in_progress':
        raise HTTPException(status_code=400, detail=f"Exam is already {attempt.status}")

    attempt.status = 'submitted'
    attempt.end_time = datetime.now()

    _calculate_results(attempt, db)

    db.commit()
    db.refresh(attempt)

    return attempt


def _calculate_results(attempt: ExamAttempt, db: Session):
    """Calculate exam results after submission"""
    exam = attempt.exam
    answers = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt.id
    ).all()

    total_marks = 0
    obtained_marks = 0
    correct_count = 0
    answered_count = 0

    for ans in answers:
        question = db.query(Question).filter(Question.id == ans.question_id).first()
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

    # If show_result_immediately is enabled, auto-verify
    if exam.show_result_immediately:
        attempt.is_verified = True
        attempt.verified_at = datetime.now()


# ============ Get Results ============

@router.get("/results", response_model=List[ExamResultResponse])
def get_my_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all verified exam results for the student"""
    student = get_student_from_user(current_user, db)

    attempts = db.query(ExamAttempt).options(
        joinedload(ExamAttempt.exam).joinedload(Exam.course),
        joinedload(ExamAttempt.exam).joinedload(Exam.module)
    ).filter(
        ExamAttempt.student_id == student.id,
        ExamAttempt.is_verified == True
    ).order_by(ExamAttempt.created_at.desc()).all()

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
            verified_at=attempt.verified_at
        ))

    return results

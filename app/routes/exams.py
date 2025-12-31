from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.exam import Exam, Question, ExamSchedule
from app.models.course import Course
from app.models.course_module import CourseModule
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse, ExamDetailResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionBulkCreate,
    ExamScheduleCreate, ExamScheduleResponse, ExamScheduleDetailResponse
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


# ============ Exam CRUD ============

@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new exam for a course module"""
    require_manager(current_user)

    # Verify course exists and get institution
    course = db.query(Course).filter(Course.id == exam_data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Verify module exists and belongs to course
    module = db.query(CourseModule).filter(
        CourseModule.id == exam_data.module_id,
        CourseModule.course_id == exam_data.course_id
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found or doesn't belong to this course")

    # Determine institution_id
    institution_id = course.institution_id or current_user.institution_id
    if institution_id and current_user.role != "super_admin":
        check_resource_access(current_user, institution_id)

    new_exam = Exam(
        course_id=exam_data.course_id,
        module_id=exam_data.module_id,
        institution_id=institution_id,
        title=exam_data.title,
        description=exam_data.description,
        passing_marks=exam_data.passing_marks,
        duration_minutes=exam_data.duration_minutes,
        allow_retakes=exam_data.allow_retakes,
        max_retakes=exam_data.max_retakes,
        shuffle_questions=exam_data.shuffle_questions,
        shuffle_options=exam_data.shuffle_options,
        show_result_immediately=exam_data.show_result_immediately,
        batch_time=exam_data.batch_time,
        batch_month=exam_data.batch_month,
        batch_year=exam_data.batch_year,
        batch_identifier=exam_data.batch_identifier,
        created_by=current_user.id
    )

    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)

    return new_exam


@router.get("/", response_model=List[ExamResponse])
def list_exams(
    course_id: Optional[UUID] = None,
    module_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all exams with optional filters"""
    require_manager(current_user)

    query = db.query(Exam)

    # Filter by institution
    if current_user.role != "super_admin":
        query = query.filter(Exam.institution_id == current_user.institution_id)

    if course_id:
        query = query.filter(Exam.course_id == course_id)
    if module_id:
        query = query.filter(Exam.module_id == module_id)
    if is_active is not None:
        query = query.filter(Exam.is_active == is_active)

    exams = query.order_by(Exam.created_at.desc()).all()
    return exams


@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam(
    exam_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get exam details with questions"""
    require_manager(current_user)

    exam = db.query(Exam).options(
        joinedload(Exam.questions),
        joinedload(Exam.course),
        joinedload(Exam.module)
    ).filter(Exam.id == exam_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    # Build response with additional info
    response = ExamDetailResponse(
        id=exam.id,
        course_id=exam.course_id,
        module_id=exam.module_id,
        institution_id=exam.institution_id,
        title=exam.title,
        description=exam.description,
        total_questions=exam.total_questions,
        passing_marks=exam.passing_marks,
        duration_minutes=exam.duration_minutes,
        is_active=exam.is_active,
        allow_retakes=exam.allow_retakes,
        max_retakes=exam.max_retakes,
        shuffle_questions=exam.shuffle_questions,
        shuffle_options=exam.shuffle_options,
        show_result_immediately=exam.show_result_immediately,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        questions=[QuestionResponse.model_validate(q) for q in exam.questions if q.is_active],
        course_name=exam.course.name if exam.course else None,
        module_name=exam.module.module_name if exam.module else None
    )

    return response


@router.patch("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: UUID,
    update_data: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update exam details"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(exam, key, value)

    db.commit()
    db.refresh(exam)

    return exam


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an exam"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    db.delete(exam)
    db.commit()

    return None


# ============ Question Management ============

@router.post("/{exam_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def add_question(
    exam_id: UUID,
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a question to an exam"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    # Get next order index
    max_order = db.query(func.max(Question.order_index)).filter(
        Question.exam_id == exam_id
    ).scalar() or 0

    order_index = question_data.order_index if question_data.order_index is not None else max_order + 1

    new_question = Question(
        exam_id=exam_id,
        question_text=question_data.question_text,
        option_a=question_data.option_a,
        option_b=question_data.option_b,
        option_c=question_data.option_c,
        option_d=question_data.option_d,
        correct_option=question_data.correct_option.upper(),
        marks=question_data.marks,
        explanation=question_data.explanation,
        order_index=order_index
    )

    db.add(new_question)

    # Update exam total questions count
    exam.total_questions = db.query(func.count(Question.id)).filter(
        Question.exam_id == exam_id,
        Question.is_active == True
    ).scalar() + 1

    db.commit()
    db.refresh(new_question)

    return new_question


@router.post("/{exam_id}/questions/bulk", response_model=List[QuestionResponse], status_code=status.HTTP_201_CREATED)
def add_questions_bulk(
    exam_id: UUID,
    bulk_data: QuestionBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add multiple questions to an exam at once"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    # Get starting order index
    max_order = db.query(func.max(Question.order_index)).filter(
        Question.exam_id == exam_id
    ).scalar() or 0

    created_questions = []
    for i, q_data in enumerate(bulk_data.questions):
        order_index = q_data.order_index if q_data.order_index is not None else max_order + i + 1

        new_question = Question(
            exam_id=exam_id,
            question_text=q_data.question_text,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_option=q_data.correct_option.upper(),
            marks=q_data.marks,
            explanation=q_data.explanation,
            order_index=order_index
        )
        db.add(new_question)
        created_questions.append(new_question)

    # Update exam total questions count
    exam.total_questions = db.query(func.count(Question.id)).filter(
        Question.exam_id == exam_id,
        Question.is_active == True
    ).scalar() + len(bulk_data.questions)

    db.commit()

    for q in created_questions:
        db.refresh(q)

    return created_questions


@router.get("/{exam_id}/questions", response_model=List[QuestionResponse])
def get_exam_questions(
    exam_id: UUID,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all questions for an exam"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    query = db.query(Question).filter(Question.exam_id == exam_id)
    if not include_inactive:
        query = query.filter(Question.is_active == True)

    questions = query.order_by(Question.order_index).all()
    return questions


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: UUID,
    update_data: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a question"""
    require_manager(current_user)

    question = db.query(Question).options(
        joinedload(Question.exam)
    ).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, question.exam.institution_id)

    for key, value in update_data.model_dump(exclude_unset=True).items():
        if key == "correct_option" and value:
            value = value.upper()
        setattr(question, key, value)

    db.commit()
    db.refresh(question)

    # Update exam question count if active status changed
    if "is_active" in update_data.model_dump(exclude_unset=True):
        question.exam.total_questions = db.query(func.count(Question.id)).filter(
            Question.exam_id == question.exam_id,
            Question.is_active == True
        ).scalar()
        db.commit()

    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a question"""
    require_manager(current_user)

    question = db.query(Question).options(
        joinedload(Question.exam)
    ).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, question.exam.institution_id)

    exam = question.exam
    db.delete(question)

    # Update exam question count
    exam.total_questions = db.query(func.count(Question.id)).filter(
        Question.exam_id == exam.id,
        Question.is_active == True
    ).scalar() - 1

    db.commit()

    return None


# ============ Exam Scheduling ============

@router.post("/schedules", response_model=ExamScheduleResponse, status_code=status.HTTP_201_CREATED)
def schedule_exam(
    schedule_data: ExamScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule an exam for a specific batch"""
    require_manager(current_user)

    exam = db.query(Exam).filter(Exam.id == schedule_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, exam.institution_id)

    new_schedule = ExamSchedule(
        exam_id=schedule_data.exam_id,
        institution_id=exam.institution_id,
        batch_time=schedule_data.batch_time,
        batch_identifier=schedule_data.batch_identifier,
        batch_month=schedule_data.batch_month,
        batch_year=schedule_data.batch_year,
        scheduled_date=schedule_data.scheduled_date,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        created_by=current_user.id
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return new_schedule


@router.get("/schedules", response_model=List[ExamScheduleDetailResponse])
def list_schedules(
    exam_id: Optional[UUID] = None,
    batch_time: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List exam schedules with optional filters"""
    require_manager(current_user)

    query = db.query(ExamSchedule).options(
        joinedload(ExamSchedule.exam).joinedload(Exam.course),
        joinedload(ExamSchedule.exam).joinedload(Exam.module)
    )

    if current_user.role != "super_admin":
        query = query.filter(ExamSchedule.institution_id == current_user.institution_id)

    if exam_id:
        query = query.filter(ExamSchedule.exam_id == exam_id)
    if batch_time:
        query = query.filter(ExamSchedule.batch_time == batch_time)
    if scheduled_date:
        query = query.filter(ExamSchedule.scheduled_date == scheduled_date)

    schedules = query.filter(ExamSchedule.is_active == True).order_by(
        ExamSchedule.scheduled_date.desc(),
        ExamSchedule.start_time
    ).all()

    # Build response with additional info
    result = []
    for s in schedules:
        result.append(ExamScheduleDetailResponse(
            id=s.id,
            exam_id=s.exam_id,
            institution_id=s.institution_id,
            batch_time=s.batch_time,
            batch_identifier=s.batch_identifier,
            batch_month=s.batch_month,
            batch_year=s.batch_year,
            scheduled_date=s.scheduled_date,
            start_time=s.start_time,
            end_time=s.end_time,
            is_active=s.is_active,
            created_by=s.created_by,
            created_at=s.created_at,
            exam_title=s.exam.title if s.exam else None,
            course_name=s.exam.course.name if s.exam and s.exam.course else None,
            module_name=s.exam.module.module_name if s.exam and s.exam.module else None
        ))

    return result


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an exam schedule"""
    require_manager(current_user)

    schedule = db.query(ExamSchedule).filter(ExamSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role != "super_admin":
        check_resource_access(current_user, schedule.institution_id)

    schedule.is_active = False
    db.commit()

    return None

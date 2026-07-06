"""
Exam management. Tenant-scoped via ctx.q(Exam) (F-02/F-04). Per the
permission matrix (docs/01 §3): staff may author exams/questions, but
publishing an exam (is_active) and scheduling require staff_manager+.
Batch targeting lives ONLY on exam_schedules (one row per batch, F-08).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.dependencies import require_roles, MANAGER_ROLES, EXAM_AUTHOR_ROLES
from app.utils.docx_parser import DocxParseError, extract_docx_lines, parse_questions
from app.models.batch import Batch
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.exam import Exam, Question, ExamSchedule
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse, ExamDetailResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionBulkCreate,
    ExamScheduleCreate, ExamScheduleResponse, ExamScheduleDetailResponse,
)
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _get_exam_or_404(ctx: TenantContext, exam_id: UUID, options=()) -> Exam:
    query = ctx.q(Exam)
    for opt in options:
        query = query.options(opt)
    exam = query.filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def _get_question_scoped(ctx: TenantContext, question_id: UUID) -> Question:
    """Question scoped through its parent exam (questions carry no
    institution_id of their own)."""
    question = (
        ctx.db.query(Question)
        .join(Exam, Question.exam_id == Exam.id)
        .options(joinedload(Question.exam))
        .filter(Question.id == question_id)
    )
    if ctx.institution_id is not None:
        question = question.filter(Exam.institution_id == ctx.institution_id)
    question = question.first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


def _refresh_question_count(ctx: TenantContext, exam: Exam) -> None:
    exam.total_questions = ctx.db.query(func.count(Question.id)).filter(
        Question.exam_id == exam.id,
        Question.is_active == True,  # noqa: E712
    ).scalar() or 0


# ============ Exam CRUD ============

@router.post(
    "/",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def create_exam(
    exam_data: ExamCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Create an exam for a course module. Exams are ALWAYS institution-owned
    (F-04): tenant users get their own institution; super_admin must pass
    institution_id. Staff-authored exams start unpublished."""
    institution_id = ctx.require_institution_id(exam_data.institution_id)

    # Course must be global or owned by the target institution
    course = ctx.db.query(Course).filter(
        Course.id == exam_data.course_id,
        (Course.institution_id == institution_id) | (Course.institution_id.is_(None)),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    module = ctx.db.query(CourseModule).filter(
        CourseModule.id == exam_data.module_id,
        CourseModule.course_id == exam_data.course_id,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found or doesn't belong to this course")

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
        # Publishing requires staff_manager+ — staff authors start unpublished
        is_active=ctx.user.role in MANAGER_ROLES,
        created_by=ctx.user.id,
    )

    ctx.db.add(new_exam)
    ctx.db.commit()
    ctx.db.refresh(new_exam)
    return new_exam


@router.get(
    "/",
    response_model=List[ExamResponse],
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def list_exams(
    course_id: Optional[UUID] = None,
    module_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List exams in the caller's institution."""
    query = ctx.q(Exam)

    if course_id:
        query = query.filter(Exam.course_id == course_id)
    if module_id:
        query = query.filter(Exam.module_id == module_id)
    if is_active is not None:
        query = query.filter(Exam.is_active == is_active)

    return query.order_by(Exam.created_at.desc()).all()


# ============ Exam Scheduling ============

@router.post(
    "/schedules",
    response_model=ExamScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def schedule_exam(
    schedule_data: ExamScheduleCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Schedule an exam for exactly one batch (staff_manager+)."""
    exam = _get_exam_or_404(ctx, schedule_data.exam_id)

    # The batch must belong to the exam's institution
    batch = ctx.db.query(Batch).filter(
        Batch.id == schedule_data.batch_id,
        Batch.institution_id == exam.institution_id,
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    duplicate = ctx.db.query(ExamSchedule).filter(
        ExamSchedule.exam_id == exam.id,
        ExamSchedule.batch_id == batch.id,
        ExamSchedule.scheduled_date == schedule_data.scheduled_date,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="This exam is already scheduled for this batch on this date",
        )

    new_schedule = ExamSchedule(
        exam_id=exam.id,
        institution_id=exam.institution_id,
        batch_id=batch.id,
        scheduled_date=schedule_data.scheduled_date,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        created_by=ctx.user.id,
    )

    ctx.db.add(new_schedule)
    ctx.db.commit()
    ctx.db.refresh(new_schedule)
    return new_schedule


@router.get(
    "/schedules",
    response_model=List[ExamScheduleDetailResponse],
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def list_schedules(
    exam_id: Optional[UUID] = None,
    batch_id: Optional[UUID] = None,
    scheduled_date: Optional[str] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List exam schedules in the caller's institution."""
    query = ctx.q(ExamSchedule).options(
        joinedload(ExamSchedule.exam).joinedload(Exam.course),
        joinedload(ExamSchedule.exam).joinedload(Exam.module),
        joinedload(ExamSchedule.batch),
    )

    if exam_id:
        query = query.filter(ExamSchedule.exam_id == exam_id)
    if batch_id:
        query = query.filter(ExamSchedule.batch_id == batch_id)
    if scheduled_date:
        query = query.filter(ExamSchedule.scheduled_date == scheduled_date)

    schedules = query.filter(ExamSchedule.is_active == True).order_by(  # noqa: E712
        ExamSchedule.scheduled_date.desc(),
        ExamSchedule.start_time,
    ).all()

    return [
        ExamScheduleDetailResponse(
            id=s.id,
            exam_id=s.exam_id,
            institution_id=s.institution_id,
            batch_id=s.batch_id,
            scheduled_date=s.scheduled_date,
            start_time=s.start_time,
            end_time=s.end_time,
            is_active=s.is_active,
            created_by=s.created_by,
            created_at=s.created_at,
            exam_title=s.exam.title if s.exam else None,
            course_name=s.exam.course.name if s.exam and s.exam.course else None,
            module_name=s.exam.module.module_name if s.exam and s.exam.module else None,
            batch_name=s.batch.name if s.batch else None,
        )
        for s in schedules
    ]


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def cancel_schedule(
    schedule_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    schedule = ctx.q(ExamSchedule).filter(ExamSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = False
    ctx.db.commit()
    return None


@router.get(
    "/{exam_id}",
    response_model=ExamDetailResponse,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def get_exam(
    exam_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Exam details with questions (manager/author view — includes answers)."""
    exam = _get_exam_or_404(
        ctx, exam_id,
        options=(joinedload(Exam.questions), joinedload(Exam.course), joinedload(Exam.module)),
    )

    return ExamDetailResponse(
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
        module_name=exam.module.module_name if exam.module else None,
    )


@router.patch(
    "/{exam_id}",
    response_model=ExamResponse,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def update_exam(
    exam_id: UUID,
    update_data: ExamUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    exam = _get_exam_or_404(ctx, exam_id)

    changes = update_data.model_dump(exclude_unset=True)

    # Publishing gate: making an exam visible/schedulable needs staff_manager+
    if "is_active" in changes and ctx.user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Publishing an exam requires staff_manager or above",
        )

    for key, value in changes.items():
        setattr(exam, key, value)

    ctx.db.commit()
    ctx.db.refresh(exam)
    return exam


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def delete_exam(
    exam_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    exam = _get_exam_or_404(ctx, exam_id)
    ctx.db.delete(exam)
    ctx.db.commit()
    return None


# ============ Question Management ============

@router.post(
    "/{exam_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def add_question(
    exam_id: UUID,
    question_data: QuestionCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    exam = _get_exam_or_404(ctx, exam_id)

    max_order = ctx.db.query(func.max(Question.order_index)).filter(
        Question.exam_id == exam.id
    ).scalar() or 0
    order_index = question_data.order_index if question_data.order_index is not None else max_order + 1

    new_question = Question(
        exam_id=exam.id,
        question_text=question_data.question_text,
        image_url=question_data.image_url,
        option_a=question_data.option_a,
        option_b=question_data.option_b,
        option_c=question_data.option_c,
        option_d=question_data.option_d,
        correct_option=question_data.correct_option.upper(),
        marks=question_data.marks,
        explanation=question_data.explanation,
        order_index=order_index,
    )
    ctx.db.add(new_question)
    ctx.db.flush()

    _refresh_question_count(ctx, exam)
    ctx.db.commit()
    ctx.db.refresh(new_question)
    return new_question


# Word imports are question text only; anything larger is almost certainly
# the wrong file (embedded images etc. belong in image_url, not the doc).
MAX_IMPORT_DOCX_BYTES = 2 * 1024 * 1024


@router.post(
    "/{exam_id}/questions/import-docx",
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
async def import_questions_docx(
    exam_id: UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(get_tenant),
):
    """Parse a Word (.docx) question paper into importable questions.

    Parse-only preview: nothing is written. The client shows the result to
    the author, who confirms via POST /{exam_id}/questions/bulk — so a
    half-broken document never silently imports its broken half.
    """
    _get_exam_or_404(ctx, exam_id)  # existence + tenant check

    if file.filename and not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported. Save the document as .docx in Word and retry.",
        )
    data = await file.read()
    if len(data) > MAX_IMPORT_DOCX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 2 MB)")

    try:
        lines = extract_docx_lines(data)
    except DocxParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    parsed, errors = parse_questions(lines)
    return {
        "questions": [
            {
                "question_text": q.question_text,
                "option_a": q.options["A"],
                "option_b": q.options["B"],
                "option_c": q.options["C"],
                "option_d": q.options["D"],
                "correct_option": q.correct_option,
                "marks": q.marks,
                "explanation": q.explanation,
            }
            for q in parsed
        ],
        "errors": errors,
    }


@router.post(
    "/{exam_id}/questions/bulk",
    response_model=List[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def add_questions_bulk(
    exam_id: UUID,
    bulk_data: QuestionBulkCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    exam = _get_exam_or_404(ctx, exam_id)

    max_order = ctx.db.query(func.max(Question.order_index)).filter(
        Question.exam_id == exam.id
    ).scalar() or 0

    created_questions = []
    for i, q_data in enumerate(bulk_data.questions):
        order_index = q_data.order_index if q_data.order_index is not None else max_order + i + 1
        new_question = Question(
            exam_id=exam.id,
            question_text=q_data.question_text,
            image_url=q_data.image_url,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_option=q_data.correct_option.upper(),
            marks=q_data.marks,
            explanation=q_data.explanation,
            order_index=order_index,
        )
        ctx.db.add(new_question)
        created_questions.append(new_question)

    ctx.db.flush()
    _refresh_question_count(ctx, exam)
    ctx.db.commit()

    for q in created_questions:
        ctx.db.refresh(q)
    return created_questions


@router.get(
    "/{exam_id}/questions",
    response_model=List[QuestionResponse],
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def get_exam_questions(
    exam_id: UUID,
    include_inactive: bool = False,
    ctx: TenantContext = Depends(get_tenant),
):
    exam = _get_exam_or_404(ctx, exam_id)

    query = ctx.db.query(Question).filter(Question.exam_id == exam.id)
    if not include_inactive:
        query = query.filter(Question.is_active == True)  # noqa: E712

    return query.order_by(Question.order_index).all()


@router.patch(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def update_question(
    question_id: UUID,
    update_data: QuestionUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    question = _get_question_scoped(ctx, question_id)

    changes = update_data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "correct_option" and value:
            value = value.upper()
        setattr(question, key, value)

    if "is_active" in changes:
        _refresh_question_count(ctx, question.exam)

    ctx.db.commit()
    ctx.db.refresh(question)
    return question


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(EXAM_AUTHOR_ROLES))],
)
def delete_question(
    question_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    question = _get_question_scoped(ctx, question_id)
    exam = question.exam
    ctx.db.delete(question)
    ctx.db.flush()

    _refresh_question_count(ctx, exam)
    ctx.db.commit()
    return None

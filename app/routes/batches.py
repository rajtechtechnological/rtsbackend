"""
Batches CRUD (F-08). Managing batches requires staff_manager+ per the
permission matrix (docs/01 §3); reads are open to all staff roles because
receptionists need the batch list to register students.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.dependencies import require_roles, MANAGER_ROLES, ALL_STAFF_ROLES
from app.models.batch import Batch
from app.models.student import Student
from app.schemas.batch import BatchCreate, BatchUpdate, BatchResponse
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _get_batch_or_404(ctx: TenantContext, batch_id: UUID) -> Batch:
    batch = ctx.q(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        # Out-of-tenant rows are indistinguishable from missing rows (404).
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@router.post(
    "/",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def create_batch(
    batch_data: BatchCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    institution_id = ctx.require_institution_id(batch_data.institution_id)

    duplicate = ctx.db.query(Batch).filter(
        Batch.institution_id == institution_id,
        Batch.start_time == batch_data.start_time,
        Batch.month == batch_data.month,
        Batch.year == batch_data.year,
        Batch.identifier == batch_data.identifier,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A batch with this slot already exists")

    batch = Batch(
        institution_id=institution_id,
        name=batch_data.name,
        start_time=batch_data.start_time,
        end_time=batch_data.end_time,
        month=batch_data.month,
        year=batch_data.year,
        identifier=batch_data.identifier,
    )
    ctx.db.add(batch)
    ctx.db.commit()
    ctx.db.refresh(batch)
    return batch


@router.get(
    "/",
    response_model=List[BatchResponse],
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def list_batches(
    is_active: Optional[bool] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    query = ctx.q(Batch)
    if is_active is not None:
        query = query.filter(Batch.is_active == is_active)
    if month is not None:
        query = query.filter(Batch.month == month)
    if year is not None:
        query = query.filter(Batch.year == year)
    return query.order_by(Batch.year.desc(), Batch.month.desc(), Batch.start_time).all()


@router.get(
    "/{batch_id}",
    response_model=BatchResponse,
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_batch(
    batch_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _get_batch_or_404(ctx, batch_id)


@router.patch(
    "/{batch_id}",
    response_model=BatchResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def update_batch(
    batch_id: UUID,
    update_data: BatchUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    batch = _get_batch_or_404(ctx, batch_id)
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(batch, key, value)
    ctx.db.commit()
    ctx.db.refresh(batch)
    return batch


@router.delete(
    "/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def delete_batch(
    batch_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    batch = _get_batch_or_404(ctx, batch_id)
    has_students = ctx.db.query(Student).filter(Student.batch_id == batch_id).first()
    if has_students:
        raise HTTPException(
            status_code=409,
            detail="Batch has students assigned; deactivate it instead",
        )
    ctx.db.delete(batch)
    ctx.db.commit()
    return None

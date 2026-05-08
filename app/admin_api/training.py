from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission
from app.schemas.training import (
    TrainingCategoryResponse,
    TrainingCategoryCreate,
    TrainingCategoryUpdate,
    TrainingLessonResponse,
    TrainingLessonDetail,
    TrainingLessonCreate,
    TrainingLessonUpdate,
    to_training_category_response,
    to_training_lesson_response,
    to_training_lesson_detail,
)
from app.services.training_service import training_service

router = APIRouter()


@router.get("/categories", response_model=List[TrainingCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.view"))
):
    """List all categories (including inactive ones for admin)."""
    # For admin, we use the repo directly to get all
    from app.repositories.training import training_category_repo
    categories = await training_category_repo.get_all(db)
    return [to_training_category_response(c) for c in categories]


@router.post("/categories", response_model=TrainingCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: TrainingCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.create"))
):
    """Create a new training category."""
    category = await training_service.create_category(db, data.model_dump())
    return to_training_category_response(category)


@router.patch("/categories/{category_id}", response_model=TrainingCategoryResponse)
async def update_category(
    category_id: UUID,
    data: TrainingCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.update"))
):
    """Update a training category."""
    try:
        category = await training_service.update_category(db, category_id, data.model_dump(exclude_unset=True))
        return to_training_category_response(category)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.delete"))
):
    """Delete a training category."""
    success = await training_service.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")


@router.get("/lessons", response_model=List[TrainingLessonResponse])
async def list_lessons(
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.view"))
):
    """List all lessons (including inactive ones for admin)."""
    from app.repositories.training import training_lesson_repo
    lessons = await training_lesson_repo.get_all(db)
    return [to_training_lesson_response(l) for l in lessons]


@router.post("/lessons", response_model=TrainingLessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    data: TrainingLessonCreate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.create"))
):
    """Create a new training lesson."""
    lesson = await training_service.create_lesson(db, data.model_dump())
    return to_training_lesson_response(lesson)


@router.patch("/lessons/{lesson_id}", response_model=TrainingLessonResponse)
async def update_lesson(
    lesson_id: UUID,
    data: TrainingLessonUpdate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.update"))
):
    """Update a training lesson."""
    try:
        lesson = await training_service.update_lesson(db, lesson_id, data.model_dump(exclude_unset=True))
        return to_training_lesson_response(lesson)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("training.delete"))
):
    """Delete a training lesson."""
    success = await training_service.delete_lesson(db, lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lesson not found")

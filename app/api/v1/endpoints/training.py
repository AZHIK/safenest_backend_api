from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, allow_anonymous
from app.schemas.training import (
    TrainingCategoryResponse,
    TrainingLessonResponse,
    TrainingLessonDetail,
    to_training_category_response,
    to_training_lesson_response,
    to_training_lesson_detail,
)
from app.services.training_service import training_service

router = APIRouter()


@router.get("/categories", response_model=List[TrainingCategoryResponse])
async def get_categories(
    featured: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get all training categories."""
    if featured:
        categories = await training_service.get_featured_categories(db, limit)
    else:
        categories = await training_service.get_all_categories(db)
    return [to_training_category_response(c) for c in categories]


@router.get("/categories/{slug}", response_model=TrainingCategoryResponse)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get category by slug."""
    category = await training_service.get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return to_training_category_response(category)


@router.get("/lessons", response_model=List[TrainingLessonResponse])
async def get_lessons(
    skip: int = 0,
    limit: int = 50,
    category_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get training lessons."""
    if category_id:
        lessons = await training_service.get_lessons_by_category(db, category_id)
    else:
        lessons = await training_service.get_all_lessons(db, skip, limit)
    return [to_training_lesson_response(l) for l in lessons]


@router.get("/lesson/{lesson_id}", response_model=TrainingLessonDetail)
async def get_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get lesson details."""
    try:
        lesson = await training_service.get_lesson_detail(db, lesson_id)
        return to_training_lesson_detail(lesson)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/lesson/slug/{slug}", response_model=TrainingLessonResponse)
async def get_lesson_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get lesson by slug."""
    lesson = await training_service.get_lesson_by_slug(db, slug)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return to_training_lesson_response(lesson)

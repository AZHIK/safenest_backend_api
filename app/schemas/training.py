from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainingCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    icon_name: Optional[str]
    color_code: Optional[str]
    sort_order: int
    is_active: bool
    is_featured: bool
    lesson_count: int


class TrainingLessonBase(BaseModel):
    title: str
    slug: str
    description: Optional[str]
    duration_minutes: Optional[int]
    difficulty_level: str
    is_active: bool
    is_premium: bool


class TrainingLessonResponse(TrainingLessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    thumbnail_url: Optional[str]
    view_count: int
    sort_order: int
    created_at: datetime


class ContentBlock(BaseModel):
    type: str = Field(pattern=r"^(text|video|audio|image|quiz|interactive)$")
    content: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[dict] = None


class TrainingLessonDetail(TrainingLessonResponse):
    content_blocks: Optional[List[ContentBlock]] = None
    video_url: Optional[str]
    audio_url: Optional[str]
    pdf_url: Optional[str]
    tags: Optional[str]
    related_lesson_ids: Optional[List[str]] = None
    completion_count: int
    rating_average: float
    rating_count: int


# --- Management Schemas ---

class TrainingCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon_name: Optional[str] = Field(default=None, max_length=50)
    color_code: Optional[str] = Field(default=None, max_length=7)
    sort_order: int = 0
    is_active: bool = True
    is_featured: bool = False


class TrainingCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_name: Optional[str] = None
    color_code: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class TrainingLessonCreate(BaseModel):
    category_id: UUID
    title: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=200)
    description: Optional[str] = None
    content_blocks: Optional[List[ContentBlock]] = None
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    video_url: Optional[str] = Field(default=None, max_length=500)
    audio_url: Optional[str] = Field(default=None, max_length=500)
    pdf_url: Optional[str] = Field(default=None, max_length=500)
    duration_minutes: Optional[int] = None
    difficulty_level: str = "beginner"
    is_active: bool = True
    is_premium: bool = False
    requires_login: bool = False
    sort_order: int = 0
    tags: Optional[str] = None


class TrainingLessonUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    content_blocks: Optional[List[ContentBlock]] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    pdf_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty_level: Optional[str] = None
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None
    requires_login: Optional[bool] = None
    sort_order: Optional[int] = None
    tags: Optional[str] = None


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_training_category_response(category) -> TrainingCategoryResponse:
    """Convert TrainingCategory ORM to response schema."""
    return TrainingCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon_name=category.icon_name,
        color_code=category.color_code,
        sort_order=category.sort_order,
        is_active=category.is_active,
        is_featured=category.is_featured,
        lesson_count=category.lesson_count
    )


def to_training_lesson_response(lesson) -> TrainingLessonResponse:
    """Convert TrainingLesson ORM to response schema."""
    return TrainingLessonResponse(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        description=lesson.description,
        duration_minutes=lesson.duration_minutes,
        difficulty_level=lesson.difficulty_level,
        is_active=lesson.is_active,
        is_premium=lesson.is_premium,
        category_id=lesson.category_id,
        thumbnail_url=lesson.thumbnail_url,
        view_count=lesson.view_count,
        sort_order=lesson.sort_order,
        created_at=lesson.created_at
    )


def to_training_lesson_detail(lesson) -> TrainingLessonDetail:
    """Convert TrainingLesson ORM with category to detail schema.
    
    Must be called after category relationship is eager-loaded.
    """
    import json
    content_blocks = None
    if lesson.content_blocks:
        try:
            content_blocks = json.loads(lesson.content_blocks)
        except:
            pass
    
    related_ids = None
    if lesson.related_lesson_ids:
        try:
            related_ids = json.loads(lesson.related_lesson_ids)
        except:
            pass
    
    return TrainingLessonDetail(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        description=lesson.description,
        duration_minutes=lesson.duration_minutes,
        difficulty_level=lesson.difficulty_level,
        is_active=lesson.is_active,
        is_premium=lesson.is_premium,
        category_id=lesson.category_id,
        thumbnail_url=lesson.thumbnail_url,
        view_count=lesson.view_count,
        sort_order=lesson.sort_order,
        created_at=lesson.created_at,
        content_blocks=content_blocks,
        video_url=lesson.video_url,
        audio_url=lesson.audio_url,
        pdf_url=lesson.pdf_url,
        tags=lesson.tags,
        related_lesson_ids=related_ids,
        completion_count=lesson.completion_count,
        rating_average=lesson.rating_average,
        rating_count=lesson.rating_count
    )

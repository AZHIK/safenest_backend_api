import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlmodel import Field, Relationship, SQLModel


class TrainingCategory(SQLModel, table=True):
    __tablename__ = "training_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Basic info
    name: str = Field(max_length=100, unique=True)
    slug: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Display
    icon_name: Optional[str] = Field(default=None, max_length=50)
    color_code: Optional[str] = Field(default=None, max_length=7)  # Hex color
    sort_order: int = Field(default=0)

    # Metadata
    is_active: bool = Field(default=True, index=True)
    is_featured: bool = Field(default=False)
    lesson_count: int = Field(default=0)

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Relationships
    lessons: List["TrainingLesson"] = Relationship(back_populates="category", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    def __repr__(self):
        return f"<TrainingCategory(id={self.id}, name={self.name})>"


class TrainingLesson(SQLModel, table=True):
    __tablename__ = "training_lessons"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(sa_column=Column(ForeignKey("training_categories.id", ondelete="CASCADE"), index=True))

    # Content
    title: str = Field(max_length=200)
    slug: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Content blocks (JSON structure for flexible content)
    content_blocks: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON: [{type: "text", content: "..."}, {type: "video", url: "..."}]

    # Media
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    video_url: Optional[str] = Field(default=None, max_length=500)
    audio_url: Optional[str] = Field(default=None, max_length=500)
    pdf_url: Optional[str] = Field(default=None, max_length=500)

    # Duration
    duration_minutes: Optional[int] = Field(default=None)
    difficulty_level: str = Field(default="beginner", max_length=20)  # beginner, intermediate, advanced

    # Engagement
    view_count: int = Field(default=0)
    completion_count: int = Field(default=0)
    rating_average: float = Field(default=0.0)
    rating_count: int = Field(default=0)

    # Status
    is_active: bool = Field(default=True, index=True)
    is_premium: bool = Field(default=False)
    requires_login: bool = Field(default=False)

    # Ordering
    sort_order: int = Field(default=0)

    # Metadata
    tags: Optional[str] = Field(default=None, max_length=255)  # Comma-separated
    related_lesson_ids: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON array of UUIDs

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Relationships
    category: "TrainingCategory" = Relationship(back_populates="lessons")

    def __repr__(self):
        return f"<TrainingLesson(id={self.id}, title={self.title}, category={self.category_id})>"

    def estimate_read_time(self) -> int:
        if self.duration_minutes:
            return self.duration_minutes
        # Rough estimate: 200 words per minute
        if self.content_blocks:
            try:
                import json
                blocks = json.loads(self.content_blocks)
                text_content = " ".join([b.get("content", "") for b in blocks if b.get("type") == "text"])
                return max(1, len(text_content.split()) // 200)
            except:
                pass
        return 5  # Default 5 minutes

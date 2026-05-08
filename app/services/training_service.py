from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingCategory, TrainingLesson
from app.repositories.training import training_category_repo, training_lesson_repo


class TrainingService:
    async def get_all_categories(
        self,
        db: AsyncSession
    ) -> List[TrainingCategory]:
        """Get all active categories. Returns ORM objects (caller must map to schema)."""
        return await training_category_repo.get_active(db)

    async def get_featured_categories(
        self,
        db: AsyncSession,
        limit: int = 3
    ) -> List[TrainingCategory]:
        """Get featured categories. Returns ORM objects (caller must map to schema)."""
        return await training_category_repo.get_featured(db, limit)

    async def get_category_by_slug(
        self,
        db: AsyncSession,
        slug: str
    ) -> Optional[TrainingCategory]:
        """Get category by slug. Returns ORM object (caller must map to schema)."""
        return await training_category_repo.get_by_slug(db, slug)

    async def get_lessons_by_category(
        self,
        db: AsyncSession,
        category_id: UUID
    ) -> List[TrainingLesson]:
        """Get lessons by category. Returns ORM objects (caller must map to schema)."""
        return await training_lesson_repo.get_by_category(db, category_id)

    async def get_lesson_detail(
        self,
        db: AsyncSession,
        lesson_id: UUID
    ) -> TrainingLesson:
        """Get lesson detail with category. Returns ORM object (caller must map to schema)."""
        lesson = await training_lesson_repo.get_by_id_full(db, lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")

        # Increment view count
        await training_lesson_repo.increment_view_count(db, lesson_id)

        return lesson

    async def get_lesson_by_slug(
        self,
        db: AsyncSession,
        slug: str
    ) -> Optional[TrainingLesson]:
        """Get lesson by slug. Returns ORM object (caller must map to schema)."""
        return await training_lesson_repo.get_by_slug(db, slug)

    async def get_all_lessons(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> List[TrainingLesson]:
        """Get all active lessons. Returns ORM objects (caller must map to schema)."""
        return await training_lesson_repo.get_active(db, skip, limit)

    # --- Management Methods ---

    async def create_category(
        self,
        db: AsyncSession,
        data: dict
    ) -> TrainingCategory:
        return await training_category_repo.create(db, data)

    async def update_category(
        self,
        db: AsyncSession,
        category_id: UUID,
        data: dict
    ) -> TrainingCategory:
        category = await training_category_repo.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        return await training_category_repo.update(db, category, data)

    async def delete_category(
        self,
        db: AsyncSession,
        category_id: UUID
    ) -> bool:
        return await training_category_repo.delete(db, category_id)

    async def create_lesson(
        self,
        db: AsyncSession,
        data: dict
    ) -> TrainingLesson:
        import json
        if "content_blocks" in data and data["content_blocks"] is not None:
            data["content_blocks"] = json.dumps([b.model_dump() if hasattr(b, "model_dump") else b for b in data["content_blocks"]])
        return await training_lesson_repo.create(db, data)

    async def update_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID,
        data: dict
    ) -> TrainingLesson:
        import json
        lesson = await training_lesson_repo.get_by_id(db, lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")
        
        if "content_blocks" in data and data["content_blocks"] is not None:
            data["content_blocks"] = json.dumps([b.model_dump() if hasattr(b, "model_dump") else b for b in data["content_blocks"]])
            
        return await training_lesson_repo.update(db, lesson, data)

    async def delete_lesson(
        self,
        db: AsyncSession,
        lesson_id: UUID
    ) -> bool:
        return await training_lesson_repo.delete(db, lesson_id)


training_service = TrainingService()

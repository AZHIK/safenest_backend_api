from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.training import TrainingCategory, TrainingLesson
from app.repositories.base import BaseRepository


class TrainingCategoryRepository(BaseRepository[TrainingCategory]):
    def __init__(self):
        super().__init__(TrainingCategory)

    async def get_active(self, db: AsyncSession) -> List[TrainingCategory]:
        result = await db.execute(
            select(TrainingCategory)
            .where(TrainingCategory.is_active == True)
            .order_by(TrainingCategory.sort_order, TrainingCategory.name)
        )
        return result.scalars().all()

    async def get_featured(self, db: AsyncSession, limit: int = 3) -> List[TrainingCategory]:
        result = await db.execute(
            select(TrainingCategory)
            .where(
                TrainingCategory.is_active == True,
                TrainingCategory.is_featured == True
            )
            .order_by(TrainingCategory.sort_order)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[TrainingCategory]:
        result = await db.execute(
            select(TrainingCategory).where(TrainingCategory.slug == slug)
        )
        return result.scalar_one_or_none()


class TrainingLessonRepository(BaseRepository[TrainingLesson]):
    def __init__(self):
        super().__init__(TrainingLesson)

    async def get_by_category(
        self,
        db: AsyncSession,
        category_id: UUID,
        include_inactive: bool = False
    ) -> List[TrainingLesson]:
        query = select(TrainingLesson).where(
            TrainingLesson.category_id == category_id
        )
        if not include_inactive:
            query = query.where(TrainingLesson.is_active == True)

        result = await db.execute(
            query.order_by(TrainingLesson.sort_order, TrainingLesson.title)
        )
        return result.scalars().all()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[TrainingLesson]:
        result = await db.execute(
            select(TrainingLesson).where(TrainingLesson.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_id_full(self, db: AsyncSession, lesson_id: UUID) -> Optional[TrainingLesson]:
        result = await db.execute(
            select(TrainingLesson)
            .options(selectinload(TrainingLesson.category))
            .where(TrainingLesson.id == lesson_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> List[TrainingLesson]:
        result = await db.execute(
            select(TrainingLesson)
            .where(TrainingLesson.is_active == True)
            .order_by(TrainingLesson.sort_order, TrainingLesson.title)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def increment_view_count(self, db: AsyncSession, lesson_id: UUID) -> None:
        from sqlalchemy import update
        await db.execute(
            update(TrainingLesson)
            .where(TrainingLesson.id == lesson_id)
            .values(view_count=TrainingLesson.view_count + 1)
        )
        await db.flush()


training_category_repo = TrainingCategoryRepository()
training_lesson_repo = TrainingLessonRepository()

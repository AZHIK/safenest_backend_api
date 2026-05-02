import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import application models and config
from sqlmodel import SQLModel
from app.core.config import get_settings

# Import all models to ensure they are registered with SQLModel.metadata
from app.models import (
    User, AnonymousSession, TrustedContact, OTPCode,
    SOSAlert, LocationPing,
    IncidentReport, EvidenceFile,
    Conversation, ConversationParticipant, Message,
    SupportCenter,
    TrainingCategory, TrainingLesson,
)

settings = get_settings()
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

def include_object(object, name, type_, reflected, compare_to):
    """
    Nuclear Filter: Only include objects that are explicitly defined in 
    our SQLModel metadata. This automatically ignores ALL PostGIS, 
    TIGER, and internal Postgres system tables.
    """
    if type_ == "table":
        # Only manage tables that exist in our Python models code
        return name in target_metadata.tables
    
    # For indexes and sequences, we generally let them pass if their 
    # parent tables passed the check above.
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    """Run actual synchronous migrations."""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_object=include_object,
        render_as_batch=False 
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
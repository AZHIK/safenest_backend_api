#!/usr/bin/env python
from __future__ import annotations

import asyncio
import getpass
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.disable(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").disabled = True

from sqlalchemy import func, select

from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal, engine
from app.operator_models.operator import OperatorUser
from scripts.rbac_seed import (
    SUPER_ADMIN_ROLE_NAME,
    assign_roles_to_user,
    get_roles_by_name,
)


def prompt_required(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValueError(f"{prompt.rstrip(': ')} is required.")
    return value


def get_email() -> str:
    email = prompt_required("Email: ").lower()
    if "@" not in email:
        raise ValueError("Email must be a valid email address.")
    return email


def get_password() -> str:
    password = getpass.getpass("Password: ")
    repeat_password = getpass.getpass("Repeat password: ")

    if password != repeat_password:
        raise ValueError("Passwords do not match.")
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")

    return password


async def main() -> int:
    email = get_email()
    full_name = prompt_required("Full name: ")
    password = get_password()

    async with AsyncSessionLocal() as db:
        roles, missing_roles = await get_roles_by_name(db, [SUPER_ADMIN_ROLE_NAME])
        if missing_roles:
            print(
                "Missing RBAC role(s): "
                f"{', '.join(missing_roles)}. Run `python scripts/rbac_seed.py` first.",
                file=sys.stderr,
            )
            return 1

        result = await db.execute(
            select(OperatorUser).where(func.lower(OperatorUser.email) == email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            print(f"Admin already exists: {email}", file=sys.stderr)
            return 1

        user = OperatorUser(
            full_name=full_name,
            email=email,
            password_hash=get_password_hash(password),
            is_active=True,
            is_super_admin=True,
            email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()

        assigned_count = await assign_roles_to_user(db, user.id, roles)
        await db.commit()

        print(
            "Admin user created successfully: "
            f"{user.email} assigned to `{SUPER_ADMIN_ROLE_NAME}` role."
        )

    await engine.dispose()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except (KeyboardInterrupt, EOFError):
        print("\nAdmin creation cancelled.", file=sys.stderr)
        raise SystemExit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

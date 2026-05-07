from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.disable(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").disabled = True

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, engine
from app.operator_models.operator import Role, UserRoleLink
from app.operator_repositories.role import role_repo
from app.rbac.permission_enum import SYSTEM_ROLE_PERMISSIONS

SUPER_ADMIN_ROLE_NAME = "super_admin"


async def upsert_default_roles(db: AsyncSession) -> list[tuple[str, int, str]]:
    """Create/update system roles from the PermissionEnum source of truth."""
    results: list[tuple[str, int, str]] = []

    for role_name, permissions in SYSTEM_ROLE_PERMISSIONS.items():
        permission_codes = sorted(permissions)
        role = await role_repo.get_by_name(db, role_name)
        action = "updated"

        if role is None:
            role = Role(
                name=role_name,
                description=f"System role: {role_name}",
                is_system=True,
            )
            db.add(role)
            await db.flush()
            action = "created"
        else:
            role.is_system = True
            if not role.description:
                role.description = f"System role: {role_name}"

        await role_repo.assign_permissions(
            db,
            role.id,
            permission_codes,
            replace_existing=True,
        )
        results.append((role_name, len(permission_codes), action))

    await db.commit()
    return results


async def get_roles_by_name(
    db: AsyncSession,
    role_names: Iterable[str],
) -> tuple[list[Role], list[str]]:
    roles: list[Role] = []
    missing: list[str] = []

    for role_name in role_names:
        role = await role_repo.get_by_name(db, role_name)
        if role is None:
            missing.append(role_name)
        else:
            roles.append(role)

    return roles, missing


async def assign_roles_to_user(
    db: AsyncSession,
    user_id,
    roles: Iterable[Role],
) -> int:
    result = await db.execute(
        select(UserRoleLink.role_id).where(UserRoleLink.user_id == user_id)
    )
    existing_role_ids = {row[0] for row in result.all()}

    assigned_count = 0
    for role in roles:
        if role.id in existing_role_ids:
            continue
        db.add(UserRoleLink(user_id=user_id, role_id=role.id))
        assigned_count += 1

    return assigned_count


async def main() -> int:
    async with AsyncSessionLocal() as db:
        results = await upsert_default_roles(db)

    created_count = sum(1 for _, _, action in results if action == "created")
    updated_count = sum(1 for _, _, action in results if action == "updated")
    permission_count = sum(count for _, count, _ in results)

    print(
        "RBAC seed completed successfully: "
        f"{len(results)} roles synced, {created_count} created, "
        f"{updated_count} updated, {permission_count} permissions assigned."
    )

    await engine.dispose()
    return 0


if __name__ == "__main__":
    import asyncio

    try:
        raise SystemExit(asyncio.run(main()))
    except (KeyboardInterrupt, EOFError):
        print("\nRBAC seed cancelled.", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

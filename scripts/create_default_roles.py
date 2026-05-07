#!/usr/bin/env python
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.rbac_seed import main as seed_rbac


async def main() -> int:
    return await seed_rbac()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

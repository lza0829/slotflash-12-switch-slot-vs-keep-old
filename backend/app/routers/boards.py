from __future__ import annotations
from fastapi import APIRouter
from app.db import db

router = APIRouter(tags=["板卡"])


@router.get("/板卡")
def list_boards():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, active_slot, watchdog_sec FROM boards ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

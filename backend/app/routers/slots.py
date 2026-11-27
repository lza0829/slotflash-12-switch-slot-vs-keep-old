from __future__ import annotations
from fastapi import APIRouter
from app.db import db

router = APIRouter(tags=["闪槽"])


@router.get("/闪槽")
def list_slots():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.board_id, b.name AS board_name, s.slot_key, s.role,
                   s.firmware_id, f.version AS firmware_version, s.write_state, s.boot_color
            FROM slots s
            JOIN boards b ON b.id = s.board_id
            LEFT JOIN firmwares f ON f.id = s.firmware_id
            ORDER BY s.board_id, s.slot_key
            """
        ).fetchall()
        return [dict(r) for r in rows]

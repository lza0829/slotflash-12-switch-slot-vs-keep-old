from __future__ import annotations
from fastapi import APIRouter
from app.db import db
from app.services import promotion

router = APIRouter(tags=["校验屏"])


@router.get("/校验")
def align_snapshot():
    with db() as conn:
        slots = conn.execute(
            """
            SELECT s.board_id, b.name AS board_name, s.slot_key, s.role, s.write_state,
                   s.boot_color, b.active_slot
            FROM slots s JOIN boards b ON b.id=s.board_id
            ORDER BY s.board_id, s.slot_key
            """
        ).fetchall()
        boots = conn.execute(
            "SELECT board_id, color, fail_streak, pending_slot FROM boot_chain"
        ).fetchall()
        orders = conn.execute(
            "SELECT id, board_id, target_slot, status FROM flash_orders ORDER BY id DESC LIMIT 20"
        ).fetchall()
        policy = conn.execute("SELECT mode, hold_sec FROM rollback_policy WHERE id=1").fetchone()
        boards = conn.execute("SELECT id FROM boards ORDER BY id").fetchall()
        readouts = [promotion.readout(conn, b["id"]) for b in boards]
        return {
            "闪槽投影": [dict(r) for r in slots],
            "启动链投影": [dict(r) for r in boots],
            "写闪近单": [dict(r) for r in orders],
            "回退拨": dict(policy) if policy else {},
            "升格口径": promotion.policy_view(),
            "现运行对读": readouts,
        }

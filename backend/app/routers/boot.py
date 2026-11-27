from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import db
from app.services.common import now_iso

router = APIRouter(tags=["启动链"])


class BootBody(BaseModel):
    board_id: int
    target_slot: str = Field(pattern="^[AB]$")


class BootColorBody(BaseModel):
    color: str
    fail_streak: int = 0


@router.get("/启动链")
def list_boot():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.board_id, b.name AS board_name, b.active_slot, c.pending_slot,
                   c.color, c.fail_streak, c.updated_at
            FROM boot_chain c
            JOIN boards b ON b.id = c.board_id
            ORDER BY c.board_id
            """
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/启动链/切槽")
def switch_slot(body: BootBody):
    with db() as conn:
        board = conn.execute("SELECT * FROM boards WHERE id=?", (body.board_id,)).fetchone()
        slot = conn.execute(
            "SELECT * FROM slots WHERE board_id=? AND slot_key=?",
            (body.board_id, body.target_slot),
        ).fetchone()
        if not board or not slot:
            raise HTTPException(400, "板卡或槽位不存在")
        ts = now_iso()
        # 底座占位：直接把目标槽标现运行，旧槽改空闲
        conn.execute(
            "UPDATE slots SET role=? WHERE board_id=? AND slot_key!=?",
            ("空闲", body.board_id, body.target_slot),
        )
        conn.execute(
            "UPDATE slots SET role=? WHERE board_id=? AND slot_key=?",
            ("现运行", body.board_id, body.target_slot),
        )
        conn.execute(
            "UPDATE boards SET active_slot=? WHERE id=?",
            (body.target_slot, body.board_id),
        )
        conn.execute(
            "UPDATE boot_chain SET pending_slot=NULL, color=?, fail_streak=0, updated_at=? WHERE board_id=?",
            ("绿", ts, body.board_id),
        )
        conn.execute(
            "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
            ("切槽", f"board-{body.board_id}", f"切到 {body.target_slot}", ts),
        )
        return {"board_id": body.board_id, "active_slot": body.target_slot, "color": "绿"}


@router.post("/启动链/{board_id}/探针色")
def set_boot_color(board_id: int, body: BootColorBody):
    with db() as conn:
        row = conn.execute("SELECT * FROM boot_chain WHERE board_id=?", (board_id,)).fetchone()
        if not row:
            raise HTTPException(404, "启动链不存在")
        ts = now_iso()
        conn.execute(
            "UPDATE boot_chain SET color=?, fail_streak=?, updated_at=? WHERE board_id=?",
            (body.color, body.fail_streak, ts, board_id),
        )
        return dict(conn.execute("SELECT * FROM boot_chain WHERE board_id=?", (board_id,)).fetchone())

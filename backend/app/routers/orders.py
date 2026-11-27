from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import db
from app.services.common import now_iso

router = APIRouter(tags=["写闪单"])


class FlashBody(BaseModel):
    board_id: int
    target_slot: str = Field(pattern="^[AB]$")
    firmware_id: int


@router.get("/写闪单")
def list_orders():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT o.id, o.board_id, b.name AS board_name, o.target_slot, o.firmware_id,
                   f.version AS firmware_version, o.status, o.note, o.created_at
            FROM flash_orders o
            JOIN boards b ON b.id = o.board_id
            JOIN firmwares f ON f.id = o.firmware_id
            ORDER BY o.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/写闪单")
def create_order(body: FlashBody):
    with db() as conn:
        board = conn.execute("SELECT * FROM boards WHERE id=?", (body.board_id,)).fetchone()
        fw = conn.execute("SELECT * FROM firmwares WHERE id=?", (body.firmware_id,)).fetchone()
        slot = conn.execute(
            "SELECT * FROM slots WHERE board_id=? AND slot_key=?",
            (body.board_id, body.target_slot),
        ).fetchone()
        if not board or not fw or not slot:
            raise HTTPException(400, "板卡/固件/槽位不存在")
        # 底座空实现：直接记一张「写闪中」单，业务裁决留给功能题
        ts = now_iso()
        cur = conn.execute(
            """
            INSERT INTO flash_orders(board_id, target_slot, firmware_id, status, note, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (body.board_id, body.target_slot, body.firmware_id, "写闪中", "底座占位写闪", ts),
        )
        oid = cur.lastrowid
        conn.execute(
            "UPDATE slots SET write_state=?, firmware_id=? WHERE id=?",
            ("写闪中", body.firmware_id, slot["id"]),
        )
        conn.execute(
            "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
            ("写闪", f"order-{oid}", f"开写闪 {board['name']}/{body.target_slot}", ts),
        )
        row = conn.execute("SELECT * FROM flash_orders WHERE id=?", (oid,)).fetchone()
        return dict(row)


@router.post("/写闪单/{oid}/收口")
def close_order(oid: int):
    with db() as conn:
        o = conn.execute("SELECT * FROM flash_orders WHERE id=?", (oid,)).fetchone()
        if not o:
            raise HTTPException(404, "写闪单不存在")
        if o["status"] != "写闪中":
            return dict(o)
        ts = now_iso()
        conn.execute(
            "UPDATE flash_orders SET status=?, note=? WHERE id=?",
            ("已完成", "底座占位收口", oid),
        )
        conn.execute(
            "UPDATE slots SET write_state=? WHERE board_id=? AND slot_key=?",
            ("完好", o["board_id"], o["target_slot"]),
        )
        conn.execute(
            "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
            ("写闪收口", f"order-{oid}", "底座收口为已完成", ts),
        )
        return dict(conn.execute("SELECT * FROM flash_orders WHERE id=?", (oid,)).fetchone())

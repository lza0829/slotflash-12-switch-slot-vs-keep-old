from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import db
from app.services import promotion
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
        out = []
        for row in rows:
            item = dict(row)
            item["升格口径"] = promotion.policy_view()["策略"]
            item["未升账"] = promotion.pending_view(promotion.open_pending(conn, row["board_id"]))
            out.append(item)
        return out


@router.get("/启动链/升格口径")
def get_promotion_policy():
    return promotion.policy_view()


@router.get("/启动链/{board_id}/对读")
def read_board(board_id: int):
    with db() as conn:
        try:
            return promotion.readout(conn, board_id)
        except promotion.PromotionNotFound as exc:
            raise HTTPException(404, str(exc))


@router.post("/启动链/切槽")
def switch_slot(body: BootBody):
    with db() as conn:
        try:
            return promotion.switch(conn, body.board_id, body.target_slot)
        except promotion.PromotionNotFound as exc:
            raise HTTPException(400, str(exc))
        except promotion.PromotionConflict as exc:
            raise HTTPException(409, str(exc))


@router.post("/升格/{pending_id}/收口")
def promote_slot(pending_id: int):
    with db() as conn:
        try:
            return promotion.promote(conn, pending_id)
        except promotion.PromotionNotFound as exc:
            raise HTTPException(404, str(exc))
        except promotion.PromotionConflict as exc:
            raise HTTPException(409, str(exc))


@router.post("/升格/{pending_id}/撤账")
def revert_slot(pending_id: int):
    with db() as conn:
        try:
            return promotion.revert(conn, pending_id)
        except promotion.PromotionNotFound as exc:
            raise HTTPException(404, str(exc))
        except promotion.PromotionConflict as exc:
            raise HTTPException(409, str(exc))


@router.post("/启动链/{board_id}/探针色")
def set_boot_color(board_id: int, body: BootColorBody):
    with db() as conn:
        row = conn.execute("SELECT * FROM boot_chain WHERE board_id=?", (board_id,)).fetchone()
        if not row:
            raise HTTPException(404, "启动链不存在")
        ts = now_iso()
        # 探活只改启动色，不碰角色表、不收未升账：未升账不许被探活「洗白」。
        conn.execute(
            "UPDATE boot_chain SET color=?, fail_streak=?, updated_at=? WHERE board_id=?",
            (body.color, body.fail_streak, ts, board_id),
        )
        return dict(conn.execute("SELECT * FROM boot_chain WHERE board_id=?", (board_id,)).fetchone())

from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.db import db
from app.services.common import now_iso

router = APIRouter(tags=["回退拨"])


class PolicyBody(BaseModel):
    mode: str
    hold_sec: int = 20


@router.get("/回退拨")
def get_policy():
    with db() as conn:
        row = conn.execute("SELECT mode, hold_sec FROM rollback_policy WHERE id=1").fetchone()
        return dict(row)


@router.post("/回退拨")
def set_policy(body: PolicyBody):
    with db() as conn:
        conn.execute(
            "UPDATE rollback_policy SET mode=?, hold_sec=? WHERE id=1",
            (body.mode, body.hold_sec),
        )
        conn.execute(
            "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
            ("回退拨", "policy", f"模式={body.mode}", now_iso()),
        )
        return dict(conn.execute("SELECT mode, hold_sec FROM rollback_policy WHERE id=1").fetchone())

from __future__ import annotations
from fastapi import APIRouter
from app.db import db

router = APIRouter(tags=["板规"])


@router.get("/板规")
def get_settings():
    with db() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


@router.get("/事件")
def list_events():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, kind, ref, detail, at FROM events ORDER BY id DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]

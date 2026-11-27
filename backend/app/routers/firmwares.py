from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.db import db
from app.services.common import now_iso

router = APIRouter(tags=["固件仓"])


@router.get("/固件")
def list_firmwares():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, version, digest, verify_state, size_kb, ready_at FROM firmwares ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/固件/{fid}/推进校验")
def advance_verify(fid: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM firmwares WHERE id=?", (fid,)).fetchone()
        if not row:
            raise HTTPException(404, "固件不存在")
        state = row["verify_state"]
        if state == "已校验":
            return dict(row)
        if state == "校验中":
            conn.execute(
                "UPDATE firmwares SET verify_state=?, ready_at=? WHERE id=?",
                ("已校验", now_iso(), fid),
            )
        else:
            conn.execute(
                "UPDATE firmwares SET verify_state=? WHERE id=?",
                ("校验中", fid),
            )
        conn.execute(
            "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
            ("校验", f"fw-{fid}", f"推进校验 {state}->下一步", now_iso()),
        )
        out = conn.execute("SELECT * FROM firmwares WHERE id=?", (fid,)).fetchone()
        return dict(out)

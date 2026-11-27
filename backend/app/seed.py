from __future__ import annotations
from app.db import connect, init_schema
from app.services.common import now_iso


def seed_if_empty() -> None:
    conn = connect()
    init_schema(conn)
    n = conn.execute("SELECT COUNT(*) AS c FROM boards").fetchone()["c"]
    if n:
        conn.close()
        return
    ts = now_iso()
    conn.execute(
        "INSERT INTO firmwares(name, version, digest, verify_state, size_kb, ready_at) VALUES (?,?,?,?,?,?)",
        ("modem-core", "2.1.0", "sha256:a11c", "已校验", 4096, ts),
    )
    conn.execute(
        "INSERT INTO firmwares(name, version, digest, verify_state, size_kb, ready_at) VALUES (?,?,?,?,?,?)",
        ("modem-core", "2.2.0-rc1", "sha256:b22d", "校验中", 4200, None),
    )
    conn.execute(
        "INSERT INTO boards(name, active_slot, watchdog_sec) VALUES (?,?,?)",
        ("edge-01", "A", 30),
    )
    conn.execute(
        "INSERT INTO boards(name, active_slot, watchdog_sec) VALUES (?,?,?)",
        ("edge-02", "B", 45),
    )
    conn.execute(
        "INSERT INTO slots(board_id, slot_key, role, firmware_id, write_state, boot_color) VALUES (?,?,?,?,?,?)",
        (1, "A", "现运行", 1, "完好", "绿"),
    )
    conn.execute(
        "INSERT INTO slots(board_id, slot_key, role, firmware_id, write_state, boot_color) VALUES (?,?,?,?,?,?)",
        (1, "B", "空闲", None, "空", "灰"),
    )
    conn.execute(
        "INSERT INTO slots(board_id, slot_key, role, firmware_id, write_state, boot_color) VALUES (?,?,?,?,?,?)",
        (2, "A", "空闲", None, "空", "灰"),
    )
    conn.execute(
        "INSERT INTO slots(board_id, slot_key, role, firmware_id, write_state, boot_color) VALUES (?,?,?,?,?,?)",
        (2, "B", "现运行", 1, "完好", "绿"),
    )
    conn.execute(
        "INSERT INTO boot_chain(board_id, pending_slot, color, fail_streak, updated_at) VALUES (?,?,?,?,?)",
        (1, None, "绿", 0, ts),
    )
    conn.execute(
        "INSERT INTO boot_chain(board_id, pending_slot, color, fail_streak, updated_at) VALUES (?,?,?,?,?)",
        (2, None, "黄", 1, ts),
    )
    conn.execute(
        "INSERT INTO rollback_policy(id, mode, hold_sec) VALUES (1,?,?)",
        ("失败硬退", 20),
    )
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?,?)",
        ("verify_digest_required", "1"),
    )
    conn.execute(
        "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
        ("种子", "系统", "槽闪底座初始化", ts),
    )
    conn.commit()
    conn.close()

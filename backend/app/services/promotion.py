"""切槽升格口径：留旧未升账（全局唯一，不做运行时选型）。

两种可行架构（实现里只贯彻这一种，切槽回执旁不提供口径菜单）：

1. 升新即改：指针挪动与角色表改写同事务，新槽记现运行、旧槽降空闲。
2. 留旧未升账：指针可以先挪，角色表暂留旧槽现运行，同时显式开一条
   「未升账」；未升账必须可核，探活与写闪不得假装角色表已升。

本实现采用第 2 种。核心不变量：

- 切槽只动指针（boards.active_slot）并开/收未升账，不碰 slots.role；
  指针与账的写入在同一个事务里。
- 升格收口在同一事务内「先降旧槽、再升新槽、再收账」；
  slots(board_id) WHERE role='现运行' 上有部分唯一索引兜底，半截写不进。
- 撤账（显式撤账或切槽时指针跳回原槽）只收账并回指针，角色表不跟。
- 探活（启动色）与写闪单只动各自的表，不改角色表、不收未升账。
- 回执、现运行对读、未升账三路都由本模块在事务内从库里重算，
  不采信调用方传参，禁止各记各的。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.common import now_iso

POLICY_KEY = "留旧未升账"
POLICY_LABEL = "留旧未升账（指针先挪，显式升格）"
PROMOTE_IMMEDIATELY = False

STATUS_OPEN = "未升账"
STATUS_PROMOTED = "已升格"
STATUS_REVERTED = "已撤账"

# 测试注入点：模拟「半截升格」。生产路径始终为 None。
# 取值 "降位后" / "升格后"，由夹具在事务中途抛错，验证整单回滚。
FAILPOINT: str | None = None


class PromotionConflict(Exception):
    """当前状态不允许该操作（指针离位、账已收口等）。"""


class PromotionNotFound(Exception):
    """板卡 / 槽位 / 未升账不存在。"""


def _fail(step: str) -> None:
    if FAILPOINT == step:
        raise RuntimeError(f"注入故障：{step}")


def policy_view() -> dict[str, Any]:
    return {
        "策略": POLICY_KEY,
        "说明": POLICY_LABEL,
        "切槽即升格": PROMOTE_IMMEDIATELY,
        "升格时机": "显式收口",
    }


def pending_view(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "原槽": row["from_slot"],
        "目标槽": row["to_slot"],
        "状态": row["status"],
        "开账时间": row["opened_at"],
        "收账时间": row["closed_at"],
        "备注": row["note"],
    }


def open_pending(conn: sqlite3.Connection, board_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM pending_promotions WHERE board_id=? AND status=?",
        (board_id, STATUS_OPEN),
    ).fetchone()


def _role_slots(conn: sqlite3.Connection, board_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT slot_key FROM slots WHERE board_id=? AND role='现运行' ORDER BY slot_key",
        (board_id,),
    ).fetchall()
    return [r["slot_key"] for r in rows]


def _boot_row(conn: sqlite3.Connection, board_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT color, pending_slot, fail_streak FROM boot_chain WHERE board_id=?",
        (board_id,),
    ).fetchone()


def _set_boot(conn: sqlite3.Connection, board_id: int, pending_slot: str | None, color: str, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO boot_chain(board_id, pending_slot, color, fail_streak, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(board_id) DO UPDATE SET
          pending_slot=excluded.pending_slot,
          color=excluded.color,
          fail_streak=excluded.fail_streak,
          updated_at=excluded.updated_at
        """,
        (board_id, pending_slot, color, 0, ts),
    )


def _slot_boot_color(conn: sqlite3.Connection, board_id: int, slot_key: str) -> str:
    row = conn.execute(
        "SELECT boot_color FROM slots WHERE board_id=? AND slot_key=?",
        (board_id, slot_key),
    ).fetchone()
    return row["boot_color"] if row else "黄"


def _event(conn: sqlite3.Connection, kind: str, board_id: int, detail: str, ts: str) -> None:
    conn.execute(
        "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
        (kind, f"board-{board_id}", detail, ts),
    )


def readout(conn: sqlite3.Connection, board_id: int) -> dict[str, Any]:
    """现运行对读：指针、角色表、未升账三路在同一读里对齐。

    对读取值：
    - 一致：指针槽 == 角色现运行槽，且没有未升账；
    - 未升账：指针已到新槽，角色表仍留旧槽，未升账正挂着且能对上；
    - 不一致：指针与角色表对不上但账也没挂上（不允许出现的脏态）；
    - 角色表异常：一块板上不是恰好一格现运行（唯一索引兜底前的旧库）。
    """
    board = conn.execute("SELECT * FROM boards WHERE id=?", (board_id,)).fetchone()
    if board is None:
        raise PromotionNotFound("板卡不存在")
    roles = _role_slots(conn, board_id)
    pending = open_pending(conn, board_id)
    pointer = board["active_slot"]
    role_slot = roles[0] if len(roles) == 1 else None

    if len(roles) != 1:
        verdict = "角色表异常"
    elif pending is not None:
        if pending["to_slot"] == pointer and pending["from_slot"] == role_slot:
            verdict = "未升账"
        else:
            verdict = "不一致"
    elif role_slot == pointer:
        verdict = "一致"
    else:
        verdict = "不一致"

    boot = _boot_row(conn, board_id)
    return {
        **policy_view(),
        "board_id": board_id,
        "board_name": board["name"],
        "指针槽": pointer,
        "角色现运行槽": role_slot,
        "现运行对读": verdict,
        "未升账": pending_view(pending),
        "启动链": dict(boot) if boot is not None else None,
    }


def _board_and_slot(conn: sqlite3.Connection, board_id: int, target_slot: str) -> tuple[sqlite3.Row, sqlite3.Row]:
    board = conn.execute("SELECT * FROM boards WHERE id=?", (board_id,)).fetchone()
    if board is None:
        raise PromotionNotFound("板卡不存在")
    slot = conn.execute(
        "SELECT * FROM slots WHERE board_id=? AND slot_key=?",
        (board_id, target_slot),
    ).fetchone()
    if slot is None:
        raise PromotionNotFound("槽位不存在")
    return board, slot


def switch(conn: sqlite3.Connection, board_id: int, target_slot: str) -> dict[str, Any]:
    """切槽：只挪指针 + 开/收未升账，角色表不动。整段在调用方事务内。"""
    board, _ = _board_and_slot(conn, board_id, target_slot)
    pointer = board["active_slot"]
    pending = open_pending(conn, board_id)
    roles = _role_slots(conn, board_id)
    if len(roles) != 1:
        # 角色表本身脏（多格/零格现运行）：先对读报错，不许在脏地基上继续切。
        raise PromotionConflict("角色表现运行不唯一，拒绝切槽")
    ts = now_iso()
    changed = False

    if target_slot == pointer:
        # 幂等：已在目标槽，不新开账、不动角色表；已有账原样返回。
        if pending is not None and pending["to_slot"] != pointer:
            raise PromotionConflict("未升账与指针不符，拒绝切槽")
    elif pending is not None:
        if pending["to_slot"] != pointer:
            raise PromotionConflict("未升账与指针不符，拒绝切槽")
        if target_slot != pending["from_slot"]:
            raise PromotionConflict("已有未升账未收口，不能切去第三个槽")
        # 指针跳回原槽：撤账，角色表不跟（旧槽本就仍是现运行）。
        conn.execute(
            "UPDATE pending_promotions SET status=?, closed_at=?, note=? WHERE id=?",
            (STATUS_REVERTED, ts, "切槽使指针跳回原槽，撤账", pending["id"]),
        )
        conn.execute("UPDATE boards SET active_slot=? WHERE id=?", (target_slot, board_id))
        _set_boot(conn, board_id, None, _slot_boot_color(conn, board_id, target_slot), ts)
        _event(conn, "切槽回撤", board_id, f"指针 {pointer}->{target_slot}，撤未升账 #{pending['id']}", ts)
        changed = True
    else:
        # 指针先挪，显式挂未升账；角色表暂留旧槽。
        cur = conn.execute(
            """
            INSERT INTO pending_promotions(board_id, from_slot, to_slot, status, opened_at, note)
            VALUES (?,?,?,?,?,?)
            """,
            (board_id, pointer, target_slot, STATUS_OPEN, ts, "切槽先挪指针，角色表暂留"),
        )
        conn.execute("UPDATE boards SET active_slot=? WHERE id=?", (target_slot, board_id))
        # 未探活前不得报绿：在途槽挂黄。
        _set_boot(conn, board_id, target_slot, "黄", ts)
        _event(conn, "切槽", board_id, f"指针 {pointer}->{target_slot}，开未升账 #{cur.lastrowid}", ts)
        changed = True

    out = readout(conn, board_id)
    out["changed"] = changed
    out["target_slot"] = target_slot
    return out


def promote(conn: sqlite3.Connection, pending_id: int) -> dict[str, Any]:
    """显式升格：同事务内先降旧、再升新、再收账；半截失败整单回滚。"""
    row = conn.execute("SELECT * FROM pending_promotions WHERE id=?", (pending_id,)).fetchone()
    if row is None:
        raise PromotionNotFound("未升账不存在")
    if row["status"] != STATUS_OPEN:
        raise PromotionConflict(f"未升账已收口（{row['status']}），不能重复升格")
    board = conn.execute("SELECT * FROM boards WHERE id=?", (row["board_id"],)).fetchone()
    if board is None:
        raise PromotionNotFound("板卡不存在")
    if board["active_slot"] != row["to_slot"]:
        raise PromotionConflict("指针不在目标槽，拒绝升格")
    roles = _role_slots(conn, row["board_id"])
    if len(roles) != 1:
        raise PromotionConflict("角色表现运行不唯一，拒绝升格")

    ts = now_iso()
    # 先降旧槽，避免部分唯一索引在提交前看到双现运行。
    conn.execute(
        "UPDATE slots SET role='空闲' WHERE board_id=? AND role='现运行' AND slot_key<>?",
        (row["board_id"], row["to_slot"]),
    )
    _fail("降位后")
    conn.execute(
        "UPDATE slots SET role='现运行' WHERE board_id=? AND slot_key=?",
        (row["board_id"], row["to_slot"]),
    )
    roles = _role_slots(conn, row["board_id"])
    if roles != [row["to_slot"]]:
        raise RuntimeError(f"升格后角色表不唯一：{roles}")
    _fail("升格后")
    conn.execute(
        "UPDATE pending_promotions SET status=?, closed_at=?, note=? WHERE id=?",
        (STATUS_PROMOTED, ts, "显式升格收口", pending_id),
    )
    _set_boot(conn, row["board_id"], None, "绿", ts)
    _event(
        conn,
        "升格",
        row["board_id"],
        f"未升账 #{pending_id} 收口：{row['from_slot']} 降空闲，{row['to_slot']} 升现运行",
        ts,
    )
    out = readout(conn, row["board_id"])
    out["changed"] = True
    return out


def revert(conn: sqlite3.Connection, pending_id: int) -> dict[str, Any]:
    """显式撤账：指针回到原槽并收账；角色表不跟（旧槽仍现运行）。"""
    row = conn.execute("SELECT * FROM pending_promotions WHERE id=?", (pending_id,)).fetchone()
    if row is None:
        raise PromotionNotFound("未升账不存在")
    if row["status"] != STATUS_OPEN:
        raise PromotionConflict(f"未升账已收口（{row['status']}），不能重复撤账")
    board = conn.execute("SELECT * FROM boards WHERE id=?", (row["board_id"],)).fetchone()
    if board is None:
        raise PromotionNotFound("板卡不存在")
    if board["active_slot"] != row["to_slot"]:
        raise PromotionConflict("指针不在目标槽，拒绝撤账")
    roles = _role_slots(conn, row["board_id"])
    if len(roles) != 1:
        raise PromotionConflict("角色表现运行不唯一，拒绝撤账")

    ts = now_iso()
    conn.execute("UPDATE boards SET active_slot=? WHERE id=?", (row["from_slot"], row["board_id"]))
    _set_boot(conn, row["board_id"], None, _slot_boot_color(conn, row["board_id"], row["from_slot"]), ts)
    conn.execute(
        "UPDATE pending_promotions SET status=?, closed_at=?, note=? WHERE id=?",
        (STATUS_REVERTED, ts, "显式撤账，指针回原槽", pending_id),
    )
    _event(
        conn,
        "撤账",
        row["board_id"],
        f"未升账 #{pending_id} 撤账：指针回到 {row['from_slot']}，角色表不动",
        ts,
    )
    out = readout(conn, row["board_id"])
    out["changed"] = True
    return out

"""切槽升格夹具：压住「留旧未升账」口径的每一条硬要求。"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(monkeypatch):
    tmpdir = tempfile.mkdtemp(prefix="slotflash-test-")
    db_path = Path(tmpdir) / "t.db"
    monkeypatch.setenv("SLOTFLASH_DB", str(db_path))

    import importlib

    import app.config
    import app.db
    import app.seed
    import app.main
    import app.services.promotion as promo

    importlib.reload(app.config)
    importlib.reload(app.db)
    importlib.reload(app.seed)
    importlib.reload(promo)
    importlib.reload(app.main)

    promo.FAILPOINT = None
    from fastapi.testclient import TestClient

    with TestClient(app.main.app, raise_server_exceptions=False) as c:
        c.promo = promo
        yield c


def _readout(c, board_id=1):
    r = c.get(f"/api/启动链/{board_id}/对读")
    assert r.status_code == 200, r.text
    return r.json()


def _switch(c, board_id, slot):
    return c.post("/api/启动链/切槽", json={"board_id": board_id, "target_slot": slot})


def _slots(c, board_id=1):
    rows = c.get("/api/闪槽").json()
    return {r["slot_key"]: r for r in rows if r["board_id"] == board_id}


def test_policy_is_single_and_not_a_menu(client):
    p = client.get("/api/启动链/升格口径").json()
    assert p["策略"] == "留旧未升账"
    assert p["切槽即升格"] is False
    # 切槽回执不自带选型口径，只回「当前钉死的这一种」。
    r = _switch(client, 1, "B").json()
    assert r["策略"] == "留旧未升账"
    assert "候选口径" not in r and "口径菜单" not in r
    assert not any("候选" in str(v) or "可选" in str(v) for v in r.values())


def test_switch_moves_pointer_opens_pending_and_keeps_roles(client):
    r = _switch(client, 1, "B")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["指针槽"] == "B"
    assert body["角色现运行槽"] == "A"  # 旧槽角色不跟
    assert body["现运行对读"] == "未升账"
    assert body["未升账"]["原槽"] == "A"
    assert body["未升账"]["目标槽"] == "B"
    assert body["启动链"]["pending_slot"] == "B"
    assert body["启动链"]["color"] == "黄"  # 未探活不报绿
    slots = _slots(client)
    assert slots["A"]["role"] == "现运行"
    assert slots["B"]["role"] == "空闲"


def test_switch_idempotent_does_not_reopen_pending(client):
    first = _switch(client, 1, "B").json()
    second = _switch(client, 1, "B").json()
    assert second["changed"] is False
    assert second["未升账"]["id"] == first["未升账"]["id"]


def test_promote_moves_role_and_closes_pending_atomically(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    r = client.post(f"/api/升格/{pid}/收口")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["指针槽"] == "B"
    assert body["角色现运行槽"] == "B"
    assert body["现运行对读"] == "一致"
    assert body["未升账"] is None
    assert body["启动链"]["color"] == "绿"
    assert body["启动链"]["pending_slot"] is None
    slots = _slots(client)
    assert slots["B"]["role"] == "现运行"
    assert slots["A"]["role"] == "空闲"


def test_half_promotion_rolls_back_both_writes(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    client.promo.FAILPOINT = "降位后"
    r = client.post(f"/api/升格/{pid}/收口")
    assert r.status_code == 500
    client.promo.FAILPOINT = None

    body = _readout(client)
    # 旧槽仍是现运行，新槽仍空闲，未升账仍挂着：没有留下双现运行，也没有半截升格。
    assert body["角色现运行槽"] == "A"
    assert body["现运行对读"] == "未升账"
    assert body["未升账"]["状态"] == "未升账"
    slots = _slots(client)
    assert slots["A"]["role"] == "现运行"
    assert slots["B"]["role"] == "空闲"
    assert sum(1 for s in slots.values() if s["role"] == "现运行") == 1


def test_half_promotion_after_raise_also_rolls_back(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    client.promo.FAILPOINT = "升格后"
    r = client.post(f"/api/升格/{pid}/收口")
    assert r.status_code == 500
    client.promo.FAILPOINT = None
    slots = _slots(client)
    assert slots["A"]["role"] == "现运行"
    assert slots["B"]["role"] == "空闲"
    assert _readout(client)["未升账"]["状态"] == "未升账"


def test_switch_interleaved_with_red_keeps_pending_and_does_not_fake_green(client):
    _switch(client, 1, "B")
    client.post("/api/启动链/1/探针色", json={"color": "红", "fail_streak": 3})
    body = _readout(client)
    # 打红只动启动色，不收未升账、不改角色表。
    assert body["启动链"]["color"] == "红"
    assert body["未升账"]["状态"] == "未升账"
    assert body["现运行对读"] == "未升账"
    assert _slots(client)["A"]["role"] == "现运行"


def test_probe_green_does_not_promote(client):
    _switch(client, 1, "B")
    client.post("/api/启动链/1/探针色", json={"color": "绿", "fail_streak": 0})
    body = _readout(client)
    assert body["现运行对读"] == "未升账"
    assert body["未升账"]["状态"] == "未升账"
    assert _slots(client)["B"]["role"] == "空闲"


def test_pending_closed_before_pointer_moves_back(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    client.post(f"/api/升格/{pid}/收口")
    # 升格后再把指针切回 A：开一条新的未升账，旧槽 A 此刻是空闲，角色表不动。
    body = _switch(client, 1, "A").json()
    assert body["指针槽"] == "A"
    assert body["角色现运行槽"] == "B"
    assert body["现运行对读"] == "未升账"
    assert body["未升账"]["原槽"] == "B"


def test_pointer_jump_back_reverts_pending_and_roles_do_not_follow(client):
    _switch(client, 1, "B")
    body = _switch(client, 1, "A").json()
    assert body["指针槽"] == "A"
    assert body["角色现运行槽"] == "A"
    assert body["现运行对读"] == "一致"
    assert body["未升账"] is None
    slots = _slots(client)
    assert slots["A"]["role"] == "现运行"
    assert slots["B"]["role"] == "空闲"
    # 撤掉的是账，不是角色：历史可核。
    events = client.get("/api/事件").json()
    assert any(e["kind"] == "切槽回撤" for e in events)


def test_explicit_revert_closes_pending_and_moves_pointer_back(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    body = client.post(f"/api/升格/{pid}/撤账").json()
    assert body["指针槽"] == "A"
    assert body["角色现运行槽"] == "A"
    assert body["现运行对读"] == "一致"
    assert body["未升账"] is None
    assert _slots(client)["A"]["role"] == "现运行"


def test_cannot_promote_when_pointer_not_on_target(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    # 模拟指针被别处挪走（例如运维手改库）：升格必须拒绝，不允许暗中升格。
    from app.db import connect

    conn = connect()
    try:
        conn.execute("UPDATE boards SET active_slot='A' WHERE id=1")
        conn.commit()
    finally:
        conn.close()
    r = client.post(f"/api/升格/{pid}/收口")
    assert r.status_code == 409
    # 指针离位的账依然可核，且没有被升格改写。
    body = _readout(client)
    assert body["未升账"]["状态"] == "未升账"
    assert body["现运行对读"] == "不一致"


def test_readout_flags_double_active_dirty_state(client):
    from app.db import connect

    conn = connect()
    try:
        # 拆掉兜底索引后人为制造双现运行：对读必须显式报「角色表异常」，不装没事。
        conn.execute("DROP INDEX IF EXISTS ux_slots_one_active")
        conn.execute("UPDATE slots SET role='现运行' WHERE board_id=1 AND slot_key='B'")
        conn.commit()
    finally:
        conn.close()
    body = _readout(client)
    assert body["角色现运行槽"] is None
    assert body["现运行对读"] == "角色表异常"
    # 脏地基上不许再切槽，把脏态沿下去。
    assert _switch(client, 1, "A").status_code == 409



def test_promote_twice_conflicts(client):
    pid = _switch(client, 1, "B").json()["未升账"]["id"]
    assert client.post(f"/api/升格/{pid}/收口").status_code == 200
    assert client.post(f"/api/升格/{pid}/收口").status_code == 409


def test_unique_index_blocks_double_active_even_if_code_misbehaves(client):
    from app.db import connect

    conn = connect()
    try:
        # A 已是现运行，任何把 B 也写成现运行的尝试都必须撞唯一索引。
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE slots SET role='现运行' WHERE board_id=1 AND slot_key='B'")
        conn.rollback()
    finally:
        conn.close()


def test_receipt_readout_and_pending_agree(client):
    body = _switch(client, 1, "B").json()
    fresh = _readout(client)
    # 回执与之后的对读同源：三路不得各记各的。
    for key in ("指针槽", "角色现运行槽", "现运行对读", "未升账"):
        assert body[key] == fresh[key]
    pending_id = body["未升账"]["id"]
    promoted = client.post(f"/api/升格/{pending_id}/收口").json()
    fresh2 = _readout(client)
    for key in ("指针槽", "角色现运行槽", "现运行对读", "未升账"):
        assert promoted[key] == fresh2[key]
    assert fresh2["现运行对读"] == "一致"


def test_align_screen_exposes_readout_per_board(client):
    _switch(client, 1, "B")
    data = client.get("/api/校验").json()
    assert data["升格口径"]["策略"] == "留旧未升账"
    by_board = {r["board_id"]: r for r in data["现运行对读"]}
    assert by_board[1]["现运行对读"] == "未升账"
    assert by_board[1]["未升账"]["目标槽"] == "B"
    assert by_board[2]["现运行对读"] == "一致"


def test_boot_list_carries_pending(client):
    _switch(client, 1, "B")
    rows = client.get("/api/启动链").json()
    row = next(r for r in rows if r["board_id"] == 1)
    assert row["未升账"]["目标槽"] == "B"
    assert row["升格口径"] == "留旧未升账"


def test_cannot_switch_to_third_slot_while_pending_open(client):
    _switch(client, 1, "B")
    # 只有 A/B 两槽，指针在 B、账 A→B 挂着；再切 A 是撤账路径，不算第三个槽。
    assert _switch(client, 1, "A").status_code == 200
    # 撤账后重新开账去 B，账仍只有一条。
    body = _switch(client, 1, "B").json()
    assert body["未升账"]["原槽"] == "A"


def test_write_flash_does_not_fake_roles_or_clear_pending(client):
    _switch(client, 1, "B")
    before = _slots(client)
    order = client.post("/api/写闪单", json={"board_id": 1, "target_slot": "B", "firmware_id": 1}).json()
    after = _slots(client)
    assert after["A"]["role"] == before["A"]["role"] == "现运行"
    assert after["B"]["role"] == before["B"]["role"] == "空闲"
    assert _readout(client)["未升账"]["状态"] == "未升账"
    client.post(f"/api/写闪单/{order['id']}/收口")
    assert _slots(client)["A"]["role"] == "现运行"
    assert _readout(client)["未升账"]["状态"] == "未升账"


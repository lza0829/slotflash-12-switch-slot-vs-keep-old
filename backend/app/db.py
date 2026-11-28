from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH
from app.services.common import now_iso


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS firmwares (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          version TEXT NOT NULL,
          digest TEXT NOT NULL,
          verify_state TEXT NOT NULL,
          size_kb INTEGER NOT NULL DEFAULT 0,
          ready_at TEXT
        );
        CREATE TABLE IF NOT EXISTS boards (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          active_slot TEXT NOT NULL,
          watchdog_sec INTEGER NOT NULL DEFAULT 30
        );
        CREATE TABLE IF NOT EXISTS slots (
          id INTEGER PRIMARY KEY,
          board_id INTEGER NOT NULL,
          slot_key TEXT NOT NULL,
          role TEXT NOT NULL,
          firmware_id INTEGER,
          write_state TEXT NOT NULL,
          boot_color TEXT NOT NULL DEFAULT '灰',
          FOREIGN KEY(board_id) REFERENCES boards(id),
          FOREIGN KEY(firmware_id) REFERENCES firmwares(id),
          UNIQUE(board_id, slot_key)
        );
        CREATE TABLE IF NOT EXISTS flash_orders (
          id INTEGER PRIMARY KEY,
          board_id INTEGER NOT NULL,
          target_slot TEXT NOT NULL,
          firmware_id INTEGER NOT NULL,
          status TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(board_id) REFERENCES boards(id),
          FOREIGN KEY(firmware_id) REFERENCES firmwares(id)
        );
        CREATE TABLE IF NOT EXISTS boot_chain (
          id INTEGER PRIMARY KEY,
          board_id INTEGER NOT NULL UNIQUE,
          pending_slot TEXT,
          color TEXT NOT NULL,
          fail_streak INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT,
          FOREIGN KEY(board_id) REFERENCES boards(id)
        );
        CREATE TABLE IF NOT EXISTS rollback_policy (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          mode TEXT NOT NULL,
          hold_sec INTEGER NOT NULL DEFAULT 20
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY,
          kind TEXT NOT NULL,
          ref TEXT,
          detail TEXT NOT NULL,
          at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pending_promotions (
          id INTEGER PRIMARY KEY,
          board_id INTEGER NOT NULL,
          from_slot TEXT NOT NULL,
          to_slot TEXT NOT NULL,
          status TEXT NOT NULL,
          opened_at TEXT NOT NULL,
          closed_at TEXT,
          note TEXT,
          FOREIGN KEY(board_id) REFERENCES boards(id)
        );
        """
    )
    # 两条唯一索引是硬兜底：一块板最多一格现运行、最多一条未升账。
    # 旧库若已带脏数据，建约束会失败：记一条事件后照常启动，
    # 由对读把「角色表异常」显式报出来，不静默吞掉。
    for ddl, detail in (
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_slots_one_active ON slots(board_id) WHERE role='现运行'",
            "存在多格现运行，唯一约束未建立",
        ),
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_pending_one_open ON pending_promotions(board_id) WHERE status='未升账'",
            "存在多条未升账，唯一约束未建立",
        ),
    ):
        try:
            conn.execute(ddl)
        except sqlite3.IntegrityError:
            conn.execute(
                "INSERT INTO events(kind, ref, detail, at) VALUES (?,?,?,?)",
                ("角色表脏数据", "schema", detail, now_iso()),
            )
    conn.commit()

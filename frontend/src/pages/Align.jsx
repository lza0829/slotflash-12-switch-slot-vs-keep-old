import React, { useEffect, useState } from "react";
import { api } from "../api";

function lamp(role, color) {
  const cls = role === "现运行" ? "run" : color === "绿" ? "ok" : color === "红" ? "bad" : "";
  return (
    <span className={`slot-lamp ${cls}`}>
      <i />
      {role}/{color}
    </span>
  );
}

function bootLamp(color) {
  const cls = color === "绿" ? "ok" : color === "红" ? "bad" : color === "黄" ? "run" : "";
  return (
    <span className={`slot-lamp ${cls}`}>
      <i />
      {color}
    </span>
  );
}

export default function Align() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.align().then(setData);
  }, []);
  if (!data) return <p className="muted">加载中…</p>;

  const slots = data.闪槽投影 || [];
  const boots = data.启动链投影 || [];
  const orders = data.写闪近单 || [];
  const policy = data.回退拨 || {};

  return (
    <div className="stack">
      <section className="panel">
        <h1>校验屏</h1>
        <p className="muted">把闪槽角色、启动链色、近单状态拉到同一屏对读。</p>
        <p className="mono">
          回退拨：{policy.mode || "—"} / {policy.hold_sec ?? "—"}s
        </p>
      </section>

      <section className="panel">
        <h2>闪槽投影</h2>
        <table className="table">
          <thead>
            <tr>
              <th>板卡</th>
              <th>槽</th>
              <th>角色灯</th>
              <th>写态</th>
              <th>板现运行</th>
            </tr>
          </thead>
          <tbody>
            {slots.map((r) => (
              <tr key={`${r.board_id}-${r.slot_key}`}>
                <td>{r.board_name}</td>
                <td>{r.slot_key}</td>
                <td>{lamp(r.role, r.boot_color)}</td>
                <td>{r.write_state}</td>
                <td className="cyan">{r.active_slot}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>启动链投影</h2>
        <table className="table">
          <thead>
            <tr>
              <th>板卡</th>
              <th>启动色</th>
              <th>连败</th>
              <th>在途槽</th>
            </tr>
          </thead>
          <tbody>
            {boots.map((r) => (
              <tr key={r.board_id}>
                <td>#{r.board_id}</td>
                <td>{bootLamp(r.color)}</td>
                <td>{r.fail_streak}</td>
                <td>{r.pending_slot || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>写闪近单</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>板卡</th>
              <th>目标槽</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={4} className="muted">
                  暂无近单
                </td>
              </tr>
            ) : (
              orders.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>#{r.board_id}</td>
                  <td>{r.target_slot}</td>
                  <td>{r.status}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

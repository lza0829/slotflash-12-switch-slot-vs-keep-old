import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Slots() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.slots().then(setRows);
  }, []);

  const lamp = (role, color) => {
    const cls = role === "现运行" ? "run" : color === "绿" ? "ok" : color === "红" ? "bad" : "";
    return (
      <span className={`slot-lamp ${cls}`}>
        <i />
        {role}/{color}
      </span>
    );
  };

  return (
    <section className="panel">
      <h1>闪槽</h1>
      <p className="muted">每块板 A/B 双槽。现运行槽与空闲槽角色要能一眼分清。</p>
      <table className="table">
        <thead>
          <tr>
            <th>板卡</th>
            <th>槽</th>
            <th>角色灯</th>
            <th>固件</th>
            <th>写态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.board_name}</td>
              <td>{r.slot_key}</td>
              <td>{lamp(r.role, r.boot_color)}</td>
              <td>{r.firmware_version || "—"}</td>
              <td>{r.write_state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

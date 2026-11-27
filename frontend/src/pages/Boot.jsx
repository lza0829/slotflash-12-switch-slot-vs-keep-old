import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Boot() {
  const [rows, setRows] = useState([]);
  const load = () => api.boot().then(setRows);
  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <h1>启动链</h1>
      <p className="muted">切槽启动后看现运行槽与启动色。底座占位可直接切。</p>
      <table className="table">
        <thead>
          <tr>
            <th>板卡</th>
            <th>现运行</th>
            <th>在途槽</th>
            <th>启动色</th>
            <th>连败</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.board_id}>
              <td>{r.board_name}</td>
              <td className="cyan">{r.active_slot}</td>
              <td>{r.pending_slot || "—"}</td>
              <td>{r.color}</td>
              <td>{r.fail_streak}</td>
              <td className="row">
                <button
                  className="btn"
                  onClick={() => api.switchSlot({ board_id: r.board_id, target_slot: "A" }).then(load)}
                >
                  切 A
                </button>
                <button
                  className="btn"
                  onClick={() => api.switchSlot({ board_id: r.board_id, target_slot: "B" }).then(load)}
                >
                  切 B
                </button>
                <button
                  className="btn danger"
                  onClick={() =>
                    api.setBootColor(r.board_id, { color: "红", fail_streak: r.fail_streak + 1 }).then(load)
                  }
                >
                  打红
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

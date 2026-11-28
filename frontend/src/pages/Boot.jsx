import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Boot() {
  const [rows, setRows] = useState([]);
  const [policy, setPolicy] = useState(null);
  const load = () => {
    api.boot().then(setRows);
    api.promotionPolicy().then(setPolicy);
  };
  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <h1>启动链</h1>
      <p className="muted">
        切槽只挪指针并挂「未升账」，角色表暂留旧槽；升格或撤账必须显式收口。
        {policy && (
          <>
            {" "}
            当前口径：<span className="cyan mono">{policy.策略}</span>
          </>
        )}
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>板卡</th>
            <th>指针槽</th>
            <th>在途槽</th>
            <th>启动色</th>
            <th>连败</th>
            <th>未升账</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const pending = r.未升账;
            return (
              <tr key={r.board_id}>
                <td>{r.board_name}</td>
                <td className="cyan">{r.active_slot}</td>
                <td>{r.pending_slot || "—"}</td>
                <td>{r.color}</td>
                <td>{r.fail_streak}</td>
                <td>
                  {pending ? (
                    <span className="mono coral">
                      #{pending.id} {pending.原槽}→{pending.目标槽}
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
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
                  {pending && (
                    <button className="btn" onClick={() => api.promoteSlot(pending.id).then(load)}>
                      升格收口
                    </button>
                  )}
                  {pending && (
                    <button className="btn" onClick={() => api.revertPromotion(pending.id).then(load)}>
                      撤账
                    </button>
                  )}
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
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Firmwares() {
  const [rows, setRows] = useState([]);
  const load = () => api.firmwares().then(setRows);
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="stack">
      <div className="hero-strip">
        <section className="panel">
          <h1>固件仓</h1>
          <p className="muted">登记待刷包、摘要与校验态。未校验的包不应贸然入空闲槽。</p>
        </section>
        <section className="panel">
          <h2 className="cyan">0-1 冒烟</h2>
          <p className="mono muted">推进校验 → 开写闪单 → 切槽启动 → 校验屏对读</p>
        </section>
      </div>
      <section className="panel">
        <h2>包列表</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>版本</th>
              <th>摘要</th>
              <th>校验</th>
              <th>体积</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.name}</td>
                <td>{r.version}</td>
                <td>{r.digest}</td>
                <td className={r.verify_state === "已校验" ? "cyan" : "coral"}>{r.verify_state}</td>
                <td>{r.size_kb} KB</td>
                <td>
                  <button className="btn" onClick={() => api.advanceVerify(r.id).then(load)}>
                    推进校验
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

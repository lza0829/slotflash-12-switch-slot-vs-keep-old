import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Policy() {
  const [mode, setMode] = useState("失败硬退");
  const [hold, setHold] = useState(20);
  const load = () =>
    api.policy().then((p) => {
      setMode(p.mode);
      setHold(p.hold_sec);
    });
  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <h1>回退拨</h1>
      <p className="muted">写闪或切槽失败时，硬退回旧槽还是挂可核缺口，由拨杆口径决定（功能题再钉死）。</p>
      <div className="row">
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="失败硬退">失败硬退</option>
          <option value="挂缺口可核">挂缺口可核</option>
        </select>
        <input type="number" value={hold} onChange={(e) => setHold(Number(e.target.value))} />
        <span className="muted mono">hold_sec</span>
        <button className="btn" onClick={() => api.setPolicy({ mode, hold_sec: hold }).then(load)}>
          保存拨杆
        </button>
      </div>
    </section>
  );
}

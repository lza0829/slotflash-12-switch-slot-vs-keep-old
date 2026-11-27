import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Rules() {
  const [settings, setSettings] = useState({});
  const [events, setEvents] = useState([]);
  useEffect(() => {
    api.settings().then(setSettings);
    api.events().then(setEvents);
  }, []);

  const rows = Object.entries(settings || {});

  return (
    <div className="stack">
      <section className="panel">
        <h1>板规</h1>
        <p className="muted">全局默认、校验门槛与超时口径，供写闪与启动链旁读。</p>
        <table className="table">
          <thead>
            <tr>
              <th>项</th>
              <th>值</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={2} className="muted">
                  暂无板规
                </td>
              </tr>
            ) : (
              rows.map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td className="mono">{String(v)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>事件</h2>
        <table className="table">
          <thead>
            <tr>
              <th>时</th>
              <th>类</th>
              <th>引用</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.at}</td>
                <td>{e.kind}</td>
                <td>{e.ref}</td>
                <td>{e.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

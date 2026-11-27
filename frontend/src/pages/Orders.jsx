import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Orders() {
  const [rows, setRows] = useState([]);
  const [boards, setBoards] = useState([]);
  const [fws, setFws] = useState([]);
  const [boardId, setBoardId] = useState(1);
  const [slot, setSlot] = useState("B");
  const [fwId, setFwId] = useState(1);

  const load = () => {
    api.orders().then(setRows);
    api.boards().then((b) => {
      setBoards(b);
      if (b[0]) setBoardId(b[0].id);
    });
    api.firmwares().then((f) => {
      setFws(f);
      if (f[0]) setFwId(f[0].id);
    });
  };
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="stack">
      <section className="panel">
        <h1>写闪单</h1>
        <p className="muted">指定板卡、目标槽与固件包，开一张写闪事务。</p>
        <div className="row">
          <select value={boardId} onChange={(e) => setBoardId(Number(e.target.value))}>
            {boards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <select value={slot} onChange={(e) => setSlot(e.target.value)}>
            <option value="A">槽 A</option>
            <option value="B">槽 B</option>
          </select>
          <select value={fwId} onChange={(e) => setFwId(Number(e.target.value))}>
            {fws.map((f) => (
              <option key={f.id} value={f.id}>
                {f.version}
              </option>
            ))}
          </select>
          <button
            className="btn"
            onClick={() =>
              api.createOrder({ board_id: boardId, target_slot: slot, firmware_id: fwId }).then(load)
            }
          >
            开写闪
          </button>
        </div>
      </section>
      <section className="panel">
        <h2>单据</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>板卡</th>
              <th>目标槽</th>
              <th>固件</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.board_name}</td>
                <td>{r.target_slot}</td>
                <td>{r.firmware_version}</td>
                <td>{r.status}</td>
                <td>
                  {r.status === "写闪中" && (
                    <button className="btn" onClick={() => api.closeOrder(r.id).then(load)}>
                      收口
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

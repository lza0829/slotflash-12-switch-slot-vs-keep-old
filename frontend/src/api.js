const j = async (url, opt) => {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opt,
  });
  return r.json();
};

export const api = {
  health: () => j("/api/健康"),
  firmwares: () => j("/api/固件"),
  advanceVerify: (id) => j(`/api/固件/${id}/推进校验`, { method: "POST" }),
  boards: () => j("/api/板卡"),
  slots: () => j("/api/闪槽"),
  orders: () => j("/api/写闪单"),
  createOrder: (body) => j("/api/写闪单", { method: "POST", body: JSON.stringify(body) }),
  closeOrder: (id) => j(`/api/写闪单/${id}/收口`, { method: "POST" }),
  boot: () => j("/api/启动链"),
  promotionPolicy: () => j("/api/启动链/升格口径"),
  readBoard: (boardId) => j(`/api/启动链/${boardId}/对读`),
  switchSlot: (body) => j("/api/启动链/切槽", { method: "POST", body: JSON.stringify(body) }),
  promoteSlot: (pendingId) => j(`/api/升格/${pendingId}/收口`, { method: "POST" }),
  revertPromotion: (pendingId) => j(`/api/升格/${pendingId}/撤账`, { method: "POST" }),
  setBootColor: (boardId, body) =>
    j(`/api/启动链/${boardId}/探针色`, { method: "POST", body: JSON.stringify(body) }),
  policy: () => j("/api/回退拨"),
  setPolicy: (body) => j("/api/回退拨", { method: "POST", body: JSON.stringify(body) }),
  align: () => j("/api/校验"),
  settings: () => j("/api/板规"),
  events: () => j("/api/事件"),
};

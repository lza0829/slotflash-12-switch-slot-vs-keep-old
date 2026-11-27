import React from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import Firmwares from "./pages/Firmwares";
import Slots from "./pages/Slots";
import Orders from "./pages/Orders";
import Boot from "./pages/Boot";
import Policy from "./pages/Policy";
import Align from "./pages/Align";
import Rules from "./pages/Rules";

const links = [
  ["/", "固件仓"],
  ["/slots", "闪槽"],
  ["/orders", "写闪单"],
  ["/boot", "启动链"],
  ["/policy", "回退拨"],
  ["/align", "校验屏"],
  ["/rules", "板规"],
];

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          槽闪
          <small>slotflash</small>
        </div>
        <p className="tagline">双分区写闪与切槽启动。先入槽校验，再写闪落盘，失败可退回旧槽。</p>
      </header>
      <nav className="nav">
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<Firmwares />} />
          <Route path="/slots" element={<Slots />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/boot" element={<Boot />} />
          <Route path="/policy" element={<Policy />} />
          <Route path="/align" element={<Align />} />
          <Route path="/rules" element={<Rules />} />
        </Routes>
      </main>
    </div>
  );
}

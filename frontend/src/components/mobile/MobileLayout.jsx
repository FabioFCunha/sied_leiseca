import { Outlet } from "react-router-dom";
import MobileBottomNav from "./MobileBottomNav.jsx";
import "../../styles/mobile.css";

export default function MobileLayout() {
  return (
    <div className="mobile-app">
      <header className="mobile-header">
        <h1>SIED Operacional</h1>
      </header>
      <main className="mobile-content">
        <Outlet />
      </main>
      <MobileBottomNav />
    </div>
  );
}

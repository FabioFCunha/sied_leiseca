import { CalendarDays, ClipboardList, FileText, Home, Menu } from "lucide-react";
import { NavLink } from "react-router-dom";

const items = [
  { to: "/app/inicio", label: "Inicio", icon: Home },
  { to: "/app/agendas", label: "Agenda", icon: CalendarDays },
  { to: "/app/escala", label: "Escala", icon: ClipboardList },
  { to: "/app/relatorios", label: "Relatorios", icon: FileText },
  { to: "/app/mais", label: "Mais", icon: Menu },
];

export default function MobileBottomNav() {
  return (
    <nav className="mobile-bottom-nav">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) => `mobile-nav-item ${isActive ? "active" : ""}`}
        >
          <Icon size={22} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
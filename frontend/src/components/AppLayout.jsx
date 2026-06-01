import { BarChart3, Bell, CalendarDays, LayoutDashboard, ListPlus, LogOut, Menu, Moon, Search, Sun, Target, Users, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/agendas", label: "Solicitações", icon: CalendarDays },
  { to: "/calendario", label: "Calendário", icon: CalendarDays },
  { to: "/relatorio-tecnico", label: "Relatório técnico", icon: BarChart3 },
  { to: "/relatorios", label: "Relatórios", icon: BarChart3 },
  { to: "/estatisticas", label: "Estatísticas", icon: BarChart3 },
  { to: "/metas", label: "Metas", icon: Target, adminOnly: true },
  { to: "/cadastros", label: "Cadastros", icon: ListPlus, adminOnly: true },
  { to: "/usuarios", label: "Usuários", icon: Users, adminOnly: true },
];

const roleLabel = {
  ADMIN: "ADMIN",
  SUPERVISOR: "CHEFE",
  USER: "AGENTE",
};

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = () => {
    logout();
    navigate("/login");
  };

  const visibleItems = items.filter((item) => !item.adminOnly || user?.role === "ADMIN");

  return (
    <div className={`app-shell ${collapsed ? "is-collapsed" : ""} ${darkMode ? "dark-mode" : ""}`}>
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">A</div>
          <div className="brand-text">
            <strong>Agenda Educação</strong>
            <span>{roleLabel[user?.role] || user?.role}</span>
          </div>
          <button className="icon-button desktop-only" onClick={() => setCollapsed((value) => !value)} aria-label="Recolher menu">
            <Menu size={18} />
          </button>
          <button className="icon-button mobile-only" onClick={() => setOpen(false)} aria-label="Fechar menu">
            <X size={18} />
          </button>
        </div>
        <nav>
          {visibleItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"} onClick={() => setOpen(false)}>
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="logout" onClick={doLogout}>
          <LogOut size={18} />
          Sair
        </button>
      </aside>

      <main className="content">
        <header className="topbar">
          <button className="icon-button mobile-only" onClick={() => setOpen(true)} aria-label="Abrir menu">
            <Menu size={20} />
          </button>
          <div className="topbar-search">
            <Search size={17} />
            <input placeholder="Pesquisar no sistema" />
          </div>
          <button className="icon-button" aria-label="Notificações">
            <Bell size={18} />
          </button>
          <button className="icon-button" onClick={() => setDarkMode((value) => !value)} aria-label="Alternar tema">
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <div>
            <strong>{user?.full_name}</strong>
            <span>{user?.email}</span>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}

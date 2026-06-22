import { BarChart3, Bell, CalendarDays, LayoutDashboard, ListPlus, LogOut, Menu, Search, ShieldCheck, Target, Users, X } from "lucide-react";
import { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import logoOperacaoLeiSeca from "../assets/operacao-lei-seca-logo.png";
import { useAuth } from "../context/AuthContext.jsx";
import { canAccessRoute, roleLabel } from "../utils/permissions.js";
import { api } from "../api/client.js";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"] },
  { to: "/agendas", label: "Solicitações", icon: CalendarDays, roles: ["ADMIN", "MANAGER", "SUPERVISOR"] },
  { to: "/calendario", label: "Calendário", icon: CalendarDays },
  { to: "/escala", label: "Escala", icon: CalendarDays, roles: ["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"] },
  { to: "/relatorio-tecnico", label: "Relatório técnico", icon: BarChart3, roles: ["ADMIN", "MANAGER", "SUPERVISOR"] },
  { to: "/relatorios", label: "Relatórios", icon: BarChart3, roles: ["ADMIN", "MANAGER"] },
  { to: "/estatisticas", label: "Estatísticas", icon: BarChart3, roles: ["ADMIN", "MANAGER", "SUPERVISOR"] },
  { to: "/metas", label: "Metas", icon: Target, roles: ["ADMIN", "MANAGER"] },
  { to: "/cadastros", label: "Cadastros", icon: ListPlus, roles: ["ADMIN", "MANAGER"] },
  { to: "/usuarios", label: "Usuários", icon: Users, roles: ["ADMIN", "MANAGER", "CREATOR"] },
  { to: "/auditoria", label: "Auditoria", icon: ShieldCheck, roles: ["CREATOR"] },
];

const menuBadgeStyle = {
  background: "#f6bd16",
  color: "#001338",
  padding: "2px 8px",
  borderRadius: "12px",
  fontSize: "11px",
  fontWeight: "800",
  boxShadow: "0 2px 6px rgba(246, 189, 22, 0.3)",
};

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [pendingRequests, setPendingRequests] = useState(0);
  const [pendingTechnicalReports, setPendingTechnicalReports] = useState(0);
  const [pendingShiftSwaps, setPendingShiftSwaps] = useState(0);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const loadPendingShiftSwaps = () => {
      if (!user || !canAccessRoute(user, ["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"])) {
        setPendingShiftSwaps(0);
        return;
      }
      api("/shift-swaps/?status=PENDING&page_size=1")
        .then((data) => setPendingShiftSwaps(data.count || 0))
        .catch(() => setPendingShiftSwaps(0));
    };

    loadPendingShiftSwaps();
    window.addEventListener("shift-swaps:changed", loadPendingShiftSwaps);

    if (user && canAccessRoute(user, ["ADMIN", "MANAGER", "SUPERVISOR"])) {
      api("/agendas/?status=PENDING&source=requests&page_size=1")
        .then((data) => setPendingRequests(data.count || 0))
        .catch(() => {});
      Promise.all([
        api("/agendas/?page_size=1000&reportable=true"),
        api("/education-reports/?page_size=1000"),
      ])
        .then(([agendasData, reportsData]) => {
          const agendas = agendasData.results || agendasData;
          const reports = reportsData.results || reportsData;
          const completedAgendaIds = new Set(reports.map((report) => String(report.agenda)));
          setPendingTechnicalReports(
            agendas.filter((agenda) => !completedAgendaIds.has(String(agenda.id))).length
          );
        })
        .catch(() => {});
    }

    return () => window.removeEventListener("shift-swaps:changed", loadPendingShiftSwaps);
  }, [user]);
  const doLogout = () => {
    logout();
    navigate("/login");
  };

  const visibleItems = items.filter((item) => canAccessRoute(user, item.roles));

  return (
    <div className={`app-shell ${collapsed ? "is-collapsed" : ""}`}>
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="sidebar-logo" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <img src={logoOperacaoLeiSeca} alt="Operação Lei Seca" />
          <span className="logo-subtitle desktop-only-text">
            Educação
          </span>
          <div className="psi-logo-art desktop-only-text" aria-label="SISTEMA INTEGRADO DA EDUCAÇÃO">
            <strong>SIED</strong>
            <span>Sistema Integrado da Educação</span>
          </div>
        </div>
        <div className="brand">

          <div className="brand-text">
            <strong>SIED</strong>
            <span>{user?.is_superuser ? "CRIADOR" : roleLabel[user?.role] || user?.role}</span>
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
              <span style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, justifyContent: "space-between" }}>
                {item.label}
                {item.to === "/agendas" && pendingRequests > 0 && (
                  <span style={menuBadgeStyle}>
                    {pendingRequests}
                  </span>
                )}
                {item.to === "/escala" && pendingShiftSwaps > 0 && (
                  <span style={menuBadgeStyle}>
                    {pendingShiftSwaps}
                  </span>
                )}
                {item.to === "/relatorio-tecnico" && pendingTechnicalReports > 0 && (
                  <span style={menuBadgeStyle}>
                    {pendingTechnicalReports}
                  </span>
                )}
              </span>
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

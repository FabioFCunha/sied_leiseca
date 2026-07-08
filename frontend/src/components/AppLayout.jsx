import { Activity, BarChart3, Bell, CalendarDays, LayoutDashboard, ListPlus, LogOut, Menu, Search, ShieldCheck, Star, Target, Users, X } from "lucide-react";
import { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import logoOperacaoLeiSeca from "../assets/operacao-lei-seca-logo.png";
import { useAuth } from "../context/AuthContext.jsx";
import { canAccessRoute, roleLabel } from "../utils/permissions.js";
import { api } from "../api/client.js";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"], moduleName: "DASHBOARD" },
  { to: "/agendas", label: "Solicitações", icon: CalendarDays, roles: ["ADMIN", "MANAGER", "SUPERVISOR"], moduleName: "AGENDAS" },
  { to: "/calendario", label: "Calendário", icon: CalendarDays, moduleName: "CALENDARIO" },
  { to: "/escala", label: "Escala", icon: CalendarDays, roles: ["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"], moduleName: "ESCALA" },
  { to: "/relatorio-tecnico", label: "Relatórios Técnicos", icon: BarChart3, roles: ["ADMIN", "MANAGER", "SUPERVISOR"], moduleName: "RELATORIOS" },
  { to: "/estatisticas", label: "Estatísticas", icon: BarChart3, roles: ["ADMIN", "MANAGER", "SUPERVISOR"], moduleName: "ESTATISTICAS" },
  { to: "/avaliacoes", label: "Avaliações", icon: Star, roles: ["ADMIN", "MANAGER", "SUPERVISOR"], moduleName: "AVALIACOES" },

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
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [showOnlinePanel, setShowOnlinePanel] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!user) return;
    const ping = () => {
      api("/users/ping/", { method: "POST" }).catch(() => {});
    };
    ping();
    const interval = setInterval(ping, 60000);
    return () => clearInterval(interval);
  }, [user]);

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

    const loadPendingRequests = () => {
      if (!user || !canAccessRoute(user, ["ADMIN", "MANAGER", "SUPERVISOR"])) {
        setPendingRequests(0);
        return;
      }
      api("/agendas/?status=PENDING&source=requests&page_size=1")
        .then((data) => setPendingRequests(data.count || 0))
        .catch(() => setPendingRequests(0));
    };

    const syncPendingRequests = (event) => {
      if (typeof event.detail?.count === "number") {
        setPendingRequests(event.detail.count);
      } else {
        loadPendingRequests();
      }
    };

    loadPendingShiftSwaps();
    loadPendingRequests();
    window.addEventListener("focus", loadPendingRequests);
    window.addEventListener("agenda-requests:changed", syncPendingRequests);
    window.addEventListener("shift-swaps:changed", loadPendingShiftSwaps);

    if (user && canAccessRoute(user, ["ADMIN", "MANAGER", "SUPERVISOR"])) {
      api("/dashboard/")
        .then((data) => {
          setPendingTechnicalReports(data.pending_technical_reports_count || 0);
        })
        .catch(() => {});
    }

    return () => {
      window.removeEventListener("focus", loadPendingRequests);
      window.removeEventListener("agenda-requests:changed", syncPendingRequests);
      window.removeEventListener("shift-swaps:changed", loadPendingShiftSwaps);
    };
  }, [user, location.pathname]);
  const fetchOnlineUsers = () => {
    api("/users/online/")
      .then(data => setOnlineUsers(data))
      .catch(() => {});
  };

  const toggleOnlinePanel = () => {
    setShowOnlinePanel(val => {
      if (!val) fetchOnlineUsers();
      return !val;
    });
  };

  const doLogout = () => {
    logout();
    navigate("/login");
  };

  const visibleItems = items.filter((item) => canAccessRoute(user, item.roles, item.moduleName));

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
          {canAccessRoute(user, ["ADMIN", "MANAGER"]) && (
            <div style={{ position: "relative" }}>
              <button className={`icon-button ${showOnlinePanel ? "active" : ""}`} aria-label="Usuários online" onClick={toggleOnlinePanel} title="Usuários online">
                <Activity size={18} />
              </button>
              {showOnlinePanel && (
                <div style={{ position: "absolute", right: 0, top: "100%", marginTop: "8px", background: "white", border: "1px solid #ddd", borderRadius: "8px", width: "250px", boxShadow: "0 4px 12px rgba(0,0,0,0.1)", zIndex: 100, padding: "12px", maxHeight: "300px", overflowY: "auto" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <h4 style={{ margin: 0, fontSize: "14px", color: "#333" }}>Usuários Online</h4>
                    <button className="icon-button" style={{ padding: "4px" }} onClick={toggleOnlinePanel}><X size={14} /></button>
                  </div>
                  {onlineUsers.length === 0 ? (
                    <p style={{ margin: 0, fontSize: "12px", color: "#666" }}>Nenhum usuário online.</p>
                  ) : (
                    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                      {onlineUsers.map(ou => (
                        <li key={ou.id} style={{ fontSize: "12px", padding: "6px 0", borderBottom: "1px solid #eee", color: "#444" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: "#4caf50" }}></span>
                            <strong>{ou.full_name || ou.email}</strong>
                          </div>
                          <div style={{ fontSize: "11px", color: "#888", marginLeft: "14px" }}>{ou.occupation}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
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

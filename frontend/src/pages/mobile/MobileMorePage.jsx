import { useAuth } from "../../context/AuthContext.jsx";
import { roleLabel } from "../../utils/permissions.js";
import { LogOut, ExternalLink, ClipboardCheck, ChevronRight, FileText, Monitor } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";

export default function MobileMorePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleOpenDesktop = () => {
    navigate("/");
  };

  return (
    <>
      <div className="mobile-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', marginBottom: '8px' }}>
        <div style={{ width: '60px', height: '60px', borderRadius: '30px', backgroundColor: '#0a1e44', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', fontWeight: 'bold', marginBottom: '12px' }}>
          {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
        </div>
        <h2 style={{ margin: '0 0 4px', fontSize: '18px', color: '#0a1e44' }}>{user?.full_name}</h2>
        <span style={{ fontSize: '13px', color: '#64748b', backgroundColor: '#f1f5f9', padding: '4px 12px', borderRadius: '12px' }}>
          {roleLabel[user?.role] || user?.role}
        </span>
        {user?.team && (
          <span style={{ fontSize: '13px', color: '#64748b', marginTop: '8px' }}>
            Equipe: {user.team}
          </span>
        )}
      </div>

      <div className="mobile-card" style={{ padding: 0, overflow: 'hidden', marginTop: '16px' }}>
        <Link to="/app/frequencia" className="mobile-list-item" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', textDecoration: 'none', color: '#0f172a', borderBottom: '1px solid #f1f5f9' }}>
          <ClipboardCheck size={20} color="#64748b" />
          <span>Frequência Operacional</span>
          <ChevronRight size={20} color="#cbd5e1" style={{ marginLeft: 'auto' }} />
        </Link>
        
        <Link to="/app/relatorios" className="mobile-list-item" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', textDecoration: 'none', color: '#0f172a', borderBottom: '1px solid #f1f5f9' }}>
          <FileText size={20} color="#64748b" />
          <span>Relatório Técnico</span>
          <ChevronRight size={20} color="#cbd5e1" style={{ marginLeft: 'auto' }} />
        </Link>
      </div>

      <button className="mobile-btn mobile-btn-primary" onClick={handleOpenDesktop} style={{ marginTop: '16px' }}>
        <Monitor size={20} />
        Versão completa
      </button>

      <button className="mobile-btn mobile-btn-danger" onClick={handleLogout} style={{ marginTop: '16px' }}>
        <LogOut size={20} />
        Sair
      </button>

      <div style={{ textAlign: 'center', marginTop: 'auto', paddingTop: '24px', fontSize: '11px', color: '#94a3b8' }}>
        <p style={{ margin: 0 }}>Sistema Integrado da Educação</p>
        {window.__APP_VERSION__ && <p style={{ margin: '4px 0 0' }}>Versão {window.__APP_VERSION__}</p>}
      </div>
    </>
  );
}

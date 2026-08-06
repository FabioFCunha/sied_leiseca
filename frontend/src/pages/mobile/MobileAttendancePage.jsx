import { Link } from "react-router-dom";
import { ClipboardCheck, Calendar, ClipboardList } from "lucide-react";

export default function MobileAttendancePage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '16px' }}>
      
      <div style={{ textAlign: 'center', marginTop: '16px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', backgroundColor: '#e0f2fe', color: '#0284c7', marginBottom: '16px' }}>
          <ClipboardCheck size={32} />
        </div>
        <h1 style={{ margin: '0 0 8px', fontSize: '22px', color: '#0f172a' }}>Frequência Operacional</h1>
        <p style={{ margin: 0, fontSize: '15px', color: '#475569', lineHeight: '1.5' }}>
          Consulte a frequência a partir de uma Agenda com participantes selecionados ou dos detalhes da sua Escala.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <Link to="/app/escala" className="mobile-btn mobile-btn-primary" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', padding: '14px' }}>
          <ClipboardList size={20} />
          Abrir Minha Escala
        </Link>

        <Link to="/app/agendas" className="mobile-btn mobile-btn-outline" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', padding: '14px', color: '#0a1e44', borderColor: '#0a1e44' }}>
          <Calendar size={20} />
          Abrir Agendas
        </Link>
      </div>

    </div>
  );
}

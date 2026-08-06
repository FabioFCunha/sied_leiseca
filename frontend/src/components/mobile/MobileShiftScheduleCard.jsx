import { Users, ChevronRight, UserMinus } from "lucide-react";
import { Link } from "react-router-dom";

export default function MobileShiftScheduleCard({ schedule }) {
  const members = schedule.members || { chiefs: [], agents: [], supports: [] };
  const totalIntegrantes = (members.chiefs?.length || 0) + (members.agents?.length || 0) + (members.supports?.length || 0);
  const totaisFaltas = (members.chiefs || []).filter(c => c.is_absent).length + 
                       (members.agents || []).filter(a => a.is_absent).length + 
                       (members.supports || []).filter(s => s.is_absent).length;

  return (
    <Link to={`/app/escala/${schedule.id}`} style={{ textDecoration: 'none', display: 'block', color: 'inherit' }}>
      <div className="mobile-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ backgroundColor: '#e2e8f0', color: '#334155', fontSize: '11px', fontWeight: 'bold', padding: '4px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
              Equipe {schedule.team_name}
            </span>
            {totaisFaltas > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#fee2e2', color: '#991b1b', fontSize: '11px', fontWeight: 'bold', padding: '4px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
                <UserMinus size={12} /> {totaisFaltas}
              </span>
            )}
          </div>
          <ChevronRight size={20} color="#cbd5e1" style={{ flexShrink: 0 }} />
        </div>

        <div>
          <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: '600', color: '#0f172a', lineHeight: '1.4', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={18} color="#64748b" />
            Efetivo Total: {totalIntegrantes}
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#475569' }}>
          <span><strong>{members.chiefs?.length || 0}</strong> Chefe(s)</span>
          <span><strong>{members.agents?.length || 0}</strong> Agente(s)</span>
          <span><strong>{members.supports?.length || 0}</strong> Apoio(s)</span>
        </div>
        
      </div>
    </Link>
  );
}

import { ChevronRight, MapPin, Clock, Users, User } from "lucide-react";
import { Link } from "react-router-dom";
import { statusLabel, statusClass } from "../../utils/status.js";
import { normalizeTime } from "../../utils/date.js";

export default function MobileAgendaCard({ agenda }) {
  const statusInfo = statusLabel[agenda.status] || "Desconhecido";
  const statusColorClass = statusClass[agenda.status] || "";

  // Helper local para mapear a classe Desktop para cor CSS inline simplificada
  const getBadgeColor = (cls) => {
    if (cls === "success") return { bg: "#dcfce7", text: "#166534" };
    if (cls === "warning" || cls === "amber") return { bg: "#fef3c7", text: "#92400e" };
    if (cls === "danger") return { bg: "#fee2e2", text: "#991b1b" };
    if (cls === "info") return { bg: "#dbeafe", text: "#1e40af" };
    return { bg: "#f1f5f9", text: "#475569" };
  };

  const badgeStyle = getBadgeColor(statusColorClass);
  const timeStr = normalizeTime(agenda.start_time);

  return (
    <Link to={`/app/agendas/${agenda.id}`} style={{ textDecoration: 'none', display: 'block', color: 'inherit' }}>
      <div className="mobile-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', position: 'relative' }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {timeStr && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', fontWeight: '600', color: '#0a1e44', backgroundColor: '#f1f5f9', padding: '4px 8px', borderRadius: '6px' }}>
                <Clock size={14} />
                {timeStr}
              </span>
            )}
            <span style={{ backgroundColor: badgeStyle.bg, color: badgeStyle.text, fontSize: '11px', fontWeight: 'bold', padding: '4px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
              {statusInfo}
            </span>
            {agenda.service_order_mode === "DESIGNATED" && (
              <span style={{ backgroundColor: '#e2e8f0', color: '#334155', fontSize: '11px', fontWeight: 'bold', padding: '4px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
                Designado
              </span>
            )}
          </div>
          <ChevronRight size={20} color="#cbd5e1" style={{ flexShrink: 0 }} />
        </div>

        <div>
          <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: '600', color: '#0f172a', lineHeight: '1.4' }}>
            {agenda.title || agenda.action_type || "Agenda sem título"}
          </h3>
          {agenda.requester_entity_type && (
            <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
              {agenda.requester_entity_type}
            </p>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {(agenda.address || agenda.city) && (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', fontSize: '13px', color: '#475569' }}>
              <MapPin size={16} style={{ flexShrink: 0, marginTop: '2px', color: '#94a3b8' }} />
              <span>
                {agenda.address ? `${agenda.address}${agenda.city ? ` - ${agenda.city}` : ''}` : agenda.city}
              </span>
            </div>
          )}

          {agenda.service_order_mode === "TEAM" && agenda.team_name && (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '13px', color: '#475569' }}>
              <Users size={16} style={{ flexShrink: 0, color: '#94a3b8' }} />
              <span>Equipe: {agenda.team_name}</span>
            </div>
          )}

          {agenda.service_order_mode === "DESIGNATED" && agenda.designated_users && agenda.designated_users.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '13px', color: '#475569' }}>
              <User size={16} style={{ flexShrink: 0, color: '#94a3b8' }} />
              <span>{agenda.designated_users.length} designado(s)</span>
            </div>
          )}
        </div>
        
      </div>
    </Link>
  );
}

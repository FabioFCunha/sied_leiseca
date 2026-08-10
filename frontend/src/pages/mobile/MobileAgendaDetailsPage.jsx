import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ArrowLeft, Clock, MapPin, Phone, Users, User, FileText, Calendar as CalendarIcon, Package } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import { statusLabel, statusClass } from "../../utils/status.js";
import { normalizeTime, formatDateBR } from "../../utils/date.js";

export default function MobileAgendaDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [agenda, setAgenda] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [report, setReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [reportError, setReportError] = useState(null);

  const { user } = useAuth();
  const abortControllerRef = useRef(null);

  const fetchAgenda = async () => {
    setLoading(true);
    setError(null);
    try {
      abortControllerRef.current = new AbortController();
      const data = await api(`/agendas/${id}/`, { signal: abortControllerRef.current.signal });
      setAgenda(data);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError("Não foi possível carregar os detalhes da agenda.");
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchReport = async (fetchedAgenda) => {
    setLoadingReport(true);
    setReportError(null);
    try {
      const res = await api(`/education-reports/?protocol=${id}`, { signal: abortControllerRef.current?.signal });
      const results = Array.isArray(res?.results) ? res.results : Array.isArray(res) ? res : [];
      if (results.length === 1) {
        setReport(results[0]);
      } else if (results.length > 1) {
        const agendaTeam = fetchedAgenda?.team_name || fetchedAgenda?.team_ref_name || fetchedAgenda?.sector_name;
        const matching = agendaTeam ? results.find(r => String(r.team) === String(agendaTeam)) : null;
        if (matching) {
          setReport(matching);
        } else {
          setReportError("Não foi possível identificar com segurança o relatório desta equipe.");
          setReport(null);
        }
      } else {
        setReport(null);
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        setReportError("Não foi possível verificar o relatório associado.");
      }
    } finally {
      setLoadingReport(false);
    }
  };

  useEffect(() => {
    fetchAgenda();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [id]);

  useEffect(() => {
    if (agenda) {
      fetchReport(agenda);
    }
  }, [agenda?.id]);

  const handleBack = () => {
    navigate(-1);
  };

  const getBadgeColor = (cls) => {
    if (cls === "success") return { bg: "#dcfce7", text: "#166534" };
    if (cls === "warning" || cls === "amber") return { bg: "#fef3c7", text: "#92400e" };
    if (cls === "danger") return { bg: "#fee2e2", text: "#991b1b" };
    if (cls === "info") return { bg: "#dbeafe", text: "#1e40af" };
    return { bg: "#f1f5f9", text: "#475569" };
  };

  if (loading) return <MobileLoadingState message="Carregando detalhes..." />;
  if (error) return <MobileErrorState message={error} onRetry={fetchAgenda} />;
  if (!agenda) return <MobileErrorState message="Agenda não encontrada." />;

  const statusInfo = statusLabel[agenda.status] || "Desconhecido";
  const badgeStyle = getBadgeColor(statusClass[agenda.status] || "");
  const timeStr = normalizeTime(agenda.start_time);
  const endTimeStr = normalizeTime(agenda.end_time);
  const fullAddress = [agenda.address, agenda.neighborhood, agenda.city].filter(Boolean).join(" - ");

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '32px' }}>
      {/* Topbar interna */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <button onClick={handleBack} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600' }}>
          <ArrowLeft size={20} />
          Voltar
        </button>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
        <span style={{ backgroundColor: badgeStyle.bg, color: badgeStyle.text, fontSize: '12px', fontWeight: 'bold', padding: '6px 12px', borderRadius: '12px', textTransform: 'uppercase' }}>
          {statusInfo}
        </span>
        {agenda.service_order_mode === "DESIGNATED" && (
          <span style={{ backgroundColor: '#e2e8f0', color: '#334155', fontSize: '12px', fontWeight: 'bold', padding: '6px 12px', borderRadius: '12px', textTransform: 'uppercase' }}>
            Designação Direta
          </span>
        )}
      </div>

      <h1 style={{ margin: 0, fontSize: '22px', color: '#0f172a', lineHeight: '1.3' }}>
        {agenda.title || agenda.action_type || "Agenda sem título"}
      </h1>

      {agenda.service_order_mode === "DESIGNATED" && agenda.designated_users_details && agenda.designated_users_details.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <button 
            onClick={() => navigate(`/app/frequencia/agenda/${agenda.id}`)}
            className="mobile-btn mobile-btn-outline" 
            style={{ width: '100%', display: 'flex', justifyContent: 'center' }}
          >
            Ver frequência dos participantes
          </button>
        </div>
      )}

      {/* Botões contextuais do Relatório Técnico */}
      <div style={{ marginBottom: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {loadingReport ? (
          <div style={{ textAlign: 'center', color: '#64748b', fontSize: '13px', padding: '8px' }}>Verificando relatório...</div>
        ) : reportError ? (
          <div style={{ textAlign: 'center', color: '#991b1b', fontSize: '13px', padding: '8px' }}>{reportError}</div>
        ) : (
          (() => {
            const isVisitor = user?.role === 'VISITOR';

            if (!report) {
              if (isVisitor) return null;
              return (
                <button
                  onClick={() => navigate(`/app/relatorios/novo/${agenda.id}`)}
                  className="mobile-btn mobile-btn-primary"
                >
                  <FileText size={18} />
                  Preencher relatório
                </button>
              );
            }

            if (report.status === "DRAFT") {
              if (isVisitor) return null;
              return (
                <button
                  onClick={() => navigate(`/app/relatorios/${report.id}/editar`)}
                  className="mobile-btn mobile-btn-primary"
                >
                  <FileText size={18} />
                  Continuar relatório
                </button>
              );
            }

            if (report.status === "RETURNED") {
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div className="mobile-alert" style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '4px', border: '1px solid #fca5a5' }}>
                    <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><FileText size={14}/> Relatório devolvido</strong>
                    <span>{report.review_notes || "Necessita correções."}</span>
                  </div>
                  {!isVisitor && (
                    <button
                      onClick={() => navigate(`/app/relatorios/${report.id}/editar`)}
                      className="mobile-btn mobile-btn-primary"
                      style={{ backgroundColor: '#dc2626' }}
                    >
                      <FileText size={18} />
                      Corrigir relatório
                    </button>
                  )}
                </div>
              );
            }

            if (report.status === "PENDING_REVIEW" || report.status === "APPROVED") {
               return (
                <button
                  onClick={() => navigate(`/app/relatorios/${report.id}`)}
                  className="mobile-btn mobile-btn-outline"
                >
                  <FileText size={18} />
                  Ver relatório
                </button>
              );
            }

            return null;
          })()
        )}
      </div>

      {/* Info Card: Data e Local */}
      <div className="mobile-card">
        <h3 className="mobile-card-header">Data e Local</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', color: '#334155', fontSize: '14px' }}>
            <CalendarIcon size={18} style={{ color: '#64748b', marginTop: '2px', flexShrink: 0 }} />
            <div>
              <strong>{formatDateBR(agenda.date) || agenda.date}</strong>
              {(timeStr || endTimeStr) && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px', color: '#475569' }}>
                  <Clock size={14} />
                  {timeStr} {endTimeStr ? `às ${endTimeStr}` : ""}
                </div>
              )}
            </div>
          </div>

          {fullAddress && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', color: '#334155', fontSize: '14px', marginTop: '4px' }}>
              <MapPin size={18} style={{ color: '#64748b', marginTop: '2px', flexShrink: 0 }} />
              <div>
                <span style={{ display: 'block', lineHeight: '1.4' }}>{fullAddress}</span>
                <a 
                  href={`https://maps.google.com/?q=${encodeURIComponent(fullAddress)}`}
                  target="_blank" rel="noopener noreferrer"
                  style={{ display: 'inline-block', marginTop: '8px', color: '#0a1e44', fontSize: '13px', fontWeight: '600', textDecoration: 'none', backgroundColor: '#f1f5f9', padding: '6px 12px', borderRadius: '6px' }}
                >
                  Abrir no Mapa
                </a>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Card: Solicitante */}
      {(agenda.requester_entity_type || agenda.external_responsible) && (
        <div className="mobile-card">
          <h3 className="mobile-card-header">Contato / Solicitante</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '14px', color: '#334155' }}>
            {agenda.requester_entity_type && (
              <p style={{ margin: 0 }}><strong>Tipo:</strong> {agenda.requester_entity_type}</p>
            )}
            {agenda.external_responsible && (
              <p style={{ margin: 0 }}><strong>Responsável:</strong> {agenda.external_responsible}</p>
            )}
            {agenda.external_responsible_phone && (
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px' }}>
                <Phone size={16} color="#64748b" />
                <a href={`tel:${agenda.external_responsible_phone.replace(/\D/g, '')}`} style={{ color: '#0a1e44', textDecoration: 'none', fontWeight: '500' }}>
                  {agenda.external_responsible_phone}
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info Card: Equipe (Se TEAM) */}
      {agenda.service_order_mode === "TEAM" && (
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={18} /> Participantes (Equipe)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '14px', color: '#334155' }}>
            {agenda.team_name ? <p style={{ margin: 0 }}><strong>Equipe:</strong> {agenda.team_name}</p> : null}
            {agenda.chief_name ? <p style={{ margin: 0 }}><strong>Chefe:</strong> {agenda.chief_name}</p> : null}
            {agenda.team_phone ? (
              <p style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Phone size={14} color="#64748b" /> 
                <a href={`tel:${agenda.team_phone.replace(/\D/g, '')}`} style={{ color: '#0a1e44', textDecoration: 'none' }}>{agenda.team_phone}</a>
              </p>
            ) : null}
            {agenda.agents && agenda.agents.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <strong>Agentes:</strong>
                <ul style={{ margin: '4px 0 0', paddingLeft: '20px', color: '#475569' }}>
                  {agenda.agents.map((ag, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>{ag.full_name || ag.name || (typeof ag === 'string' ? ag : 'Agente')}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info Card: Designados (Se DESIGNATED) */}
      {agenda.service_order_mode === "DESIGNATED" && agenda.designated_users && agenda.designated_users.length > 0 && (
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <User size={18} /> Participantes Designados
          </h3>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: '#475569' }}>
            {agenda.designated_users.map(u => (
              <li key={u.id || u.user?.id} style={{ marginBottom: '6px' }}>
                <strong>{u.user?.full_name || u.full_name || 'Usuário'}</strong>
                {u.role ? ` (${u.role})` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Info Card: Materiais */}
      {((agenda.materials && agenda.materials.length > 0) || agenda.kit_1) && (
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Package size={18} /> Materiais e Kits
          </h3>
          <div style={{ fontSize: '14px', color: '#475569' }}>
            {/* Se usar a nova estrutura de array */}
            {agenda.materials && agenda.materials.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {agenda.materials.map((m, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {m.quantity}x {m.name || m.material}
                  </li>
                ))}
              </ul>
            )}
            
            {/* Se usar campos legados kit_1, material_1 */}
            {agenda.kit_1 && <p style={{ margin: '4px 0' }}>{agenda.kit_1_quantity}x {agenda.kit_1} {agenda.material_1}</p>}
            {agenda.kit_2 && <p style={{ margin: '4px 0' }}>{agenda.kit_2_quantity}x {agenda.kit_2} {agenda.material_2}</p>}
            {agenda.kit_3 && <p style={{ margin: '4px 0' }}>{agenda.kit_3_quantity}x {agenda.kit_3} {agenda.material_3}</p>}
          </div>
        </div>
      )}

      {/* Info Card: Observações */}
      {agenda.notes && (
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={18} /> Observações
          </h3>
          <p style={{ margin: 0, fontSize: '14px', color: '#475569', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
            {agenda.notes}
          </p>
        </div>
      )}

    </div>
  );
}

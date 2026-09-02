import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  ArrowLeft,
  Clock,
  MapPin,
  Phone,
  Users,
  User,
  FileText,
  Calendar as CalendarIcon,
  Package,
  Mail,
  Car,
  Building2,
  ClipboardList,
  Info,
} from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import { statusLabel, statusClass } from "../../utils/status.js";
import { normalizeTime, formatDateBR } from "../../utils/date.js";
import { getAgendaAgentNames, getAgendaChiefNames, getAgendaStaffWarning, getAgendaSupportNames } from "../../utils/agendaStaff.js";
import { STREET_ACTION_ID } from "../../utils/constants.js";
import { streetActionTypeLabel } from "../../utils/streetActionTypes.js";

function serviceOrderLabel(agenda) {
  const number = agenda?.service_order_number;
  return number ? `OS ${String(number).padStart(4, "0")}` : "-";
}

function displayValue(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  return String(value);
}

function normalizeList(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "string" && value.trim()) {
    return value
      .split(/\s+-\s+|,\s*/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function requesterTypeLabel(value) {
  if (String(value) === String(STREET_ACTION_ID)) return "Ação de Rua";
  return displayValue(value);
}

function agendaActionType(agenda) {
  return (
    agenda?.action_type ||
    agenda?.action_type_ref_name ||
    agenda?.activity_type ||
    "-"
  );
}

function materialName(item) {
  return (
    item?.dynamic_name ||
    item?.kit_name ||
    item?.material_name ||
    item?.name ||
    item?.dynamic ||
    item?.kit ||
    item?.material ||
    "Item"
  );
}

function materialCategory(item) {
  if (item?.dynamic || item?.dynamic_name) return "Dinâmica";
  if (item?.kit || item?.kit_name) return "Material para distribuição";
  if (item?.material || item?.material_name) return "Material de apoio";
  return "Material";
}

function memberName(member) {
  if (!member) return "";
  if (typeof member === "string") return member;
  return (
    member.full_name ||
    member.name ||
    member.user?.full_name ||
    member.user?.name ||
    ""
  );
}

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
      const data = await api(`/agendas/${id}/`, {
        signal: abortControllerRef.current.signal,
      });
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
      const res = await api(`/education-reports/?protocol=${id}`, {
        signal: abortControllerRef.current?.signal,
      });
      const results = Array.isArray(res?.results)
        ? res.results
        : Array.isArray(res)
          ? res
          : [];

      if (results.length === 1) {
        setReport(results[0]);
      } else if (results.length > 1) {
        const agendaTeam =
          fetchedAgenda?.team_name ||
          fetchedAgenda?.team_ref_name ||
          fetchedAgenda?.sector_name;

        const matching = agendaTeam
          ? results.find((item) => String(item.team) === String(agendaTeam))
          : null;

        if (matching) {
          setReport(matching);
        } else {
          setReportError(
            "Não foi possível identificar com segurança o relatório desta equipe."
          );
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
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
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
    if (cls === "warning" || cls === "amber") {
      return { bg: "#fef3c7", text: "#92400e" };
    }
    if (cls === "danger") return { bg: "#fee2e2", text: "#991b1b" };
    if (cls === "info") return { bg: "#dbeafe", text: "#1e40af" };
    return { bg: "#f1f5f9", text: "#475569" };
  };

  if (loading) {
    return <MobileLoadingState message="Carregando detalhes..." />;
  }

  if (error) {
    return <MobileErrorState message={error} onRetry={fetchAgenda} />;
  }

  if (!agenda) {
    return <MobileErrorState message="Agenda não encontrada." />;
  }

  const statusInfo = statusLabel[agenda.status] || "Desconhecido";
  const badgeStyle = getBadgeColor(statusClass[agenda.status] || "");
  const timeStr = normalizeTime(agenda.start_time);
  const endTimeStr = normalizeTime(agenda.end_time);

  const fullAddress = [
    agenda.address,
    agenda.neighborhood || agenda.neighborhood_ref_name,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
  ]
    .filter(Boolean)
    .join(" - ");

  const agents = getAgendaAgentNames(agenda);
  const designatedUsers =
    (Array.isArray(agenda.designated_users_details) &&
      agenda.designated_users_details) ||
    (Array.isArray(agenda.designated_users) && agenda.designated_users) ||
    [];

  const supports = getAgendaSupportNames(agenda);
  const chiefs = getAgendaChiefNames(agenda);
  const staffWarning = getAgendaStaffWarning(agenda);

  const vehicles = normalizeList(
    agenda.vehicle_name || agenda.vehicle || ""
  );

  const materials = Array.isArray(agenda.materials)
    ? agenda.materials.filter(
        (item) =>
          item?.dynamic ||
          item?.dynamic_name ||
          item?.kit ||
          item?.kit_name ||
          item?.material ||
          item?.material_name ||
          item?.name
      )
    : [];

  const streetActionDetails = Array.isArray(agenda.street_action_details)
    ? agenda.street_action_details
    : [];

  const isStreetAction =
    String(agenda.action_type_ref) === String(STREET_ACTION_ID) ||
    String(agenda.requester_entity_type) === String(STREET_ACTION_ID) ||
    String(agenda.action_type_ref_name || "")
      .trim()
      .toLocaleLowerCase("pt-BR") === "ação de rua";

  const responsibleInternal =
    agenda.responsible_name ||
    agenda.created_by_name ||
    "";

  const hasRequestActivityInfo = Boolean(
    agenda.institution_location ||
      agenda.requester_entity_type ||
      agenda.action_type ||
      agenda.action_type_ref_name ||
      agenda.activity_type ||
      agenda.audience ||
      agenda.age_ranges ||
      agenda.participant_range ||
      agenda.quantity ||
      streetActionDetails.length ||
      agenda.travel_displacement
  );

  const hasAccessibilityInfo = Boolean(
    agenda.accessibility_access ||
      agenda.has_ramps ||
      agenda.has_elevators ||
      agenda.has_accessible_bathrooms ||
      agenda.media_equipment ||
      agenda.image_authorization
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        paddingBottom: "32px",
      }}
    >
      {/* Topbar interna */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "8px",
        }}
      >
        <button
          onClick={handleBack}
          style={{
            background: "none",
            border: "none",
            padding: "8px",
            cursor: "pointer",
            color: "#0a1e44",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            fontWeight: "600",
          }}
        >
          <ArrowLeft size={20} />
          Voltar
        </button>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          alignItems: "center",
          marginBottom: "4px",
        }}
      >
        <span
          style={{
            backgroundColor: badgeStyle.bg,
            color: badgeStyle.text,
            fontSize: "12px",
            fontWeight: "bold",
            padding: "6px 12px",
            borderRadius: "12px",
            textTransform: "uppercase",
          }}
        >
          {statusInfo}
        </span>

        {agenda.service_order_mode === "DESIGNATED" && (
          <span
            style={{
              backgroundColor: "#e2e8f0",
              color: "#334155",
              fontSize: "12px",
              fontWeight: "bold",
              padding: "6px 12px",
              borderRadius: "12px",
              textTransform: "uppercase",
            }}
          >
            Designação Direta
          </span>
        )}
      </div>

      <h1
        style={{
          margin: 0,
          fontSize: "22px",
          color: "#0f172a",
          lineHeight: "1.3",
        }}
      >
        {agenda.title || agenda.action_type || "Agenda sem título"}
      </h1>

      {/* Identificação da OS */}
      <div className="mobile-card">
        <h3
          className="mobile-card-header"
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <ClipboardList size={18} /> Identificação da OS
        </h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            fontSize: "14px",
            color: "#334155",
          }}
        >
          <div>
            <strong>Protocolo</strong>
            <div style={{ marginTop: "3px", color: "#475569" }}>
              #{agenda.id}
            </div>
          </div>

          <div>
            <strong>Ordem de Serviço</strong>
            <div style={{ marginTop: "3px", color: "#475569" }}>
              {serviceOrderLabel(agenda)}
            </div>
          </div>

          <div>
            <strong>Origem</strong>
            <div style={{ marginTop: "3px", color: "#475569" }}>
              {agenda.origin === "INTERNAL"
                ? "Solicitação interna"
                : agenda.origin === "PUBLIC_FORM"
                  ? "Solicitação externa"
                  : displayValue(agenda.origin)}
            </div>
          </div>

          <div>
            <strong>Modo da OS</strong>
            <div style={{ marginTop: "3px", color: "#475569" }}>
              {agenda.service_order_mode === "DESIGNATED"
                ? "Participantes selecionados"
                : "Equipe operacional"}
            </div>
          </div>

          {responsibleInternal && (
            <div style={{ gridColumn: "1 / -1" }}>
              <strong>Responsável interno</strong>
              <div style={{ marginTop: "3px", color: "#475569" }}>
                {responsibleInternal}
              </div>
            </div>
          )}
        </div>
      </div>

      {agenda.internal_observation?.trim() && (
        <div
          className="mobile-card"
          style={{
            background: "#e7f1ff",
            border: "1px solid #b6d4fe",
            overflowWrap: "anywhere",
          }}
        >
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px", color: "#084298" }}
          >
            <Info size={18} /> OBSERVAÇÃO DA OS
          </h3>
          <p style={{ margin: 0, color: "#084298", whiteSpace: "pre-wrap", lineHeight: "1.5" }}>
            {agenda.internal_observation}
          </p>
        </div>
      )}

      {agenda.service_order_mode === "DESIGNATED" &&
        designatedUsers.length > 0 && (
          <div style={{ marginBottom: "8px" }}>
            <button
              onClick={() =>
                navigate(`/app/frequencia/agenda/${agenda.id}`)
              }
              className="mobile-btn mobile-btn-outline"
              style={{
                width: "100%",
                display: "flex",
                justifyContent: "center",
              }}
            >
              Ver frequência dos participantes
            </button>
          </div>
        )}

      {/* Botões contextuais do Relatório Técnico */}
      <div
        style={{
          marginBottom: "8px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        {loadingReport ? (
          <div
            style={{
              textAlign: "center",
              color: "#64748b",
              fontSize: "13px",
              padding: "8px",
            }}
          >
            Verificando relatório...
          </div>
        ) : reportError ? (
          <div
            style={{
              textAlign: "center",
              color: "#991b1b",
              fontSize: "13px",
              padding: "8px",
            }}
          >
            {reportError}
          </div>
        ) : (
          (() => {
            const isVisitor = user?.role === "VISITOR";

            if (!report) {
              if (isVisitor) return null;

              return (
                <button
                  onClick={() =>
                    navigate(`/app/relatorios/novo/${agenda.id}`)
                  }
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
                  onClick={() =>
                    navigate(`/app/relatorios/${report.id}/editar`)
                  }
                  className="mobile-btn mobile-btn-primary"
                >
                  <FileText size={18} />
                  Continuar relatório
                </button>
              );
            }

            if (report.status === "RETURNED") {
              return (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div
                    className="mobile-alert"
                    style={{
                      backgroundColor: "#fee2e2",
                      color: "#991b1b",
                      padding: "12px",
                      borderRadius: "8px",
                      fontSize: "13px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                      border: "1px solid #fca5a5",
                    }}
                  >
                    <strong
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <FileText size={14} /> Relatório devolvido
                    </strong>
                    <span>
                      {report.review_notes || "Necessita correções."}
                    </span>
                  </div>

                  {!isVisitor && (
                    <button
                      onClick={() =>
                        navigate(`/app/relatorios/${report.id}/editar`)
                      }
                      className="mobile-btn mobile-btn-primary"
                      style={{ backgroundColor: "#dc2626" }}
                    >
                      <FileText size={18} />
                      Corrigir relatório
                    </button>
                  )}
                </div>
              );
            }

            if (
              report.status === "PENDING_REVIEW" ||
              report.status === "APPROVED"
            ) {
              return (
                <button
                  onClick={() =>
                    navigate(`/app/relatorios/${report.id}`)
                  }
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

      {/* Data e Local */}
      <div className="mobile-card">
        <h3 className="mobile-card-header">Data e Local</h3>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: "8px",
              alignItems: "flex-start",
              color: "#334155",
              fontSize: "14px",
            }}
          >
            <CalendarIcon
              size={18}
              style={{
                color: "#64748b",
                marginTop: "2px",
                flexShrink: 0,
              }}
            />

            <div>
              <strong>{formatDateBR(agenda.date) || agenda.date}</strong>

              {(timeStr || endTimeStr) && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    marginTop: "4px",
                    color: "#475569",
                  }}
                >
                  <Clock size={14} />
                  {timeStr}
                  {endTimeStr ? ` às ${endTimeStr}` : ""}
                </div>
              )}
            </div>
          </div>

          {(agenda.institution_location || agenda.location) && (
            <div
              style={{
                display: "flex",
                gap: "8px",
                alignItems: "flex-start",
                color: "#334155",
                fontSize: "14px",
              }}
            >
              <Building2
                size={18}
                style={{
                  color: "#64748b",
                  marginTop: "2px",
                  flexShrink: 0,
                }}
              />
              <div>
                <strong>Instituição / Local</strong>
                <div style={{ marginTop: "3px", color: "#475569" }}>
                  {agenda.institution_location || agenda.location}
                </div>
              </div>
            </div>
          )}

          {fullAddress && (
            <div
              style={{
                display: "flex",
                gap: "8px",
                alignItems: "flex-start",
                color: "#334155",
                fontSize: "14px",
                marginTop: "4px",
              }}
            >
              <MapPin
                size={18}
                style={{
                  color: "#64748b",
                  marginTop: "2px",
                  flexShrink: 0,
                }}
              />

              <div>
                <strong>Endereço</strong>
                <span
                  style={{
                    display: "block",
                    lineHeight: "1.4",
                    marginTop: "3px",
                  }}
                >
                  {fullAddress}
                </span>

                <a
                  href={`https://maps.google.com/?q=${encodeURIComponent(
                    fullAddress
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-block",
                    marginTop: "8px",
                    color: "#0a1e44",
                    fontSize: "13px",
                    fontWeight: "600",
                    textDecoration: "none",
                    backgroundColor: "#f1f5f9",
                    padding: "6px 12px",
                    borderRadius: "6px",
                  }}
                >
                  Abrir no Mapa
                </a>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Solicitação / Atividade */}
      {hasRequestActivityInfo && (
        <div className="mobile-card">
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <FileText size={18} /> Solicitação / Atividade
          </h3>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "14px",
              color: "#334155",
            }}
          >
            {agenda.requester_entity_type && (
              <p style={{ margin: 0 }}>
                <strong>Tipo de entidade:</strong>{" "}
                {requesterTypeLabel(agenda.requester_entity_type)}
              </p>
            )}

            <p style={{ margin: 0 }}>
              <strong>Modalidade:</strong> {agendaActionType(agenda)}
            </p>

            {agenda.travel_displacement !== undefined &&
              agenda.travel_displacement !== null && (
                <p style={{ margin: 0 }}>
                  <strong>Deslocamento de viagem:</strong>{" "}
                  {agenda.travel_displacement ? "Sim" : "Não"}
                </p>
              )}

            {agenda.audience && (
              <p style={{ margin: 0 }}>
                <strong>Público-alvo:</strong> {agenda.audience}
              </p>
            )}

            {agenda.age_ranges && (
              <p style={{ margin: 0 }}>
                <strong>Faixa etária:</strong>{" "}
                {Array.isArray(agenda.age_ranges)
                  ? agenda.age_ranges.join(", ")
                  : agenda.age_ranges}
              </p>
            )}

            {(agenda.participant_range || agenda.quantity) && (
              <p style={{ margin: 0 }}>
                <strong>Participantes / Público estimado:</strong>{" "}
                {agenda.participant_range || agenda.quantity}
              </p>
            )}

            {isStreetAction && streetActionDetails.length > 0 && (
              <div style={{ marginTop: "4px" }}>
                <strong>Ações previstas na OS:</strong>
                <ul
                  style={{
                    margin: "6px 0 0",
                    paddingLeft: "20px",
                    color: "#475569",
                  }}
                >
                  {streetActionDetails.map((detail, index) => (
                    <li key={index} style={{ marginBottom: "4px" }}>
                      {detail?.type
                        ? streetActionTypeLabel(detail.type)
                        : `Ação ${index + 1}`}
                      {detail?.public
                        ? ` — público estimado: ${detail.public}`
                        : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Contato / Solicitante */}
      {(agenda.external_responsible ||
        agenda.external_responsible_phone ||
        agenda.external_email ||
        agenda.contact_email) && (
        <div className="mobile-card">
          <h3 className="mobile-card-header">Contato / Solicitante</h3>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "14px",
              color: "#334155",
            }}
          >
            {agenda.external_responsible && (
              <p style={{ margin: 0 }}>
                <strong>Responsável:</strong>{" "}
                {agenda.external_responsible}
              </p>
            )}

            {agenda.external_responsible_phone && (
              <div
                style={{
                  display: "flex",
                  gap: "6px",
                  alignItems: "center",
                  marginTop: "4px",
                }}
              >
                <Phone size={16} color="#64748b" />
                <a
                  href={`tel:${agenda.external_responsible_phone.replace(
                    /\D/g,
                    ""
                  )}`}
                  style={{
                    color: "#0a1e44",
                    textDecoration: "none",
                    fontWeight: "500",
                  }}
                >
                  {agenda.external_responsible_phone}
                </a>
              </div>
            )}

            {(agenda.external_email || agenda.contact_email) && (
              <div
                style={{
                  display: "flex",
                  gap: "6px",
                  alignItems: "center",
                }}
              >
                <Mail size={16} color="#64748b" />
                <a
                  href={`mailto:${
                    agenda.external_email || agenda.contact_email
                  }`}
                  style={{
                    color: "#0a1e44",
                    textDecoration: "none",
                    fontWeight: "500",
                    overflowWrap: "anywhere",
                  }}
                >
                  {agenda.external_email || agenda.contact_email}
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Equipe operacional */}
      {agenda.service_order_mode !== "DESIGNATED" && (
        <div className="mobile-card">
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Users size={18} /> Participantes (Equipe)
          </h3>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "14px",
              color: "#334155",
            }}
          >
            {(agenda.team_name || agenda.team_ref_name || agenda.sector_name) && (
              <p style={{ margin: 0 }}>
                <strong>Equipe:</strong>{" "}
                {agenda.team_name ||
                  agenda.team_ref_name ||
                  agenda.sector_name}
              </p>
            )}

            {chiefs.length > 0 && (
              <p style={{ margin: 0 }}>
                <strong>Chefe:</strong>{" "}
                {chiefs.join(" - ")}
              </p>
            )}

            {agenda.team_phone && (
              <p
                style={{
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Phone size={14} color="#64748b" />
                <a
                  href={`tel:${agenda.team_phone.replace(/\D/g, "")}`}
                  style={{
                    color: "#0a1e44",
                    textDecoration: "none",
                  }}
                >
                  {agenda.team_phone}
                </a>
              </p>
            )}

            {agents.length > 0 && (
              <div style={{ marginTop: "4px" }}>
                <strong>Agentes:</strong>
                <ul
                  style={{
                    margin: "4px 0 0",
                    paddingLeft: "20px",
                    color: "#475569",
                  }}
                >
                  {agents.map((agent, index) => (
                    <li key={index} style={{ marginBottom: "4px" }}>
                      {memberName(agent) || agent}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {supports.length > 0 && (
              <div style={{ marginTop: "4px" }}>
                <strong>Apoio:</strong>
                <ul
                  style={{
                    margin: "4px 0 0",
                    paddingLeft: "20px",
                    color: "#475569",
                  }}
                >
                  {supports.map((support, index) => (
                    <li key={index} style={{ marginBottom: "4px" }}>
                      {memberName(support) || support}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {staffWarning && (
              <p style={{ margin: 0, color: "#b45309", fontWeight: 600 }}>
                {staffWarning}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Participantes designados */}
      {agenda.service_order_mode === "DESIGNATED" &&
        designatedUsers.length > 0 && (
          <div className="mobile-card">
            <h3
              className="mobile-card-header"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <User size={18} /> Participantes Designados
            </h3>

            <ul
              style={{
                margin: 0,
                paddingLeft: "20px",
                fontSize: "14px",
                color: "#475569",
              }}
            >
              {designatedUsers.map((member, index) => (
                <li
                  key={member?.id || member?.user?.id || index}
                  style={{ marginBottom: "8px" }}
                >
                  <strong>{memberName(member) || "Usuário"}</strong>

                  {(member?.role_label ||
                    member?.role ||
                    member?.team_name ||
                    member?.sector_name) && (
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#64748b",
                        marginTop: "2px",
                      }}
                    >
                      {[
                        member.role_label || member.role,
                        member.team_name || member.sector_name,
                      ]
                        .filter(Boolean)
                        .join(" - ")}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

      {/* Viaturas */}
      {vehicles.length > 0 && (
        <div className="mobile-card">
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Car size={18} /> Viatura
          </h3>

          <ul
            style={{
              margin: 0,
              paddingLeft: "20px",
              fontSize: "14px",
              color: "#475569",
            }}
          >
            {vehicles.map((vehicle, index) => (
              <li key={index} style={{ marginBottom: "4px" }}>
                {vehicle}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Condições do local */}
      {hasAccessibilityInfo && (
        <div className="mobile-card">
          <h3 className="mobile-card-header">Condições do Local</h3>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "14px",
              color: "#334155",
            }}
          >
            {agenda.accessibility_access && (
              <p style={{ margin: 0 }}>
                <strong>Acessibilidade:</strong>{" "}
                {agenda.accessibility_access}
              </p>
            )}

            {agenda.has_ramps && (
              <p style={{ margin: 0 }}>
                <strong>Rampa:</strong> {agenda.has_ramps}
              </p>
            )}

            {agenda.has_elevators && (
              <p style={{ margin: 0 }}>
                <strong>Elevador:</strong> {agenda.has_elevators}
              </p>
            )}

            {agenda.has_accessible_bathrooms && (
              <p style={{ margin: 0 }}>
                <strong>Banheiro adaptado:</strong>{" "}
                {agenda.has_accessible_bathrooms}
              </p>
            )}

            {agenda.media_equipment && (
              <p style={{ margin: 0 }}>
                <strong>Equipamentos disponíveis:</strong>{" "}
                {agenda.media_equipment}
              </p>
            )}

            {agenda.image_authorization && (
              <p style={{ margin: 0 }}>
                <strong>Autorização de imagem:</strong>{" "}
                {agenda.image_authorization}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Materiais */}
      {(materials.length > 0 || agenda.kit_1) && (
        <div className="mobile-card">
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Package size={18} /> Materiais e Kits
          </h3>

          <div style={{ fontSize: "14px", color: "#475569" }}>
            {materials.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {["Dinâmica", "Material para distribuição", "Material de apoio"]
                  .map((category) => {
                    const rows = materials.filter(
                      (item) => materialCategory(item) === category
                    );

                    if (!rows.length) return null;

                    return (
                      <div key={category}>
                        <strong style={{ color: "#334155" }}>
                          {category}
                        </strong>
                        <ul
                          style={{
                            margin: "4px 0 0",
                            paddingLeft: "20px",
                          }}
                        >
                          {rows.map((item, index) => (
                            <li
                              key={item.id || `${category}-${index}`}
                              style={{ marginBottom: "4px" }}
                            >
                              {item.quantity !== null &&
                              item.quantity !== undefined &&
                              item.quantity !== ""
                                ? `${item.quantity}x `
                                : ""}
                              {materialName(item)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
              </div>
            )}

            {materials.length === 0 && (
              <>
                {agenda.kit_1 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_1_quantity}x {agenda.kit_1}{" "}
                    {agenda.material_1}
                  </p>
                )}
                {agenda.kit_2 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_2_quantity}x {agenda.kit_2}{" "}
                    {agenda.material_2}
                  </p>
                )}
                {agenda.kit_3 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_3_quantity}x {agenda.kit_3}{" "}
                    {agenda.material_3}
                  </p>
                )}
                {agenda.kit_4 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_4_quantity}x {agenda.kit_4}{" "}
                    {agenda.material_4}
                  </p>
                )}
                {agenda.kit_5 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_5_quantity}x {agenda.kit_5}{" "}
                    {agenda.material_5}
                  </p>
                )}
                {agenda.kit_6 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_6_quantity}x {agenda.kit_6}{" "}
                    {agenda.material_6}
                  </p>
                )}
                {agenda.kit_7 && (
                  <p style={{ margin: "4px 0" }}>
                    {agenda.kit_7_quantity}x {agenda.kit_7}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Descrição / Observações */}
      {(agenda.description || agenda.notes) && (
        <div className="mobile-card">
          <h3
            className="mobile-card-header"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <FileText size={18} /> Informações Complementares
          </h3>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              fontSize: "14px",
              color: "#475569",
              lineHeight: "1.5",
            }}
          >
            {agenda.description && (
              <div>
                <strong style={{ color: "#334155" }}>Descrição</strong>
                <p
                  style={{
                    margin: "4px 0 0",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {agenda.description}
                </p>
              </div>
            )}

            {agenda.notes && (
              <div>
                <strong style={{ color: "#334155" }}>Observações</strong>
                <p
                  style={{
                    margin: "4px 0 0",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {agenda.notes}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

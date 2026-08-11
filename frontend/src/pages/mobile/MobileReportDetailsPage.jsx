import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { api } from "../../api/client.js";
import { formatDateBR } from "../../utils/date.js";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileReportStatusBadge, { reportStatusLabel } from "../../components/mobile/MobileReportStatusBadge.jsx";

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function formatDateTime(value) {
  if (!hasValue(value)) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function serviceOrder(value) {
  if (!hasValue(value)) return "";
  return `OS ${String(value).padStart(4, "0")}`;
}

function FieldRow({ label, value }) {
  if (!hasValue(value)) return null;
  return (
    <div className="mobile-report-field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TextBlock({ label, value }) {
  if (!hasValue(value)) return null;
  return (
    <div className="mobile-report-text-block">
      <span>{label}</span>
      <p>{value}</p>
    </div>
  );
}

function Section({ title, children }) {
  const content = Array.isArray(children) ? children.filter(Boolean) : children;
  if (!content || (Array.isArray(content) && content.length === 0)) return null;
  return (
    <section className="mobile-card mobile-report-section">
      <h3 className="mobile-card-header">{title}</h3>
      {content}
    </section>
  );
}

function actionTitle(action, index) {
  return action.type_action || action.institution_name || action.place_action || `Acao ${index + 1}`;
}

function fullFormButtonText(status) {
  if (status === "DRAFT") return "Continuar preenchimento";
  if (status === "RETURNED") return "Abrir formulario";
  if (status === "APPROVED") return "Consultar na versao completa";
  return "Abrir na versao completa";
}

export default function MobileReportDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const abortControllerRef = useRef(null);

  const fetchReport = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    setLoading(true);
    setError("");

    try {
      const data = await api(`/education-reports/${id}/`, { signal, redirectOnUnauthorized: false });
      setReport(data);
    } catch (err) {
      if (err.name === "AbortError") return;
      const message = String(err.message || "");
      if (message.includes("permissao") || message.includes("permiss") || message.includes("403")) {
        setError("Voce nao possui permissao para consultar Relatorios Tecnicos.");
      } else if (message.includes("nao foi encontrado") || message.includes("404")) {
        setError("Relatorio Tecnico nao encontrado.");
      } else if (message.includes("Sessao") || message.includes("401")) {
        setError("Sessao expirada. Entre novamente para consultar Relatorios Tecnicos.");
      } else {
        setError(message || "Nao foi possivel carregar o Relatorio Tecnico.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [id]);

  if (loading) return <MobileLoadingState message="Carregando relatorio..." />;
  if (error) return <MobileErrorState message={error} onRetry={fetchReport} />;
  if (!report) return <MobileErrorState message="Relatorio Tecnico nao encontrado." />;

  const actions = Array.isArray(report.actions) ? report.actions : [];
  const materialFields = [
    ["Materiais retirados", report.materials_removed],
    ["Materiais utilizados", report.materials_spent],
    ["Equipamentos retirados", report.equipment_materials_removed],
    ["Equipamentos distribuidos", report.equipment_materials_distributed],
    ["Materiais de distribuicao retirados", report.distribution_materials_removed],
    ["Materiais de distribuicao distribuidos", report.distribution_materials_distributed],
    ["Etilometros", report.breathalyzers],
    ["Viaturas", report.cars],
  ].filter(([, value]) => hasValue(value));

  const hasStatisticsField = Object.prototype.hasOwnProperty.call(report, "statistics_processed");
  const statisticsText = report.statistics_processed
    ? `Processada${hasValue(report.statistics_processed_at) ? ` em ${formatDateTime(report.statistics_processed_at)}` : ""}`
    : "Aguardando processamento";

  return (
    <div className="mobile-report-details">
      <button type="button" onClick={() => navigate(-1)} className="mobile-back-btn">
        <ArrowLeft size={20} />
        Voltar
      </button>

      <div className="mobile-report-title-block">
        <MobileReportStatusBadge status={report.status} />
        <h2>{report.agenda_title || "Relatorio Tecnico"}</h2>
        {hasValue(report.agenda_location) && <p>{report.agenda_location}</p>}
      </div>

      <Section title="Identificacao">
        <FieldRow label="Data da operacao" value={formatDateBR(report.operation_date)} />
        <FieldRow label="Agenda" value={report.agenda_title} />
        <FieldRow label="Ordem de servico" value={serviceOrder(report.agenda_service_order_number)} />
        <FieldRow label="Equipe" value={report.team} />
        <FieldRow label="Status" value={reportStatusLabel(report.status)} />
        <FieldRow label="Criado em" value={formatDateTime(report.created_at)} />
        <FieldRow label="Ultima atualizacao" value={formatDateTime(report.updated_at)} />
      </Section>

      <Section title="Local e solicitacao">
        <FieldRow label="Local" value={report.agenda_location} />
        <FieldRow label="Solicitante / contato" value={report.contact_received} />
        <TextBlock label="Dados da solicitacao" value={report.request_details} />
        <TextBlock label="Observacoes gerais" value={report.general_observations} />
      </Section>

      <Section title="Participantes registrados">
        <TextBlock label="Gestao" value={report.management_name} />
        <TextBlock label="Agentes de Educacao" value={report.education_agents} />
        <TextBlock label="Alteracoes de efetivo" value={report.changes_staff} />
      </Section>

      <Section title="Acoes executadas">
        {actions.length ? (
          <div className="mobile-report-action-list">
            {actions.map((action, index) => (
              <article className="mobile-report-action" key={action.id || index}>
                <h4>{actionTitle(action, index)}</h4>
                <FieldRow label="Local" value={action.place_action} />
                <FieldRow label="Instituicao" value={action.institution_name} />
                <FieldRow label="Publico" value={action.type_audience} />
                <FieldRow label="Inicio" value={action.start_time} />
                <FieldRow label="Fim" value={action.final_hour} />
                <FieldRow label="Abordagens" value={action.approach || action.approached_actions} />
              </article>
            ))}
          </div>
        ) : (
          <p className="mobile-muted">Nenhuma acao registrada no relatorio.</p>
        )}
      </Section>

      <Section title="Materiais">
        {materialFields.length ? (
          materialFields.map(([label, value]) => <TextBlock key={label} label={label} value={value} />)
        ) : (
          <p className="mobile-muted">Nenhum material registrado no relatorio.</p>
        )}
      </Section>

      {report.status === "RETURNED" && hasValue(report.review_notes) && (
        <Section title="Devolucao">
          <TextBlock label="Observacao da conferencia" value={report.review_notes} />
        </Section>
      )}

      <Section title="Estatistica">
        <FieldRow label="Relatorio" value={reportStatusLabel(report.status)} />
        {hasStatisticsField && <FieldRow label="Estatistica" value={statisticsText} />}
      </Section>

      <div className="mobile-card mobile-report-full-form">
        <p>Voce saira do modo aplicativo para abrir a versao completa do Relatorio Tecnico.</p>
        <button
          type="button"
          className="mobile-btn mobile-btn-primary"
          onClick={() => {
            if (report.status === "DRAFT" || report.status === "RETURNED") {
              navigate(`/app/relatorios/${report.id}/editar`);
              return;
            }
            navigate(`/relatorio-tecnico?openReport=${encodeURIComponent(report.id)}`);
          }}
        >
          <ExternalLink size={18} />
          {fullFormButtonText(report.status)}
        </button>
      </div>
    </div>
  );
}

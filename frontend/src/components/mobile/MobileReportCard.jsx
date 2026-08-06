import { CalendarDays, ChevronRight, ClipboardList, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { formatDateBR } from "../../utils/date.js";
import MobileReportStatusBadge from "./MobileReportStatusBadge.jsx";

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function serviceOrder(value) {
  if (!hasValue(value)) return "";
  return `OS ${String(value).padStart(4, "0")}`;
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

export default function MobileReportCard({ report }) {
  const title = report.agenda_title || "Relatorio tecnico";
  const order = serviceOrder(report.agenda_service_order_number);
  const updatedAt = formatDateTime(report.updated_at);

  return (
    <article className="mobile-report-card">
      <div className="mobile-report-card-top">
        <MobileReportStatusBadge status={report.status} />
        {report.statistics_processed === true && (
          <span className="mobile-report-stat-chip">Estatistica processada</span>
        )}
      </div>

      <h3>{title}</h3>

      <div className="mobile-report-meta">
        {hasValue(report.operation_date) && (
          <span>
            <CalendarDays size={16} />
            {formatDateBR(report.operation_date)}
          </span>
        )}
        {order && (
          <span>
            <ClipboardList size={16} />
            {order}
          </span>
        )}
        {hasValue(report.team) && <span>Equipe {report.team}</span>}
        {hasValue(report.agenda_location) && (
          <span>
            <MapPin size={16} />
            {report.agenda_location}
          </span>
        )}
        {updatedAt && <span>Atualizado em {updatedAt}</span>}
      </div>

      <Link to={`/app/relatorios/${report.id}`} className="mobile-report-card-link">
        Ver relatorio
        <ChevronRight size={18} />
      </Link>
    </article>
  );
}

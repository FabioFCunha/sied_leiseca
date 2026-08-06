const STATUS_LABELS = {
  DRAFT: "Rascunho",
  PENDING_REVIEW: "Enviado / Aguardando Conferência",
  APPROVED: "Aprovado",
  RETURNED: "Devolvido",
};

const STATUS_CLASSES = {
  DRAFT: "mobile-report-status-draft",
  PENDING_REVIEW: "mobile-report-status-pending",
  APPROVED: "mobile-report-status-approved",
  RETURNED: "mobile-report-status-returned",
};

export function reportStatusLabel(status) {
  return STATUS_LABELS[status] || "Status não identificado";
}

export default function MobileReportStatusBadge({ status }) {
  return (
    <span className={`mobile-report-status ${STATUS_CLASSES[status] || "mobile-report-status-unknown"}`}>
      {reportStatusLabel(status)}
    </span>
  );
}

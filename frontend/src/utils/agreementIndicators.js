export const REQUESTER_ENTITY_KIND_OPTIONS = [
  { value: "SCHOOL", label: "Instituição de Ensino" },
  { value: "BUSINESS", label: "Empresa" },
  { value: "MILITARY", label: "Órgão Militar" },
  { value: "PUBLIC", label: "Órgão Público" },
  { value: "OTHER", label: "Outros" },
];

export const REQUESTER_ENTITY_NATURE_OPTIONS = [
  { value: "PUBLIC", label: "Pública" },
  { value: "PRIVATE", label: "Privada" },
];

export const EDUCATION_ACTION_AGE_RANGE_OPTIONS = [
  { value: "AGE_05_10", label: "05 - 10 anos (ensino fundamental - anos iniciais)" },
  { value: "AGE_11_14", label: "11 - 14 anos (ensino fundamental - anos finais)" },
  { value: "AGE_15_17", label: "15 - 17 anos (ensino médio)" },
  { value: "AGE_ADULT", label: "acima de 18 anos - Adultos" },
];

const AGE_LABEL_TO_VALUE = new Map(
  EDUCATION_ACTION_AGE_RANGE_OPTIONS.map((option) => [option.label.toLocaleLowerCase("pt-BR"), option.value])
);

function normalizedText(value) {
  return String(value || "").trim().toLocaleLowerCase("pt-BR");
}

export function agreementIndicatorLabel(value) {
  return value === "ESCOLINHA_NOTA_10"
    ? "Escolinha Nota 10"
    : value === "ESCOLA_NOTA_10"
      ? "Escola Nota 10"
      : "";
}

export function requesterEntityKindLabel(value) {
  return REQUESTER_ENTITY_KIND_OPTIONS.find((option) => option.value === value)?.label || value || "";
}

export function requesterEntityNatureLabel(value) {
  return REQUESTER_ENTITY_NATURE_OPTIONS.find((option) => option.value === value)?.label || value || "";
}

export function ageRangeLabel(value) {
  return EDUCATION_ACTION_AGE_RANGE_OPTIONS.find((option) => option.value === value)?.label || value || "";
}

export function normalizeAgeRange(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (EDUCATION_ACTION_AGE_RANGE_OPTIONS.some((option) => option.value === text)) return text;
  return AGE_LABEL_TO_VALUE.get(normalizedText(text)) || "";
}

export function normalizeRequesterEntityType(value) {
  const text = String(value || "").trim();
  if (!text) return { kind: "", nature: "" };
  if (REQUESTER_ENTITY_KIND_OPTIONS.some((option) => option.value === text)) return { kind: text, nature: "" };

  const lower = normalizedText(text);
  if (text === "2" || lower.includes("instituição de ensino") || lower.includes("instituicao de ensino") || lower.includes("escola") || lower.includes("colégio") || lower.includes("colegio")) {
    const nature = lower.includes("públic") || lower.includes("public") ? "PUBLIC" : lower.includes("privad") || lower.includes("particular") ? "PRIVATE" : "";
    return { kind: "SCHOOL", nature };
  }
  if (text === "4" || lower.includes("empresa")) return { kind: "BUSINESS", nature: "" };
  if (lower.includes("militar")) return { kind: "MILITARY", nature: "" };
  if (text === "1" || lower.includes("órgão") || lower.includes("orgao")) return { kind: "PUBLIC", nature: "" };
  return { kind: "", nature: "" };
}

export function deriveEducationAgreementIndicator(kind, nature, ageRange) {
  const normalizedAge = normalizeAgeRange(ageRange);
  if (kind !== "SCHOOL" || nature !== "PUBLIC" || !normalizedAge) return "";
  if (normalizedAge === "AGE_05_10" || normalizedAge === "AGE_11_14") return "ESCOLINHA_NOTA_10";
  if (normalizedAge === "AGE_15_17" || normalizedAge === "AGE_ADULT") return "ESCOLA_NOTA_10";
  return "";
}

export function deriveAgreementIndicatorFromAgenda(agenda) {
  const { kind, nature } = normalizeRequesterEntityType(agenda?.requester_entity_type);
  return deriveEducationAgreementIndicator(kind, nature, normalizeAgeRange(agenda?.age_ranges));
}

export function buildAgreementFieldsFromAgenda(agenda) {
  const { kind, nature } = normalizeRequesterEntityType(agenda?.requester_entity_type);
  return {
    requester_entity_kind: kind,
    requester_entity_nature: nature,
    age_range: normalizeAgeRange(agenda?.age_ranges),
  };
}

export function getDisplayedAgreementIndicator(action = {}, agenda = null, index = 0) {
  const actionIndicator = action.agreement_indicator || deriveEducationAgreementIndicator(
    action.requester_entity_kind,
    action.requester_entity_nature,
    action.age_range
  );
  if (actionIndicator) return actionIndicator;
  const hasActionFields = Boolean(action.requester_entity_kind || action.requester_entity_nature || action.age_range);
  if (index === 0 && !hasActionFields) return deriveAgreementIndicatorFromAgenda(agenda);
  return "";
}

import { STREET_ACTION_ID } from "./constants.js";
import {
  buildAgreementFieldsFromAgenda,
  normalizeAgeRange,
  normalizeRequesterEntityNature,
  normalizeRequesterEntityType,
} from "./agreementIndicators.js";
import { getAgendaOperationalActionTypeName } from "./actionTypeOptions.js";

const legacyStreetActionTypeMap = {
  BAR: "Bares",
  EMPRESA: "Empresas",
  ESCOLA: "Escolas",
  ESPORTES: "Praças Esportivas",
  EVENTO: "Eventos",
  FESTA_BAIRRO: "Eventos",
  PARQUE: "Praças/Parques Públicos",
  PEDAGIO: "Pedágio",
  PRAIA: "Praia",
  SHOPPING: "Shopping/Centro Comerciais",
  UNIVERSIDADE: "Universidades",
  PONTO_TURISTICO: "Pontos turísticos",
  SINDICATO: "Outros",
};

export function normalizeStreetActionType(value) {
  const normalized = String(value || "").trim();
  return legacyStreetActionTypeMap[normalized] || normalized;
}

function normalizedType(value) {
  return String(value || "").trim().toLocaleLowerCase("pt-BR");
}

export function isStreetActionAgenda(agenda) {
  return [agenda?.action_type_ref, agenda?.requester_entity_type, agenda?.action_type_ref_name]
    .some((value) => {
      const type = normalizedType(value);
      return String(value) === STREET_ACTION_ID || type === "ação de rua" || type === "acao de rua";
    });
}

export function getAgendaActionPlace(agenda = {}) {
  const fullAddress = [
    agenda.address,
    agenda.neighborhood || agenda.neighborhood_ref_name,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
  ].filter(Boolean).join(", ");

  return fullAddress || agenda.location || agenda.institution_location || "";
}

// Only source values from the agenda. Callers merge these fields into blank actions,
// so saved drafts and values entered by the chief always take precedence.
export function buildFirstActionAgendaPrefill(agenda = {}, actionTypes = []) {
  const isStreetAction = isStreetActionAgenda(agenda);
  const agreementFields = isStreetAction
    ? {
      requester_entity_kind: normalizeRequesterEntityType(agenda.requester_entity_kind).kind,
      requester_entity_nature: normalizeRequesterEntityNature(agenda.requester_entity_nature),
      age_range: normalizeAgeRange(agenda.age_range || agenda.age_ranges),
    }
    : buildAgreementFieldsFromAgenda(agenda);
  const streetActionType = (agenda.street_action_details || [])
    .map((detail) => detail?.type)
    .find(Boolean) || agenda.action_type_ref_name || agenda.action_type || "";

  return {
    action_mode: isStreetAction ? "STREET" : "LECTURE",
    place_action: getAgendaActionPlace(agenda),
    institution_name: agenda.institution_location || agenda.location || "",
    type_action: isStreetAction
      ? normalizeStreetActionType(streetActionType)
      : getAgendaOperationalActionTypeName(agenda, actionTypes),
    type_audience: agenda.audience || "",
    requester_entity_kind: agreementFields.requester_entity_kind || "",
    // This uses only the structured API field (when present); it never derives
    // Public/Private from the street-action label.
    requester_entity_nature: agreementFields.requester_entity_nature || "",
    age_range: agreementFields.age_range || "",
    start_time: agenda.start_time?.slice?.(0, 5) || "",
    final_hour: agenda.end_time?.slice?.(0, 5) || "",
    // Estimated audience is not an executed number of approaches. Street actions
    // must therefore start blank for the chief to record the real result.
    approach: isStreetAction ? "" : (agenda.quantity || 0),
  };
}

export function applyBlankActionPrefill(action = {}, prefill = {}) {
  return Object.fromEntries(
    Object.entries(prefill).map(([field, value]) => [
      field,
      action[field] !== undefined && action[field] !== null && action[field] !== ""
        ? action[field]
        : value,
    ])
  );
}

// Fields rendered as read-only for the action inherited from the OS must reflect
// the current OS. All other fields keep the saved report value so corrections do
// not erase the chief's operational data.
export function applyAgendaOwnedActionPrefill(action = {}, prefill = {}) {
  const merged = applyBlankActionPrefill(action, prefill);
  return {
    ...action,
    ...merged,
    institution_name: prefill.institution_name || merged.institution_name || "",
    place_action: prefill.place_action || merged.place_action || "",
  };
}

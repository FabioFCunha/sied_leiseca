import { formatDateBR } from "./date.js";


export function reportName(report) {
  return `Relat\u00F3rio - ${report.team || "Equipe"}`;
}

export function chiefFromReport(report) {
  const match = String(report.education_agents || "").match(/Chefe(?: respons[\u00E1a]vel)?:\s*([^\n]+)/i);
  return match?.[1]?.trim() || "";
}

function agentsFromReport(report) {
  return report.education_agents ? report.education_agents.match(/Agentes?:\s*([^\n]+)/i)?.[1]?.trim() || "" : "";
}

function phoneFromReport(report) {
  const match = String(report.education_agents || "").match(/Telefone do chefe\/equipe:\s*([^\n]+)/i);
  return match?.[1]?.trim() || "";
}

function uniqueNames(values = []) {
  const unique = [];
  const normalizedSeen = new Set();

  values.forEach((value) => {
    const name = String(value || "").trim();
    const normalized = name.toLocaleLowerCase("pt-BR");
    if (name && !normalizedSeen.has(normalized)) {
      normalizedSeen.add(normalized);
      unique.push(name);
    }
  });

  return unique;
}

function memberNames(items = []) {
  return uniqueNames(items.map((item) => item?.name));
}

function hasEffectiveMembers(effectiveMembers) {
  if (!effectiveMembers) return false;
  return ["chiefs", "agents", "supports"].some((group) => Array.isArray(effectiveMembers[group]) && effectiveMembers[group].length > 0);
}

export function getReachedAudienceForAction(action, index) {
  if (!action) return undefined;
  if (index === 0) {
    const lectures = action.approached_lectures;
    const hasLectures =
      lectures !== "" &&
      lectures !== null &&
      lectures !== undefined &&
      Number(lectures) > 0;

    if (hasLectures) {
      return lectures;
    }
    return action.approached_actions;
  }
  return action.approached_actions;
}

export function getSupports(report, selectedAgenda, effectiveMembers) {
  if (hasEffectiveMembers(effectiveMembers)) {
    return memberNames(effectiveMembers.supports || []);
  }

  const supportsList = [];

  if (selectedAgenda) {
    if (selectedAgenda.support_1 && selectedAgenda.support_1.trim()) {
      supportsList.push(selectedAgenda.support_1.trim());
    }
    if (selectedAgenda.support_2 && selectedAgenda.support_2.trim()) {
      supportsList.push(selectedAgenda.support_2.trim());
    }
  }

  if (report && report.education_agents) {
    const lines = String(report.education_agents).split("\n");
    lines.forEach((line) => {
      const match = line.match(/^(?:Apoio\s*[12]?|Apoios?)(?:\s*operacional)?:\s*(.+)$/i);
      if (match) {
        const val = match[1].trim();
        if (val) {
          supportsList.push(val);
        }
      }
    });
  }
  
  return uniqueNames(supportsList);
}

export function buildEducationAgentsText(report, selectedAgenda, effectiveMembers) {
  if (!hasEffectiveMembers(effectiveMembers)) {
    return report?.education_agents || "";
  }

  const chief = memberNames(effectiveMembers.chiefs || [])[0] || "";
  const phone = String(selectedAgenda?.team_phone || phoneFromReport(report)).trim();
  const agents = memberNames(effectiveMembers.agents || []);
  const supports = memberNames(effectiveMembers.supports || []);
  const lines = [];

  if (chief) lines.push(`Chefe respons\u00E1vel: ${chief}`);
  if (phone) lines.push(`Telefone do chefe/equipe: ${phone}`);
  if (agents.length) lines.push(`Agentes: ${agents.join(" - ")}`);
  supports.forEach((support, index) => {
    lines.push(`Apoio ${index + 1}: ${support}`);
  });

  return lines.join("\n");
}

export function buildOperationalResponsibility(report, selectedAgenda, effectiveMembers) {
  const chief = hasEffectiveMembers(effectiveMembers)
    ? memberNames(effectiveMembers.chiefs || [])[0] || ""
    : chiefFromReport(report);
  const agentsSummary = hasEffectiveMembers(effectiveMembers)
    ? memberNames(effectiveMembers.agents || []).join(" - ")
    : agentsFromReport(report);
  const supports = getSupports(report, selectedAgenda, effectiveMembers);

  return {
    chief,
    agentsSummary,
    supports,
    supportsSummary: supports.join(" - "),
    educationAgentsText: buildEducationAgentsText(report, selectedAgenda, effectiveMembers),
  };
}

export function buildSupportsSummary(report, selectedAgenda, effectiveMembers) {
  return getSupports(report, selectedAgenda, effectiveMembers).join(" - ");
}

export function buildPreview(report, selectedAgendaOrShowEstimatedPublic = true, maybeShowEstimatedPublic = true, maybeEffectiveMembers) {
  let selectedAgenda = selectedAgendaOrShowEstimatedPublic;
  let showEstimatedPublic = maybeShowEstimatedPublic;
  let effectiveMembers = maybeEffectiveMembers;

  if (typeof selectedAgendaOrShowEstimatedPublic === "boolean" || selectedAgendaOrShowEstimatedPublic === undefined) {
    selectedAgenda = undefined;
    showEstimatedPublic = selectedAgendaOrShowEstimatedPublic ?? true;
    effectiveMembers = maybeShowEstimatedPublic;
  }

  const actions = report.actions || [];
  const responsibility = buildOperationalResponsibility(report, selectedAgenda, effectiveMembers);

  let totalsEstimado = 0;
  let totalsAlcancado = 0;

  actions.forEach((action, index) => {
    // P\u00FAblico Estimado: somente A\u00E7\u00E3o 1
    if (index === 0) {
      totalsEstimado += Number(action.approach || 0);
    }
    // P\u00FAblico Alcan\u00E7ado: approached_lectures na A\u00E7\u00E3o 1, approached_actions nas extras
    const alcVal = getReachedAudienceForAction(action, index);
    const alcNum = Number(alcVal);
    totalsAlcancado += (alcVal !== "" && alcVal !== null && alcVal !== undefined && Number.isFinite(alcNum)) ? alcNum : 0;
  });

  const taxaText = totalsEstimado > 0
    ? `${((totalsAlcancado / totalsEstimado) * 100).toFixed(1)}%`
    : "N/A";

  const actionLines = actions.length
    ? actions.map((action, index) => {
        const isFirstAction = index === 0;
        const alcVal = getReachedAudienceForAction(action, index);
        const alcDisplay = (alcVal !== "" && alcVal !== null && alcVal !== undefined)
          ? alcVal
          : "N\u00E3o informado";

        const estimadoLine = (isFirstAction && showEstimatedPublic)
          ? `   P\u00FAblico estimado: ${action.approach || 0}\n`
          : "";

        return (
          `${index + 1}. ${action.type_action || "A\u00E7\u00E3o"} - ${action.institution_name || action.place_action || "local n\u00E3o informado"}\n` +
          `   Institui\u00E7\u00E3o/Local: ${action.institution_name || "n\u00E3o informado"}\n` +
          `   Endere\u00E7o do Local: ${action.place_action || "n\u00E3o informado"}\n` +
          `   P\u00FAblico: ${action.type_audience || "n\u00E3o informado"}\n` +
          `   Hor\u00E1rio: ${action.start_time || "--"} \u00E0s ${action.final_hour || "--"}\n` +
          estimadoLine +
          `   P\u00FAblico alcan\u00E7ado: ${alcDisplay}\n` +
          `   Din\u00E2mica retirada: ${action.equipment_materials_removed ? action.equipment_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Din\u00E2mica distribu\u00EDda: ${action.equipment_materials_distributed ? action.equipment_materials_distributed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Material para distribui\u00E7\u00E3o retirado: ${action.distribution_materials_removed ? action.distribution_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Material para distribui\u00E7\u00E3o distribu\u00EDdo: ${action.distribution_materials_distributed ? action.distribution_materials_distributed.replace(/\\n/g, ", ") : "-"}`
        );
      }).join("\n\n")
    : "Nenhuma a\u00E7\u00E3o registrada.";

  return (
    `${reportName(report).toUpperCase()}\n\n` +
    `Protocolo: ${report.agenda ? "#" + report.agenda : "n\u00E3o informado"}\n` +
    `Solicita\u00E7\u00E3o: ${report.agenda_title || "n\u00E3o informada"}\n` +
    `Data: ${report.operation_date ? formatDateBR(report.operation_date) : "n\u00E3o informada"}\n` +
    `Equipe: ${report.team || "n\u00E3o informada"}\n` +
    `Chefe respons\u00E1vel: ${responsibility.chief || "n\u00E3o informado"}\n` +
    `Telefone do solicitante: ${report.agenda_phone || "n\u00E3o informado"}\n` +
    "\n" +
    `EFETIVO E ESTRUTURA\n` +
    `Agentes de educa\u00E7\u00E3o: ${responsibility.agentsSummary || "n\u00E3o informado"}\n` +
    `Apoios: ${responsibility.supportsSummary || "N\u00E3o informado"}\n` +
    `Etil\u00F4metros: ${report.breathalyzers || "n\u00E3o informado"}\n` +
    `Viaturas: ${report.cars || "n\u00E3o informado"}\n` +
    `Altera\u00E7\u00F5es gerais: ${report.changes_general || "n\u00E3o informado"}\n\n` +
    (report.changes_staff && report.changes_staff.trim()
      ? `ALTERA\u00C7\u00D5ES DE EFETIVO\n${report.changes_staff}\n\n`
      : "") +
    `A\u00C7\u00D5ES\n${actionLines}\n\n` +
    `TOTAIS\n` +
    (showEstimatedPublic ? `P\u00FAblico estimado (total): ${totalsEstimado}\n` : "") +
    `P\u00FAblico alcan\u00E7ado (total): ${totalsAlcancado}\n` +
    `Taxa de Alcance: ${taxaText}\n` +
    `A\u00E7\u00F5es Realizadas: ${actions.length}\n\n` +
    `RELATO OPERACIONAL DO CHEFE\n` +
    `${report.general_observations || "N\u00E3o informado"}\n\n` +
    `CONTATO/OCORR\u00CANCIAS\n` +
    `Contato recebido: ${report.contact_received || "n\u00E3o informado"}\n` +
    `Observa\u00E7\u00E3o de ocorr\u00EAncia: ${report.occurrence_observation || "n\u00E3o informado"}\n` +
    `Coordenadas: ${report.lat || "-"}, ${report.lng || "-"}` +
    (report.satisfaction_survey ? (() => {
      const survey = report.satisfaction_survey;
      const scores = [
        Number(survey.overall_rating),
        Number(survey.punctuality),
        Number(survey.team_enthusiasm),
        Number(survey.speaker_knowledge),
        Number(survey.workshops),
        Number(survey.audiovisual_resources),
        Number(survey.support_material)
      ].filter(val => !isNaN(val) && val > 0);
      const avg = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "N\u00E3o avaliado";
      
      return `\n\n========================================\n` +
      `PESQUISA DE SATISFA\u00C7\u00C3O (Respondida em: ${survey.answered_at ? formatDateBR(survey.answered_at.split("T")[0]) : "-"} ${survey.answered_at ? survey.answered_at.split("T")[1].slice(0, 5) : ""})\n` +
      `========================================\n` +
      `M\u00E9dia de satisfa\u00E7\u00E3o: ${avg === "N\u00E3o avaliado" ? avg : `${avg}/5`}\n` +
      `Avalia\u00E7\u00E3o geral: ${survey.overall_rating ? `${survey.overall_rating}/5` : "N\u00E3o avaliado"}\n` +
      `Pontualidade da equipe: ${survey.punctuality ? `${survey.punctuality}/5` : "N\u00E3o avaliado"}\n` +
      `Entusiasmo e dinamismo: ${survey.team_enthusiasm ? `${survey.team_enthusiasm}/5` : "N\u00E3o avaliado"}\n` +
      `Dom\u00EDnio do palestrante: ${survey.speaker_knowledge ? `${survey.speaker_knowledge}/5` : "N\u00E3o avaliado"}\n` +
      `Oficinas / Din\u00E2micas: ${survey.workshops ? `${survey.workshops}/5` : "N\u00E3o avaliado"}\n` +
      `Recursos audiovisuais: ${survey.audiovisual_resources ? `${survey.audiovisual_resources}/5` : "N\u00E3o avaliado"}\n` +
      `Material de apoio: ${survey.support_material ? `${survey.support_material}/5` : "N\u00E3o avaliado"}\n` +
      `Sugest\u00F5es / Coment\u00E1rios:\n"${survey.suggestion || "Nenhum coment\u00E1rio enviado."}"`;
    })() : "")
  );
}

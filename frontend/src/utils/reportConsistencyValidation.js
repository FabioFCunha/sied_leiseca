function timeToMinutes(value) {
  const match = String(value || "").trim().match(/^(\d{1,2})(?::|h)(\d{2})$/i);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour > 23 || minute > 59) return null;
  return hour * 60 + minute;
}

function materialRows(value) {
  return String(value || "").split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const normalized = line.replace(/\[\s*\]/g, "| 0").replace(/\s+-\s+/g, " | ");
    const parts = normalized.split("|");
    const name = String(parts[0] || "").trim();
    const quantity = Number(String(parts.at(-1) || "").match(/\d+/)?.[0] || 0);
    return { name, quantity };
  }).filter(({ name }) => name);
}

function isKit(name) {
  return String(name || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z0-9]+/).includes("kit");
}

export function getReportConsistencyErrors(actions = []) {
  const errors = [];
  const intervals = [];

  actions.forEach((action, index) => {
    const lectures = Math.max(0, Number(action?.approached_lectures || 0));
    const audience = index === 0 && lectures > 0
      ? lectures
      : Math.max(0, Number(action?.approached_actions || 0));

    materialRows(action?.distribution_materials_distributed).forEach(({ name, quantity }) => {
      if (isKit(name) && quantity > audience) {
        errors.push(`Ação ${index + 1}: a quantidade de "${name}" distribuída (${quantity}) não pode ser maior que o público alcançado (${audience}).`);
      }
    });

    const start = timeToMinutes(action?.start_time);
    const end = timeToMinutes(action?.final_hour);
    if (start === null || end === null) return;
    intervals.push({ start, end: end <= start ? end + (24 * 60) : end, index });
  });

  intervals.forEach((current, position) => {
    for (const next of intervals.slice(position + 1)) {
      const overlaps = [-24 * 60, 0, 24 * 60].some((shift) => (
        current.start < next.end + shift && next.start + shift < current.end
      ));
      if (overlaps) {
        errors.push(`Ação ${next.index + 1}: o horário informado conflita com a Ação ${current.index + 1}. As atividades do mesmo relatório não podem ocorrer em horários sobrepostos.`);
      }
    }
  });

  return errors;
}

export function assertReportConsistency(actions) {
  const errors = getReportConsistencyErrors(actions);
  if (errors.length) {
    throw new Error(`Corrija as inconsistências das ações antes de continuar:\n${errors.map((error) => `- ${error}`).join("\n")}`);
  }
}

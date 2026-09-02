function memberName(member) {
  if (!member) return "";
  if (typeof member === "string") return member.trim();
  if (typeof member.name === "string" && member.name.trim()) return member.name.trim();
  if (typeof member.full_name === "string" && member.full_name.trim()) return member.full_name.trim();
  return "";
}

function uniqueNames(items = []) {
  const seen = new Set();
  const names = [];
  for (const item of items) {
    const name = memberName(item);
    if (!name) continue;
    const key = name.toLocaleLowerCase("pt-BR");
    if (seen.has(key)) continue;
    seen.add(key);
    names.push(name);
  }
  return names;
}

export function getAgendaEffectiveStaff(agenda) {
  if (agenda?.service_order_mode === "DESIGNATED") {
    return {
      chiefs: [],
      agents: [],
      supports: [],
      manual: [],
    };
  }
  if (agenda?.effective_staff) {
    return agenda.effective_staff;
  }
  return {
    chiefs: uniqueNames([agenda?.chief_ref_name, agenda?.chief_name]).map((name) => ({ name })),
    agents: uniqueNames(
      Array.isArray(agenda?.agents)
        ? agenda.agents
        : String(agenda?.agents || "")
            .split(/\s+-\s+|,\s*/)
            .filter(Boolean)
    ).map((name) => ({ name })),
    supports: uniqueNames([
      agenda?.support_1_ref_name,
      agenda?.support_1,
      agenda?.support_2_ref_name,
      agenda?.support_2,
    ]).map((name) => ({ name })),
    manual: [],
  };
}

export function getAgendaChiefNames(agenda) {
  return uniqueNames(getAgendaEffectiveStaff(agenda)?.chiefs || []);
}

export function getAgendaAgentNames(agenda) {
  return uniqueNames(getAgendaEffectiveStaff(agenda)?.agents || []);
}

export function getAgendaSupportNames(agenda) {
  return uniqueNames(getAgendaEffectiveStaff(agenda)?.supports || []);
}

export function getAgendaStaffWarning(agenda) {
  return String(agenda?.effective_staff_warning || "").trim();
}

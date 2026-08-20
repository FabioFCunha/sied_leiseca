function memberRows(members = {}) {
  return [
    ...(members.chiefs || []).map((item) => ({ ...item, type: "CHIEF" })),
    ...(members.agents || []).map((item) => ({ ...item, type: "AGENT" })),
    ...(members.supports || []).map((item) => ({ ...item, type: "SUPPORT" })),
  ];
}

export function buildStaffChanges(schedule = {}) {
  const changes = [];
  memberRows(schedule.members).forEach((member) => {
    if (member.is_extra) changes.push(`Extra: ${member.name}`);
    if (member.is_swap) changes.push(`Troca: ${member.name} (no lugar de ${member.swap_for})`);
  });

  const removedIds = {
    CHIEF: schedule.removed_chiefs || [],
    AGENT: schedule.removed_agents || [],
    SUPPORT: schedule.removed_supports || [],
  };
  (schedule.member_changes || []).forEach((change) => {
    if (change.action === "REMOVED" && removedIds[change.member_type]?.includes(change.member_id)) {
      changes.push(`Retirado: ${change.member_name}`);
    }
  });
  return [...new Set(changes)];
}

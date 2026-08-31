export function buildShiftScheduleDetailUrl(scheduleId, agendaId) {
  const agendaQuery = agendaId ? `?agenda=${encodeURIComponent(agendaId)}` : "";
  return `/shift-schedules/${scheduleId}/${agendaQuery}`;
}

export function buildTeamAttendanceForm(members = {}) {
  const form = {};
  const groups = [
    [members.chiefs, "CHIEF", "Chefe"],
    [members.agents, "AGENT", "Agente"],
    [members.supports, "SUPPORT", "Apoio"],
  ];

  groups.forEach(([group, memberType, roleLabel]) => {
    if (!Array.isArray(group)) return;

    group.forEach((member) => {
      const key = `${memberType}_${member.id}`;
      if (form[key]) return;

      form[key] = {
        member_type: memberType,
        member_id: member.id,
        name: member.full_name || member.name,
        roleLabel,
        is_absent: member.is_absent,
        reason: member.absence_reason || "",
        attachment: null,
      };
    });
  });

  return form;
}

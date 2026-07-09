import { AlertTriangle, CalendarDays, Check, ChevronLeft, ChevronRight, Paperclip, Repeat2, Trash2, X, AlertCircle, CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateBR } from "../utils/date.js";

function toISO(date) {
  return date.toISOString().slice(0, 10);
}

function memberRows(members = {}) {
  return [
    ...(members.chiefs || []).map((item) => ({ ...item, type: "CHIEF", typeLabel: "Chefe" })),
    ...(members.agents || []).map((item) => ({ ...item, type: "AGENT", typeLabel: "Agente" })),
    ...(members.supports || []).map((item) => ({ ...item, type: "SUPPORT", typeLabel: "Apoio" })),
  ];
}

function sameTypeMembers(type, roster = {}) {
  if (type === "CHIEF") return roster.chiefs || [];
  if (type === "SUPPORT") return roster.supports || [];
  return roster.agents || [];
}

async function loadAll(path) {
  const glue = path.includes("?") ? "&" : "?";
  let nextPath = `${path}${glue}page_size=500`;
  const rows = [];
  while (nextPath) {
    const data = await api(nextPath);
    rows.push(...(data.results || data));
    nextPath = data.next ? `${new URL(data.next).pathname.replace("/api", "")}?${new URL(data.next).searchParams.toString()}` : "";
  }
  return rows;
}

function emptySwapForm(scheduleId = "") {
  return {
    schedule: scheduleId,
    member_type: "AGENT",
    from_member_id: "",
    target_team: "",
    to_member_id: "",
    reason: "",
    attachment: null,
  };
}

function emptyAbsenceForm() {
  return {
    reason: "",
    attachment: null,
  };
}

const teamColorMap = {
  ALFA: { bg: "#e7f8ee", border: "#39a66a", text: "#145232" },
  BRAVO: { bg: "#eaf2ff", border: "#3b82f6", text: "#173f83" },
  CHARLIE: { bg: "#fff1df", border: "#f59e0b", text: "#7a4100" },
  DELTA: { bg: "#f1ecff", border: "#8b5cf6", text: "#4c1d95" },
  ECHO: { bg: "#e8fbff", border: "#06b6d4", text: "#155e75" },
  FOX: { bg: "#fff0f0", border: "#ef4444", text: "#8a1f1f" },
  GOLF: { bg: "#effaf0", border: "#65a30d", text: "#365314" },
  HOTEL: { bg: "#fff7d6", border: "#eab308", text: "#6f5200" },
};

function formatTeamName(value) {
  return String(value || "").trim().toUpperCase();
}

function uniqueUppercaseTeams(rows) {
  const seen = new Set();
  return rows
    .map((team) => ({ ...team, name: formatTeamName(team.name) }))
    .filter((team) => {
      if (!team.name || seen.has(team.name)) return false;
      seen.add(team.name);
      return true;
    })
    .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}

function teamColorStyle(teamName) {
  const palette = teamColorMap[String(teamName || "").trim().toUpperCase()];
  if (!palette) return {};
  return {
    "--shift-team-bg": palette.bg,
    "--shift-team-border": palette.border,
    "--shift-team-text": palette.text,
  };
}

export default function ShiftSchedulePage() {
  const { user } = useAuth();
  const [cursor, setCursor] = useState(new Date());
  const [schedules, setSchedules] = useState([]);
  const [teams, setTeams] = useState([]);
  const [chiefs, setChiefs] = useState([]);
  const [agents, setAgents] = useState([]);
  const [supports, setSupports] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTeamIds, setSelectedTeamIds] = useState([]);
  const [detailScheduleId, setDetailScheduleId] = useState("");
  const [isSwapOpen, setIsSwapOpen] = useState(false);
  const [swapForm, setSwapForm] = useState(emptySwapForm());
  const [attendanceTarget, setAttendanceTarget] = useState(null);
  const [attendanceForm, setAttendanceForm] = useState({});
  const [message, setMessage] = useState("");
  const [swapMessage, setSwapMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const requestSeq = useRef(0);
  const canApprove = ["ADMIN", "MANAGER"].includes(user?.role);
  const isAgentRole = user?.role === "USER";
  const isSupervisorRole = user?.role === "SUPERVISOR";
  const normalizeText = (value) => String(value || "").trim().toLocaleLowerCase("pt-BR");
  const onlyDigits = (value) => String(value || "").replace(/\D/g, "");
  const memberMatchesUser = (member) => {
    const userCpf = onlyDigits(user?.cpf);
    const memberCpf = onlyDigits(member?.cpf);
    if (userCpf && memberCpf && userCpf === memberCpf) return true;
    return Boolean(user?.full_name) && normalizeText(member?.name) === normalizeText(user.full_name);
  };
  const teamMatchesUser = (teamName) => Boolean(user?.sector_name || user?.sector?.name) && normalizeText(teamName) === normalizeText(user.sector_name || user.sector?.name);
  const canDecideSwap = (swap) => {
    if (canApprove) return true;
    const isRequester = swap.requester && user?.id && String(swap.requester) === String(user.id);
    return !isRequester && swap.can_decide === true;
  };

  const days = useMemo(() => {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = new Date(first);
    start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }, [cursor]);

  const rostersByTeam = useMemo(() => {
    const base = {};
    teams.forEach((team) => {
      base[team.name] = { chiefs: [], agents: [], supports: [] };
    });
    chiefs.forEach((item) => {
      const tName = String(item.team_name || "").trim().toUpperCase();
      if (tName && base[tName]) base[tName].chiefs.push(item);
    });
    agents.forEach((item) => {
      const tName = String(item.team_name || "").trim().toUpperCase();
      if (tName && base[tName]) base[tName].agents.push(item);
    });
    supports.forEach((item) => {
      const tName = String(item.team_name || "").trim().toUpperCase();
      if (tName && base[tName]) base[tName].supports.push(item);
    });
    return base;
  }, [agents, chiefs, supports, teams]);

  const selectedSchedules = schedules.filter((item) => item.date === selectedDate);
  const detailSchedule = schedules.find((item) => String(item.id) === String(detailScheduleId));
  const detailRoster = detailSchedule?.members || { chiefs: [], agents: [], supports: [] };
  const detailPendingSwaps = (detailSchedule?.swap_requests || []).filter((swap) => swap.status === "PENDING");
  const swapSchedules = schedules.filter((schedule) => {
    if (isSupervisorRole) return teamMatchesUser(schedule.team_name);
    if (isAgentRole) return memberRows(schedule.members).some(memberMatchesUser);
    return true;
  });
  const swapSchedule = schedules.find((item) => String(item.id) === String(swapForm.schedule));
  const swapRoster = swapSchedule?.members || { chiefs: [], agents: [], supports: [] };
  const targetRoster = rostersByTeam[String(swapForm.target_team)] || { chiefs: [], agents: [], supports: [] };
  const visibleTeams = isSupervisorRole
    ? teams.filter((team) => teamMatchesUser(team.name))
    : teams;
  const selectableTargetTeams = teams.filter((team) => String(team.id) !== String(swapSchedule?.team));
  const fromMemberOptions = sameTypeMembers(swapForm.member_type, swapRoster).filter((member) => {
    if (isAgentRole) return memberMatchesUser(member);
    if (isSupervisorRole) return teamMatchesUser(member.team_name || swapSchedule?.team_name);
    return true;
  });
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportTeam, setReportTeam] = useState("");
  const [reportMonth, setReportMonth] = useState(cursor.getMonth());
  const [reportYear, setReportYear] = useState(cursor.getFullYear());

  const openReportModal = () => {
    if (!canApprove) return;
    if (teams.length > 0 && !reportTeam) {
      setReportTeam(String(teams[0].id));
    }
    setReportMonth(cursor.getMonth());
    setReportYear(cursor.getFullYear());
    setIsReportOpen(true);
  };

  const reportSchedules = useMemo(() => {
    if (!isReportOpen || !reportTeam) return [];
    return schedules.filter((s) => {
      const d = new Date(s.date + "T12:00:00");
      return (
        String(s.team) === String(reportTeam) &&
        d.getMonth() === Number(reportMonth) &&
        d.getFullYear() === Number(reportYear)
      );
    }).sort((a, b) => a.date.localeCompare(b.date));
  }, [schedules, isReportOpen, reportTeam, reportMonth, reportYear]);

  const reportChiefName = useMemo(() => {
    const teamChief = chiefs.find((c) => String(c.team) === String(reportTeam) && c.is_active);
    return teamChief ? teamChief.name : "Chefe não cadastrado";
  }, [chiefs, reportTeam]);
  const loadSchedules = async () => {
    const params = new URLSearchParams({
      date_from: toISO(days[0]),
      date_to: toISO(days[days.length - 1]),
    }).toString();
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    const data = await loadAll(`/shift-schedules/?${params}`);
    if (seq === requestSeq.current) {
      setSchedules(data);
    }
  };

  useEffect(() => {
    Promise.all([
      loadAll("/teams/"),
      loadAll("/chiefs/"),
      loadAll("/agents/"),
      loadAll("/supports/"),
    ]).then(([teamRows, chiefRows, agentRows, supportRows]) => {
      const fromUsers = (row) => String(row.source_id || "").startsWith("user:");
      setTeams(uniqueUppercaseTeams(teamRows));
      setChiefs(chiefRows.filter(fromUsers));
      setAgents(agentRows.filter(fromUsers));
      setSupports(supportRows.filter(fromUsers));
    });
  }, []);

  useEffect(() => {
    loadSchedules().catch((err) => setMessage(err.message));
  }, [days]);

  const openDay = (date) => {
    if (!canApprove) return;
    const iso = toISO(date);
    const daySchedules = schedules.filter((item) => item.date === iso);
    setSelectedDate(iso);
    setSelectedTeamIds(daySchedules.map((item) => String(item.team)));
    setMessage("");
  };

  const openTeamDetail = (schedule) => {
    setDetailScheduleId(String(schedule.id));
    setMessage("");
  };

  const toggleTeam = (teamId) => {
    const id = String(teamId);
    setSelectedTeamIds((current) => (
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    ));
  };

  const saveDayTeams = async () => {
    if (!canApprove) {
      setMessage("Apenas gestores e administradores podem fazer escala.");
      return;
    }
    if (!selectedDate || !selectedTeamIds.length) {
      setMessage("Selecione ao menos uma equipe para a escala.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const freshDayData = await api(`/shift-schedules/?date=${selectedDate}`);
      const freshDaySchedules = freshDayData.results || freshDayData;
      const existingByTeam = new Map(freshDaySchedules.map((schedule) => [String(schedule.team), schedule]));
      const selected = new Set(selectedTeamIds.map(String));
      const toCreate = selectedTeamIds.filter((teamId) => !existingByTeam.has(String(teamId)));
      const toRemove = freshDaySchedules.filter((schedule) => !selected.has(String(schedule.team)));
      await Promise.all(toCreate.map((teamId) => (
        api("/shift-schedules/", {
          method: "POST",
          body: JSON.stringify({ date: selectedDate, team: Number(teamId), notes: "" }),
        })
      )));
      if (canApprove) {
        await Promise.all(toRemove.map((schedule) => (
          api(`/shift-schedules/${schedule.id}/`, { method: "DELETE" })
        )));
      }
      await loadSchedules();
      setSelectedDate(null);
      setMessage(toRemove.length && !canApprove
        ? "Equipes adicionadas. Remoção de escala exige gestor ou administrador."
        : "Escala do dia salva.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openSwapModal = (scheduleId = "") => {
    const allowedSchedules = swapSchedules;
    const firstSchedule = scheduleId || allowedSchedules[0]?.id || "";
    if (!firstSchedule) {
      setMessage("Cadastre uma escala antes de solicitar troca.");
      return;
    }
    if ((isAgentRole || isSupervisorRole) && !allowedSchedules.some((schedule) => String(schedule.id) === String(firstSchedule))) {
      setMessage(isAgentRole ? "Seu perfil so pode solicitar troca para o proprio agente." : "Chefes so podem solicitar troca da propria equipe.");
      return;
    }
    setSwapForm(emptySwapForm(String(firstSchedule)));
    setSwapMessage("");
    setIsSwapOpen(true);
  };

  const changeSwapSchedule = (scheduleId) => {
    setSwapForm(emptySwapForm(scheduleId));
    setSwapMessage("");
  };

  const submitSwap = async () => {
    if (!swapSchedule) {
      setSwapMessage("Selecione a escala da troca.");
      return;
    }
    if (!swapForm.from_member_id || !swapForm.target_team || !swapForm.to_member_id) {
      setSwapMessage("Preencha os integrantes da troca.");
      return;
    }
    setLoading(true);
    setSwapMessage("");
    try {
      const body = new FormData();
      body.append("schedule", swapForm.schedule);
      body.append("member_type", swapForm.member_type);
      body.append("from_member_id", swapForm.from_member_id);
      body.append("target_team", swapForm.target_team);
      body.append("to_member_id", swapForm.to_member_id);
      body.append("reason", swapForm.reason);
      if (swapForm.attachment) {
        body.append("attachment", swapForm.attachment);
      }
      await api("/shift-swaps/", { method: "POST", body });
      await loadSchedules();
      window.dispatchEvent(new Event("shift-swaps:changed"));
      setSwapForm(emptySwapForm(String(swapForm.schedule)));
      setSwapMessage("Solicitação de troca enviada para aprovação.");
    } catch (err) {
      setSwapMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const decideSwap = async (swapId, action) => {
    setLoading(true);
    setSwapMessage("");
    try {
      await api(`/shift-swaps/${swapId}/${action}/`, { method: "POST", body: JSON.stringify({}) });
      await loadSchedules();
      window.dispatchEvent(new Event("shift-swaps:changed"));
      setSwapMessage(action === "approve" ? "Troca aprovada." : "Troca rejeitada.");
    } catch (err) {
      setSwapMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (group, memberId) => {
    if (!canApprove || !detailSchedule) return;
    setLoading(true);
    setMessage("");
    try {
      const idNum = Number(memberId);
      const isChief = group === "chiefs";
      const isSupport = group === "supports";
      const isAgent = group === "agents";

      let memberObj = null;
      if (isChief) memberObj = chiefs.find((c) => c.id === idNum);
      if (isAgent) memberObj = agents.find((a) => a.id === idNum);
      if (isSupport) memberObj = supports.find((s) => s.id === idNum);

      if (!memberObj) return;

      const isDefaultTeamMember = String(memberObj.team_name || "").trim().toUpperCase() === String(detailSchedule.team_name || "").trim().toUpperCase();

      let payload = {};
      if (isChief) {
        if (isDefaultTeamMember) {
          payload.removed_chiefs = (detailSchedule.removed_chiefs || []).filter((id) => id !== idNum);
        } else {
          payload.extra_chiefs = [...(detailSchedule.extra_chiefs || []), idNum];
        }
      } else if (isSupport) {
        if (isDefaultTeamMember) {
          payload.removed_supports = (detailSchedule.removed_supports || []).filter((id) => id !== idNum);
        } else {
          payload.extra_supports = [...(detailSchedule.extra_supports || []), idNum];
        }
      } else if (isAgent) {
        if (isDefaultTeamMember) {
          payload.removed_agents = (detailSchedule.removed_agents || []).filter((id) => id !== idNum);
        } else {
          payload.extra_agents = [...(detailSchedule.extra_agents || []), idNum];
        }
      }

      const updated = await api(`/shift-schedules/${detailSchedule.id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      setSchedules((current) =>
        current.map((s) => (String(s.id) === String(detailSchedule.id) ? updated : s))
      );
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveMember = async (group, member) => {
    if (!canApprove || !detailSchedule) return;
    setLoading(true);
    setMessage("");
    try {
      const idNum = Number(member.id);
      const isChief = group === "chiefs";
      const isSupport = group === "supports";
      const isAgent = group === "agents";

      let payload = {};
      if (member.is_extra) {
        if (isChief) {
          payload.extra_chiefs = (detailSchedule.extra_chiefs || []).filter((id) => id !== idNum);
        } else if (isSupport) {
          payload.extra_supports = (detailSchedule.extra_supports || []).filter((id) => id !== idNum);
        } else if (isAgent) {
          payload.extra_agents = (detailSchedule.extra_agents || []).filter((id) => id !== idNum);
        }
      } else {
        if (isChief) {
          payload.removed_chiefs = [...(detailSchedule.removed_chiefs || []), idNum];
        } else if (isSupport) {
          payload.removed_supports = [...(detailSchedule.removed_supports || []), idNum];
        } else if (isAgent) {
          payload.removed_agents = [...(detailSchedule.removed_agents || []), idNum];
        }
      }

      const updated = await api(`/shift-schedules/${detailSchedule.id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      setSchedules((current) =>
        current.map((s) => (String(s.id) === String(detailSchedule.id) ? updated : s))
      );
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openAttendanceManager = (schedule) => {
    const form = {};
    memberRows(schedule.members).forEach(m => {
       form[`${m.type}_${m.id}`] = {
         is_absent: !!m.is_absent,
         reason: m.absence_reason || "",
         attachment: null,
         member: m
       };
    });
    setAttendanceForm(form);
    setAttendanceTarget(schedule);
  };

  const submitAttendanceManager = async () => {
    if (!canApprove || !attendanceTarget) return;
    setLoading(true);
    setMessage("");
    try {
      const promises = Object.entries(attendanceForm).map(([key, data]) => {
        const [memberType, memberId] = key.split("_");
        if (data.is_absent) {
          const body = new FormData();
          body.append("member_type", memberType);
          body.append("member_id", memberId);
          body.append("reason", data.reason || "Falta");
          if (data.attachment) body.append("attachment", data.attachment);
          return api(`/shift-schedules/${attendanceTarget.id}/absence/`, { method: "POST", body });
        } else {
          return api(`/shift-schedules/${attendanceTarget.id}/absence/`, { 
            method: "DELETE", 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ member_type: memberType, member_id: memberId })
          });
        }
      });
      await Promise.all(promises);
      
      if (attendanceTarget.attendance_reported && !attendanceTarget.attendance_approved) {
        await api(`/shift-schedules/${attendanceTarget.id}/approve-attendance/`, { method: "POST" });
      }
      
      await loadSchedules();
      setAttendanceTarget(null);
      if (detailScheduleId === String(attendanceTarget.id)) {
        setDetailScheduleId(""); // close details to force reload if needed, or we just let it reload
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteSchedule = async () => {
    if (!canApprove || !detailSchedule) return;
    if (!window.confirm(`Excluir a escala da equipe ${formatTeamName(detailSchedule.team_name)} em ${formatDateBR(detailSchedule.date)}?`)) {
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      await api(`/shift-schedules/${detailSchedule.id}/`, { method: "DELETE" });
      setDetailScheduleId("");
      await loadSchedules();
      setMessage("Escala excluida.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = () => {
    const originalTitle = document.title;
    const teamName = teams.find((t) => String(t.id) === String(reportTeam))?.name || "Equipe";
    const monthName = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][Number(reportMonth)];
    document.title = `Relatorio_Mensal_${teamName}_${monthName}_${reportYear}`;
    window.print();
    document.title = originalTitle;
  };

  return (
    <section className="page shift-page">
      <div className="page-title">
        <div>
          <h1>Escala</h1>
          <p>Selecione rapidamente as equipes de serviço por dia e acompanhe as solicitações de troca.</p>
        </div>
      </div>

      <div className="calendar-toolbar shift-toolbar">
        <button className="icon-button" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))} aria-label="Mês anterior"><ChevronLeft size={18} /></button>
        <strong>{cursor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</strong>
        <button className="icon-button" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))} aria-label="Próximo mês"><ChevronRight size={18} /></button>
        <input className="jump-date" type="date" value={toISO(cursor)} onChange={(event) => setCursor(new Date(`${event.target.value}T12:00:00`))} />
        <button type="button" className="secondary" onClick={() => openSwapModal()}><Repeat2 size={17} /> Solicitar troca</button>
        <button type="button" className="secondary" onClick={() => openReportModal()} style={{ marginLeft: 8 }}><CalendarDays size={17} /> Relatório RH</button>
      </div>

      {message && <div className="alert">{message}</div>}

      <div className="calendar-grid shift-calendar-grid">
        {days.map((day) => {
          const iso = toISO(day);
          const daySchedules = schedules.filter((item) => item.date === iso);
          return (
            <article key={iso} className="day-cell shift-day-cell" onClick={() => openDay(day)}>
              <span>{day.getDate()}</span>
              {daySchedules.map((schedule) => (
                <button key={schedule.id} className="shift-team-pill" type="button" onClick={(event) => { event.stopPropagation(); openTeamDetail(schedule); }}>
                  <span>
                    <strong>{formatTeamName(schedule.team_name)}</strong>
                    {(schedule.swap_requests || []).some((swap) => swap.status === "PENDING") && (
                      <b><AlertTriangle size={12} /> Troca</b>
                    )}
                    {schedule.date <= toISO(new Date()) && (
                      schedule.attendance_approved ? (
                        <b style={{ background: "#dcfce7", color: "#15803d", marginLeft: "4px", gap: "2px" }} title="Frequência Aprovada">
                          <CheckCircle2 size={12} /> Freq. OK
                        </b>
                      ) : schedule.attendance_reported ? (
                        <b style={{ background: "#fef08a", color: "#854d0e", marginLeft: "4px", gap: "2px" }} title="Frequência reportada. Aguardando revisão.">
                          <AlertCircle size={12} /> Revisar Freq.
                        </b>
                      ) : (
                        <b style={{ background: "#fee2e2", color: "#b91c1c", marginLeft: "4px", gap: "2px" }} title="Frequência pendente de envio pelo relatório">
                          <AlertCircle size={12} /> Freq. Pendente
                        </b>
                      )
                    )}
                  </span>
                  <small>{memberRows(schedule.members).length} integrantes</small>
                </button>
              ))}
            </article>
          );
        })}
      </div>

      {selectedDate && (
        <div className="modal-backdrop" onClick={() => setSelectedDate(null)}>
          <article className="modal shift-modal shift-team-modal" onClick={(event) => event.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h2>Escala de {formatDateBR(selectedDate)}</h2>
                <p>Marque as equipes que estarão de serviço neste dia.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setSelectedDate(null)} aria-label="Fechar"><X size={18} /></button>
            </header>

            <div className="shift-team-picker">
              {visibleTeams.map((team) => {
                const roster = rostersByTeam[team.name] || {};
                return (
                  <label key={team.id} className={selectedTeamIds.includes(String(team.id)) ? "selected" : ""}>
                    <input
                      type="checkbox"
                      checked={selectedTeamIds.includes(String(team.id))}
                      onChange={() => toggleTeam(team.id)}
                    />
                    <span>
                      <strong>{team.name}</strong>
                      <small>{memberRows(roster).length} integrantes cadastrados</small>
                    </span>
                  </label>
                );
              })}
            </div>

            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setSelectedDate(null)}>Cancelar</button>
              <button type="button" onClick={saveDayTeams} disabled={loading}><CalendarDays size={17} /> Salvar escala</button>
            </div>
          </article>
        </div>
      )}

      {detailSchedule && (
        <div className="modal-backdrop" onClick={() => setDetailScheduleId("")}>
          <article className="modal shift-modal" onClick={(event) => event.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h2>{formatTeamName(detailSchedule.team_name)}</h2>
                <p>Serviço de {formatDateBR(detailSchedule.date)}</p>
              </div>
              <div className="modal-header-actions">
                {canApprove && (
                  <button className="secondary danger-action" type="button" onClick={deleteSchedule} disabled={loading}>
                    <Trash2 size={16} /> Excluir escala
                  </button>
                )}
                <button className="icon-button" type="button" onClick={() => setDetailScheduleId("")} aria-label="Fechar"><X size={18} /></button>
              </div>
            </header>

            {detailPendingSwaps.length > 0 && (
              <section className="shift-swap-alert-panel">
                <h3><AlertTriangle size={16} /> Troca pendente</h3>
                {detailPendingSwaps.map((swap) => (
                  <article key={swap.id} className="swap-card pending">
                    <div>
                      <strong>{swap.from_member_name} por {swap.to_member_name}</strong>
                      <span>{swap.member_type === "CHIEF" ? "Chefe" : swap.member_type === "SUPPORT" ? "Apoio" : "Agente"} | {formatTeamName(swap.schedule_team_name)} para {formatTeamName(swap.target_team_name)}</span>
                      {swap.reason && <small>{swap.reason}</small>}
                      {swap.attachment_url && <a href={swap.attachment_url} target="_blank" rel="noreferrer"><Paperclip size={13} /> Anexo</a>}
                    </div>
                    <b>Pendente</b>
                    {canDecideSwap(swap) && (
                      <div className="swap-actions">
                        <button type="button" onClick={() => decideSwap(swap.id, "approve")}><Check size={15} /> Aprovar</button>
                        <button className="secondary" type="button" onClick={() => decideSwap(swap.id, "reject")}><X size={15} /> Rejeitar</button>
                      </div>
                    )}
                  </article>
                ))}
              </section>
            )}

            <section className="shift-roster">
              <h3>Integrantes em serviço</h3>
              {["chiefs", "agents", "supports"].map((group) => (
                <div key={group} className="shift-roster-group">
                  <strong>{group === "chiefs" ? "👤 Chefes" : group === "agents" ? "🛡️ Agentes" : "🤝 Apoio"}</strong>
                  {(detailRoster[group] || []).length ? (
                    <div className="shift-member-list">
                       {(detailRoster[group] || []).map((member) => (
                        <span
                          key={`${group}-${member.id}`}
                          className={`${member.swapped ? "swapped" : ""} ${member.is_extra ? "extra-member" : ""} ${member.is_absent ? "absent-member" : ""}`}
                        >
                          <span style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
                            <span style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "4px" }}>
                              <span style={{ fontWeight: 500, textDecoration: member.is_absent ? "line-through" : "none", opacity: member.is_absent ? 0.6 : 1 }}>{member.name}</span>
                              {member.is_extra && <span className="member-badge extra">Extra</span>}
                              {member.is_absent && <span className="member-badge absent">Falta</span>}
                            </span>
                            {member.role && <small>{member.role}</small>}
                            {member.is_absent && member.absence_reason && (
                              <small className="absence-note">{member.absence_reason}</small>
                            )}
                            {member.is_absent && member.absence_attachment_url && (
                              <a className="absence-attachment" href={member.absence_attachment_url} target="_blank" rel="noreferrer">
                                <Paperclip size={13} /> Anexo da justificativa
                              </a>
                            )}
                          </span>
                          <div className="shift-member-actions">
                            {canApprove && !member.swapped && (
                              <button
                                type="button"
                                className="remove-btn"
                                onClick={() => handleRemoveMember(group, member)}
                                title="Remover da escala"
                              >
                                <X size={14} />
                              </button>
                            )}
                          </div>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: "var(--text-soft)", fontSize: "0.85rem", margin: "4px 0", fontStyle: "italic" }}>Nenhum integrante cadastrado.</p>
                  )}
                  {canApprove && (
                    <select
                      className="shift-add-member-select"
                      defaultValue=""
                      onChange={(e) => {
                        if (e.target.value) {
                          handleAddMember(group, e.target.value);
                          e.target.value = "";
                        }
                      }}
                    >
                      <option value="">+ Adicionar integrante...</option>
                      {(group === "chiefs" ? chiefs : group === "agents" ? agents : supports)
                        .filter((allM) => {
                          if (allM.vacation_start && allM.vacation_end) {
                            if (detailSchedule.date >= allM.vacation_start && detailSchedule.date <= allM.vacation_end) return false;
                          }
                          return !(detailRoster[group] || []).some((m) => String(m.id) === String(allM.id));
                        })
                        .map((allM) => {
                          const teamObj = teams.find((t) => String(t.id) === String(allM.team));
                          return (
                            <option key={allM.id} value={allM.id}>
                              {allM.name} {teamObj ? `(${teamObj.name})` : ""}
                            </option>
                          );
                        })}
                    </select>
                  )}
                </div>
              ))}
              {canApprove && (
                <div style={{ marginTop: "20px", display: "flex", justifyContent: "center", gap: "10px", padding: "10px", borderTop: "1px solid #ddd" }}>
                  <button className="primary" onClick={() => openAttendanceManager(detailSchedule)}>
                    {detailSchedule.attendance_reported && !detailSchedule.attendance_approved ? "Dar Ciência / Aprovar Frequência" : "Gerenciar Frequência"}
                  </button>
                </div>
              )}
            </section>
          </article>
        </div>
      )}

      {attendanceTarget && (
        <div className="modal-backdrop" onClick={() => setAttendanceTarget(null)}>
          <article className="modal shift-modal" onClick={(event) => event.stopPropagation()} style={{ maxWidth: "800px" }}>
            <header className="modal-header">
              <div>
                <h2>Gerenciar Frequência - {formatTeamName(attendanceTarget.team_name)}</h2>
                <p>Data: {formatDateBR(attendanceTarget.date)}</p>
                {attendanceTarget.attendance_reported && !attendanceTarget.attendance_approved && (
                  <p style={{ color: "#854d0e", fontWeight: "bold" }}>O relatório de frequência foi enviado. Revise e aprove abaixo.</p>
                )}
              </div>
              <button className="icon-button" type="button" onClick={() => setAttendanceTarget(null)} aria-label="Fechar"><X size={18} /></button>
            </header>

            <section className="attendance-manager-list" style={{ maxHeight: "60vh", overflowY: "auto", padding: "10px" }}>
              {Object.entries(attendanceForm).map(([key, data]) => (
                <div key={key} style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "12px", marginBottom: "10px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div style={{ fontWeight: 500, fontSize: "1.1rem" }}>
                      {data.member.name} <small style={{ color: "var(--text-soft)" }}>({data.member.typeLabel})</small>
                    </div>
                    <div style={{ display: "flex", gap: "15px" }}>
                      <label style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }}>
                        <input
                          type="radio"
                          name={`status_${key}`}
                          checked={!data.is_absent}
                          onChange={() => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], is_absent: false } }))}
                        />
                        <span style={{ color: !data.is_absent ? "#15803d" : "inherit", fontWeight: !data.is_absent ? "bold" : "normal" }}>Presente</span>
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }}>
                        <input
                          type="radio"
                          name={`status_${key}`}
                          checked={data.is_absent}
                          onChange={() => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], is_absent: true } }))}
                        />
                        <span style={{ color: data.is_absent ? "#b91c1c" : "inherit", fontWeight: data.is_absent ? "bold" : "normal" }}>Falta</span>
                      </label>
                    </div>
                  </div>
                  {data.is_absent && (
                    <div style={{ background: "#f9fafb", padding: "10px", borderRadius: "4px", marginTop: "10px" }}>
                      <label style={{ display: "block", marginBottom: "10px" }}>
                        <span style={{ display: "block", fontSize: "0.85rem", marginBottom: "4px" }}>Justificativa</span>
                        <input
                          type="text"
                          value={data.reason}
                          onChange={(e) => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], reason: e.target.value } }))}
                          placeholder="Ex: Férias, Atestado, etc."
                          style={{ width: "100%", padding: "6px", border: "1px solid #ccc", borderRadius: "4px" }}
                        />
                      </label>
                      <label style={{ display: "block" }}>
                        <span style={{ display: "block", fontSize: "0.85rem", marginBottom: "4px" }}>Comprovante (opcional)</span>
                        {data.member.absence_attachment_url && !data.attachment && (
                          <div style={{ marginBottom: "5px" }}>
                            <a href={data.member.absence_attachment_url} target="_blank" rel="noreferrer" style={{ fontSize: "0.85rem", color: "var(--primary-color)" }}>
                              <Paperclip size={12} /> Ver anexo enviado pelo chefe
                            </a>
                          </div>
                        )}
                        <input
                          type="file"
                          onChange={(e) => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], attachment: e.target.files?.[0] || null } }))}
                          style={{ fontSize: "0.85rem" }}
                        />
                      </label>
                    </div>
                  )}
                </div>
              ))}
              {Object.keys(attendanceForm).length === 0 && (
                <p>Nenhum integrante na equipe.</p>
              )}
            </section>

            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setAttendanceTarget(null)}>Cancelar</button>
              <button type="button" onClick={submitAttendanceManager} disabled={loading}>
                {attendanceTarget.attendance_reported && !attendanceTarget.attendance_approved ? "Aprovar Frequência" : "Salvar Frequência"}
              </button>
            </div>
          </article>
        </div>
      )}

      {isSwapOpen && (
        <div className="modal-backdrop" onClick={() => setIsSwapOpen(false)}>
          <article className="modal shift-modal" onClick={(event) => event.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h2>Solicitar troca</h2>
                <p>Escolha a escala e informe quem sai e quem entra na mesma função.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setIsSwapOpen(false)} aria-label="Fechar"><X size={18} /></button>
            </header>

            <section className="shift-swap-box">
              <div className="shift-swap-grid">
                <label className="full">
                  <span>Escala</span>
                  <select value={swapForm.schedule} onChange={(event) => changeSwapSchedule(event.target.value)}>
                    {swapSchedules.map((schedule) => (
                      <option key={schedule.id} value={schedule.id}>
                        {formatDateBR(schedule.date)} - {formatTeamName(schedule.team_name)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Função</span>
                  <select value={swapForm.member_type} onChange={(event) => setSwapForm({ ...emptySwapForm(swapForm.schedule), member_type: event.target.value })}>
                    {!isAgentRole && <option value="CHIEF">Chefe</option>}
                    <option value="AGENT">Agente</option>
                    {!isAgentRole && <option value="SUPPORT">Apoio</option>}
                  </select>
                </label>
                <label>
                  <span>Quem sai</span>
                  <select value={swapForm.from_member_id} onChange={(event) => setSwapForm((current) => ({ ...current, from_member_id: event.target.value }))}>
                    <option value="">Selecione</option>
                    {fromMemberOptions.map((member) => (
                      <option key={member.id} value={member.id}>{member.name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Equipe substituta</span>
                  <select value={swapForm.target_team} onChange={(event) => setSwapForm((current) => ({ ...current, target_team: event.target.value, to_member_id: "" }))}>
                    <option value="">Selecione</option>
                    {selectableTargetTeams.map((team) => (
                      <option key={team.id} value={team.id}>{team.name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Quem entra</span>
                  <select value={swapForm.to_member_id} onChange={(event) => setSwapForm((current) => ({ ...current, to_member_id: event.target.value }))}>
                    <option value="">Selecione</option>
                    {sameTypeMembers(swapForm.member_type, targetRoster).map((member) => (
                      <option key={member.id} value={member.id}>{member.name}</option>
                    ))}
                  </select>
                </label>
                <label className="full">
                  <span>Motivo</span>
                  <input value={swapForm.reason} onChange={(event) => setSwapForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Opcional" />
                </label>
                <label className="full">
                  <span>Anexo opcional</span>
                  <input type="file" onChange={(event) => setSwapForm((current) => ({ ...current, attachment: event.target.files?.[0] || null }))} />
                </label>
                <button type="button" onClick={submitSwap} disabled={loading}><Repeat2 size={17} /> Enviar solicitação</button>
              </div>
            </section>

            <section className="shift-swap-list">
              <h3>Solicitações desta escala</h3>
              {(swapSchedule?.swap_requests || []).length ? (
                swapSchedule.swap_requests.map((swap) => (
                  <article key={swap.id} className={`swap-card ${swap.status.toLowerCase()}`}>
                    <div>
                      <strong>{swap.from_member_name} por {swap.to_member_name}</strong>
                      <span>{swap.member_type === "CHIEF" ? "Chefe" : swap.member_type === "SUPPORT" ? "Apoio" : "Agente"} | {formatTeamName(swap.schedule_team_name)} para {formatTeamName(swap.target_team_name)}</span>
                      {swap.reason && <small>{swap.reason}</small>}
                      {swap.attachment_url && <a href={swap.attachment_url} target="_blank" rel="noreferrer"><Paperclip size={13} /> Anexo</a>}
                    </div>
                    <b>{swap.status === "PENDING" ? "Pendente" : swap.status === "APPROVED" ? "Aprovada" : "Rejeitada"}</b>
                    {canDecideSwap(swap) && swap.status === "PENDING" && (
                      <div className="swap-actions">
                        <button type="button" onClick={() => decideSwap(swap.id, "approve")}><Check size={15} /> Aprovar</button>
                        <button className="secondary" type="button" onClick={() => decideSwap(swap.id, "reject")}><X size={15} /> Rejeitar</button>
                      </div>
                    )}
                  </article>
                ))
              ) : (
                <p>Nenhuma solicitação de troca para esta escala.</p>
              )}
            </section>

            {swapMessage && <div className="alert">{swapMessage}</div>}
          </article>
        </div>
      )}

      {isReportOpen && (
        <div className="modal-backdrop" onClick={() => setIsReportOpen(false)}>
          <article className="modal shift-modal" onClick={(event) => event.stopPropagation()} style={{ maxWidth: "800px", width: "95%" }}>
            <header className="modal-header">
              <div>
                <h2>Relatório Mensal de Escala e Frequência (RH)</h2>
                <p>Gere e imprima a folha de frequência mensal consolidada de uma equipe para entrega ao RH.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setIsReportOpen(false)} aria-label="Fechar"><X size={18} /></button>
            </header>

            <div className="filters report-filters" style={{ display: "flex", gap: "12px", marginBottom: "20px", padding: "12px", background: "var(--bg-light, #f8fafc)", borderRadius: "8px" }}>
              <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: "600" }}>Equipe</span>
                <select value={reportTeam} onChange={(e) => setReportTeam(e.target.value)} style={{ padding: "6px 10px", borderRadius: "4px", border: "1px solid #ccc" }}>
                  {visibleTeams.map((team) => (
                    <option key={team.id} value={team.id}>{team.name}</option>
                  ))}
                </select>
              </label>
              <label style={{ width: "150px", display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: "600" }}>Mês</span>
                <select value={reportMonth} onChange={(e) => setReportMonth(e.target.value)} style={{ padding: "6px 10px", borderRadius: "4px", border: "1px solid #ccc" }}>
                  {["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"].map((m, idx) => (
                    <option key={idx} value={idx}>{m}</option>
                  ))}
                </select>
              </label>
              <label style={{ width: "100px", display: "flex", flexDirection: "column", gap: "4px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: "600" }}>Ano</span>
                <input
                  type="number"
                  value={reportYear}
                  onChange={(e) => setReportYear(e.target.value)}
                  style={{ padding: "6px 10px", borderRadius: "4px", border: "1px solid #ccc" }}
                />
              </label>
            </div>

            <section className="print-report-area" style={{ background: "#fff", color: "#000", padding: "30px", border: "1px solid #e2e8f0", borderRadius: "6px", fontFamily: "Courier New, monospace" }}>
              <style>{`
                @media print {
                  @page {
                    size: A4 portrait !important;
                    margin: 1.5cm !important;
                  }
                  body, html {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #fff !important;
                    width: 100% !important;
                  }
                  .sidebar,
                  .topbar,
                  .page-title,
                  .calendar-toolbar,
                  .calendar-grid,
                  .alert,
                  .modal-header,
                  .report-filters,
                  .modal-actions {
                    display: none !important;
                  }
                  .app-shell,
                  .content {
                    display: block !important;
                    position: static !important;
                    width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    overflow: visible !important;
                  }
                  .modal-backdrop {
                    position: static !important;
                    background: transparent !important;
                    display: block !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    overflow: visible !important;
                    width: 100% !important;
                  }
                  .modal {
                    box-shadow: none !important;
                    border: none !important;
                    background: transparent !important;
                    max-width: 100% !important;
                    width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    display: block !important;
                  }
                  .print-report-area {
                    border: none !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                  }
                }
              `}</style>

              <div style={{ textAlign: "center", borderBottom: "2px double #000", paddingBottom: "10px", marginBottom: "20px" }}>
                <h3 style={{ margin: "0 0 5px 0", fontSize: "1.3rem", fontWeight: "bold" }}>OPERAÇÃO LEI SECA</h3>
                <h4 style={{ margin: "0", fontSize: "1rem", textTransform: "uppercase" }}>RELATÓRIO MENSAL DE FREQUÊNCIA E ESCALA</h4>
                <span style={{ fontSize: "0.8rem", color: "#666" }}>Destinatário: Departamento de Recursos Humanos (RH)</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "20px", fontSize: "0.9rem", borderBottom: "1px solid #ccc", paddingBottom: "10px" }}>
                <div><strong>Equipe:</strong> {formatTeamName(teams.find(t => String(t.id) === String(reportTeam))?.name || "-")}</div>
                <div><strong>Competência:</strong> {["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][Number(reportMonth)]} / {reportYear}</div>
                <div><strong>Chefe de Equipe:</strong> {reportChiefName}</div>
                <div><strong>Total de Plantões:</strong> {reportSchedules.length}</div>
              </div>

              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", marginBottom: "20px" }}>
                <thead>
                  <tr style={{ borderBottom: "1.5px solid #000" }}>
                    <th style={{ textAlign: "left", padding: "6px", border: "1px solid #ddd" }}>Data</th>
                    <th style={{ textAlign: "left", padding: "6px", border: "1px solid #ddd" }}>Presenças</th>
                    <th style={{ textAlign: "left", padding: "6px", border: "1px solid #ddd" }}>Faltas</th>
                    <th style={{ textAlign: "left", padding: "6px", border: "1px solid #ddd" }}>Trocas/Substituições Homologadas</th>
                  </tr>
                </thead>
                <tbody>
                  {reportSchedules.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: "center", padding: "20px", color: "#666" }}>Nenhum plantão registrado nesta competência.</td>
                    </tr>
                  ) : (
                    reportSchedules.map((sched) => {
                      const allMembers = [
                        ...(sched.members?.chiefs || []),
                        ...(sched.members?.agents || []),
                        ...(sched.members?.supports || [])
                      ];
                      
                      const presences = allMembers.filter(m => !m.is_absent).map(m => m.name);
                      const absences = allMembers.filter(m => m.is_absent).map((m) => ({
                        name: m.name,
                        reason: m.absence_reason || "Justificativa nao informada",
                      }));
                      
                      const approvedSwaps = (sched.swap_requests || [])
                        .filter(sw => sw.status === "APPROVED")
                        .map(sw => `${sw.from_member_name} por ${sw.to_member_name}`);

                      return (
                        <tr key={sched.id} style={{ borderBottom: "1px solid #eee" }}>
                          <td style={{ padding: "6px", whiteSpace: "nowrap", fontWeight: "bold", border: "1px solid #ddd" }}>{formatDateBR(sched.date)}</td>
                          <td style={{ padding: "6px", border: "1px solid #ddd" }}>{presences.length > 0 ? presences.join(", ") : "-"}</td>
                          <td style={{ padding: "6px", color: absences.length > 0 ? "#b91c1c" : "inherit", border: "1px solid #ddd" }}>
                            {absences.length > 0 ? (
                              <div style={{ display: "grid", gap: "6px" }}>
                                {absences.map((absence) => (
                                  <div key={`${sched.id}-${absence.name}`}>
                                    <strong>{absence.name}</strong>
                                    <br />
                                    <span style={{ color: "#374151", fontSize: "0.78rem" }}>Justificativa: {absence.reason}</span>
                                  </div>
                                ))}
                              </div>
                            ) : "Nenhuma"}
                          </td>
                          <td style={{ padding: "6px", fontSize: "0.8rem", fontStyle: "italic", border: "1px solid #ddd" }}>{approvedSwaps.length > 0 ? approvedSwaps.join(" | ") : "Nenhuma"}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>

              <div style={{ marginTop: "40px", fontSize: "0.85rem", lineHeight: "1.5" }}>
                <p style={{ margin: "0 0 40px 0" }}>
                  Declaro que as informações constantes neste relatório correspondem fielmente às escalas de serviço
                  efetivamente cumpridas pela equipe e as ausências ou substituições foram devidamente registradas e justificadas.
                </p>

                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "20px" }}>
                  <div style={{ width: "300px", borderBottom: "1px solid #000", marginBottom: "5px" }}></div>
                  <strong style={{ fontSize: "0.9rem" }}>{reportChiefName}</strong>
                  <span style={{ fontSize: "0.8rem", color: "#555" }}>Chefe de Equipe / Responsável</span>
                </div>
              </div>
            </section>

            <div className="modal-actions" style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button className="secondary" type="button" onClick={() => setIsReportOpen(false)}>Fechar</button>
              <button type="button" onClick={handleExportPDF} disabled={reportSchedules.length === 0}>
                Exportar PDF
              </button>
            </div>
          </article>
        </div>
      )}
    </section>
  );
}

import { AlertTriangle, CalendarDays, Check, ChevronLeft, ChevronRight, Paperclip, Repeat2, Trash2, X } from "lucide-react";
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
  const [message, setMessage] = useState("");
  const [swapMessage, setSwapMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const requestSeq = useRef(0);
  const canApprove = user?.is_superuser || user?.is_staff || ["ADMIN", "MANAGER", "CREATOR"].includes(user?.role);
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
      base[String(team.id)] = { chiefs: [], agents: [], supports: [] };
    });
    chiefs.forEach((item) => {
      if (item.team) base[String(item.team)]?.chiefs.push(item);
    });
    agents.forEach((item) => {
      if (item.team) base[String(item.team)]?.agents.push(item);
    });
    supports.forEach((item) => {
      if (item.team) base[String(item.team)]?.supports.push(item);
    });
    return base;
  }, [agents, chiefs, supports, teams]);

  const selectedSchedules = schedules.filter((item) => item.date === selectedDate);
  const detailSchedule = schedules.find((item) => String(item.id) === String(detailScheduleId));
  const detailRoster = detailSchedule?.members || { chiefs: [], agents: [], supports: [] };
  const detailPendingSwaps = (detailSchedule?.swap_requests || []).filter((swap) => swap.status === "PENDING");
  const swapSchedule = schedules.find((item) => String(item.id) === String(swapForm.schedule));
  const swapRoster = swapSchedule?.members || { chiefs: [], agents: [], supports: [] };
  const targetRoster = rostersByTeam[String(swapForm.target_team)] || { chiefs: [], agents: [], supports: [] };

  const loadSchedules = async () => {
    const params = new URLSearchParams({
      date_from: toISO(days[0]),
      date_to: toISO(days[days.length - 1]),
    }).toString();
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    const data = await api(`/shift-schedules/?${params}`);
    if (seq === requestSeq.current) {
      setSchedules(data.results || data);
    }
  };

  useEffect(() => {
    Promise.all([
      loadAll("/teams/"),
      loadAll("/chiefs/"),
      loadAll("/agents/"),
      loadAll("/supports/"),
    ]).then(([teamRows, chiefRows, agentRows, supportRows]) => {
      setTeams(teamRows);
      setChiefs(chiefRows);
      setAgents(agentRows);
      setSupports(supportRows);
    });
  }, []);

  useEffect(() => {
    loadSchedules().catch((err) => setMessage(err.message));
  }, [days]);

  const openDay = (date) => {
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
    const firstSchedule = scheduleId || schedules[0]?.id || "";
    if (!firstSchedule) {
      setMessage("Cadastre uma escala antes de solicitar troca.");
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
      setSwapMessage(action === "approve" ? "Troca aprovada." : "Troca rejeitada.");
    } catch (err) {
      setSwapMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteSchedule = async () => {
    if (!detailSchedule) return;
    if (!window.confirm(`Excluir a escala da equipe ${detailSchedule.team_name} em ${formatDateBR(detailSchedule.date)}?`)) {
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
        <button type="button" onClick={() => openSwapModal()}><Repeat2 size={17} /> Solicitar troca</button>
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
                    <strong>{schedule.team_name}</strong>
                    {(schedule.swap_requests || []).some((swap) => swap.status === "PENDING") && (
                      <b><AlertTriangle size={12} /> Troca</b>
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
              {teams.map((team) => {
                const roster = rostersByTeam[String(team.id)] || {};
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
                <h2>{detailSchedule.team_name}</h2>
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
                      <span>{swap.member_type === "CHIEF" ? "Chefe" : swap.member_type === "SUPPORT" ? "Apoio" : "Agente"} | {swap.schedule_team_name} para {swap.target_team_name}</span>
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
                  <strong>{group === "chiefs" ? "Chefes" : group === "agents" ? "Agentes" : "Apoio"}</strong>
                  {(detailRoster[group] || []).length ? (
                    <div className="shift-member-list">
                      {(detailRoster[group] || []).map((member) => (
                        <span key={`${group}-${member.id}`} className={member.swapped ? "swapped" : ""}>
                          {member.name}
                          {member.role && <small>{member.role}</small>}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p>Nenhum integrante cadastrado.</p>
                  )}
                </div>
              ))}
            </section>
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
                    {schedules.map((schedule) => (
                      <option key={schedule.id} value={schedule.id}>
                        {formatDateBR(schedule.date)} - {schedule.team_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Função</span>
                  <select value={swapForm.member_type} onChange={(event) => setSwapForm({ ...emptySwapForm(swapForm.schedule), member_type: event.target.value })}>
                    <option value="CHIEF">Chefe</option>
                    <option value="AGENT">Agente</option>
                    <option value="SUPPORT">Apoio</option>
                  </select>
                </label>
                <label>
                  <span>Quem sai</span>
                  <select value={swapForm.from_member_id} onChange={(event) => setSwapForm((current) => ({ ...current, from_member_id: event.target.value }))}>
                    <option value="">Selecione</option>
                    {sameTypeMembers(swapForm.member_type, swapRoster).map((member) => (
                      <option key={member.id} value={member.id}>{member.name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Equipe substituta</span>
                  <select value={swapForm.target_team} onChange={(event) => setSwapForm((current) => ({ ...current, target_team: event.target.value, to_member_id: "" }))}>
                    <option value="">Selecione</option>
                    {teams.filter((team) => String(team.id) !== String(swapSchedule?.team)).map((team) => (
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
                      <span>{swap.member_type === "CHIEF" ? "Chefe" : swap.member_type === "SUPPORT" ? "Apoio" : "Agente"} | {swap.schedule_team_name} para {swap.target_team_name}</span>
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
    </section>
  );
}

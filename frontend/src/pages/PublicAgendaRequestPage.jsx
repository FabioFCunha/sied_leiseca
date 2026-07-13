import { CalendarPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import soprinhoMascot from "../assets/soprinho-transparent.png";
import leiSecaLogo from "../assets/logo lei seca preto.jpg.jpeg";
import { useAuth } from "../context/AuthContext.jsx";

const actionTypes = [
  "Palestra",
  "Ação de educação/conscientização",
];

const ageRangeOptions = [
  "05 - 10 anos (ensino fundamental - anos iniciais)",
  "11 - 14 anos (ensino fundamental - anos finais)",
  "15 - 17 anos (ensino médio)",
  "acima de 18 anos - Adultos",
];

const participantRangeOptions = [
  { label: "30 a 50", quantity: 50 },
  { label: "51 a 100", quantity: 100 },
  { label: "100 a 200", quantity: 200 },
];

const accessibilityAccessOptions = [
  "Sim",
  "Não",
  "Não se aplica, pois será realizado no térreo",
];

const mediaEquipmentOptions = [
  "Datashow",
  "Tela de projeção",
  "TV",
  "Caixa de som",
  "Microfone",
  "Notebook",
  "Cabo HDMI",
  "Entrada para pen drive",
  "Acesso a internet",
];

const imageAuthorizationOptions = [
  "O requisitante da palestra acima identificado(a), com fundamento no art. 5º, X e XXVIII da Constituição Federal/1988, e no art. 18, da Lei 10.406, de 10/01/2002, AUTORIZA a Operação Lei Seca do Estado do Rio de Janeiro a utilizar as imagens, vídeos e/ou voz captadas durante a palestra promovida pela Operação Lei Seca, realizada na data solicitada neste formulário, ou em data posteriormente acordada, para fins de divulgação das atividades e propaganda, podendo, para tanto, reproduzi-la e/ou divulgá-la pela internet, mídia eletrônica, por jornais, revistas, folders; bem como por todo e qualquer material e veículo de comunicação, público e/ou privado, e por parceiros, com finalidade informativa e de utilidade pública, por tempo indeterminado. Declara ainda que não há nada a ser reclamado, a título de direitos conexos; referentes ao uso da imagem e/ou nome. A presente autorização é concedida a título gratuito.",
  "Outro",
];

const empty = {
  date: "",
  start_time: "",
  end_time: "",
  time_2: "",
  time_3: "",
  action_type: "",
  actions_count: "1",
  institution_location: "",
  requester_entity_kind: "",
  requester_entity_nature: "",
  cep: "",
  address: "",
  address_number: "",
  address_complement: "",
  neighborhood: "",
  city: "",
  state: "RJ",
  external_responsible: "",
  external_responsible_phone: "",
  external_email: "",
  contact_email: "",
  requester_role: "",
  audience: "",
  quantity: "",
  participant_range: "",
  age_ranges: "",
  accessibility_access: "",
  has_ramps: "",
  has_elevators: "",
  has_accessible_bathrooms: "",
  media_equipment: [],
  image_authorization: "",
  image_authorization_other: "",
  notes: "",
};

function optionList(options) {
  return options.map((option) => (
    <option key={option} value={option}>
      {option}
    </option>
  ));
}

function addHours(time, amount) {
  if (!time) return "";
  const [hours, minutes] = time.split(":").map(Number);
  const date = new Date(2000, 0, 1, hours, minutes);
  date.setHours(date.getHours() + amount);
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export default function PublicAgendaRequestPage({ internalRequest = false }) {
  const auth = useAuth();
  const user = auth?.user;
  const { token } = useParams();
  const editMode = Boolean(token);
  const [form, setForm] = useState(empty);
  const [message, setMessage] = useState("");
  const [successData, setSuccessData] = useState(null);
  const [cepMessage, setCepMessage] = useState("");
  const [dateMessage, setDateMessage] = useState("");
  const [cepLoading, setCepLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [protocol, setProtocol] = useState("");

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api(`/public/agenda-request/${token}/`)
      .then((data) => {
        setProtocol(data.protocol);
        setForm((current) => ({
          ...current,
          date: data.date || "",
          start_time: String(data.start_time || "").slice(0, 5),
          actions_count: String(data.actions_count || "1"),
          institution_location: data.institution_location || "",
          external_responsible: data.external_responsible || "",
          external_email: data.external_email || "",
        }));
      })
      .catch((err) => setMessage(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!form.date) {
      setDateMessage("");
      return;
    }
    const controller = new AbortController();
    let url = `/public/agenda-request/?date=${form.date}`;
    if (editMode && protocol) {
      url += `&agenda_id=${protocol}`;
    }
    api(url, { signal: controller.signal })
      .then((res) => {
        if (res.available === false && res.message) {
          setDateMessage(res.message);
        } else {
          setDateMessage("");
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setDateMessage("");
        }
      });
    return () => controller.abort();
  }, [form.date, editMode, protocol]);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));
  const updateActionsCount = (value) => {
    setForm((current) => ({
      ...current,
      actions_count: value,
      time_2: Number(value) >= 2 ? current.time_2 : "",
      time_3: Number(value) >= 3 ? current.time_3 : "",
    }));
  };

  const lookupCep = async () => {
    const cep = form.cep.replace(/\D/g, "");
    if (cep.length !== 8) {
      setCepMessage("Informe um CEP com 8 digitos.");
      return;
    }
    setCepLoading(true);
    setCepMessage("");
    try {
      const data = await api(`/public/cep/?cep=${cep}`, { redirectOnUnauthorized: false });
      setForm((current) => ({
        ...current,
        address: data.address || current.address,
        neighborhood: data.neighborhood || current.neighborhood,
        city: data.city || current.city,
        state: data.state || current.state,
        complement: data.complement || current.complement,
      }));
      setCepMessage("Endereco localizado. Complete o numero e o complemento, se houver.");
    } catch (err) {
      setCepMessage(err.message || "Nao foi possivel buscar o CEP agora.");
    } finally {
      setCepLoading(false);
    }
  };

  const toggleList = (field, value) => {
    setForm((current) => {
      const values = current[field].includes(value)
        ? current[field].filter((item) => item !== value)
        : [...current[field], value];
      return { ...current, [field]: values };
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    const isAcaoRua = form.requester_entity_kind === "Ação de Rua";
    if (editMode) {
      setLoading(true);
      setMessage("");
      try {
        const response = await api(`/public/agenda-request/${token}/`, {
          method: "PATCH",
          body: JSON.stringify({
            date: form.date,
            start_time: form.start_time,
            end_time: isAcaoRua ? addHours(form.start_time, 4) : addHours(form.start_time, 1),
            actions_count: form.actions_count === "" ? null : Number(form.actions_count),
            time_2: null,
            time_3: null,
          }),
        });
        setSuccessData({ detail: response.detail, protocol: response.protocol });
      } catch (err) {
        setMessage(err.message);
      } finally {
        setLoading(false);
      }
      return;
    }
    if (!form.age_ranges && form.requester_entity_kind !== "Ação de Rua") {
      setMessage("Selecione pelo menos uma faixa etária do público.");
      return;
    }
    if (form.requester_entity_kind !== "Ação de Rua") {
      if (!form.accessibility_access || !form.has_accessible_bathrooms) {
        setMessage("Responda todas as perguntas sobre acessibilidade do local.");
        return;
      }
    }
    if (form.requester_entity_kind !== "Ação de Rua" && !form.image_authorization) {
      setMessage("Selecione uma opção de autorização de uso de imagem.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const title = `${form.action_type || "Solicitação"} - ${form.institution_location || "Sem local"}`;
      const fullAddress = [
        form.address,
        form.address_number ? `nº ${form.address_number}` : "",
        form.address_complement,
      ].filter(Boolean).join(", ");
      const payload = {
        ...form,
        address: fullAddress,
        title,
        description: form.notes || title,
        requester_entity_type: `${form.requester_entity_kind} ${form.requester_entity_nature}`.trim(),
        image_authorization:
          form.image_authorization === "Outro"
            ? form.image_authorization_other
            : form.image_authorization,
        end_time: isAcaoRua ? addHours(form.start_time, 4) : addHours(form.start_time, 1),
        quantity: (isAcaoRua && !internalRequest) ? null : (form.quantity === "" ? null : Number(form.quantity)),
        actions_count: form.actions_count === "" ? null : Number(form.actions_count),
        time_2: null,
        time_3: null,
        age_ranges: isAcaoRua ? "" : form.age_ranges,
        media_equipment: form.media_equipment.join(", "),
        action_type: isAcaoRua ? "Ação de educação/conscientização" : form.action_type,
        participant_range: (isAcaoRua && !internalRequest) ? "" : form.participant_range,
        accessibility_access: isAcaoRua ? "" : form.accessibility_access,
        has_accessible_bathrooms: isAcaoRua ? "" : form.has_accessible_bathrooms,
      };
      delete payload.requester_entity_kind;
      delete payload.requester_entity_nature;
      delete payload.image_authorization_other;
      delete payload.cep;
      delete payload.address_number;
      delete payload.address_complement;
      const response = await api(internalRequest ? "/internal/agenda-request/" : "/public/agenda-request/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setForm(empty);
      setSuccessData({ detail: response.detail, protocol: response.protocol });
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (editMode) {
    return (
      <main className="public-page">
        <section className="public-form">
          <div className="public-header">
            <img className="public-mascot" src={soprinhoMascot} alt="Mascote da Operacao Lei Seca" />
            <div>
              <h1>Alterar data da solicitacao</h1>
              <p>{protocol ? `Protocolo #${protocol}` : "Carregando protocolo..."}</p>
            </div>
          </div>
          <form className="stack-form" onSubmit={submit}>
            <div className="form-section">
              <h3>Dados do protocolo</h3>
              <label className="field-label">
                <span>Solicitante</span>
                <input value={form.external_responsible} readOnly />
              </label>
              <label className="field-label">
                <span>E-mail</span>
                <input value={form.external_email} readOnly />
              </label>
              <label className="field-label">
                <span>Instituicao/Organizacao</span>
                <input value={form.institution_location} readOnly />
              </label>
            </div>
            <div className="form-section">
              <h3>Nova data solicitada</h3>
              <div className="split">
                <label className="field-label" style={{ flex: 1 }}>
                  <span>Data pretendida <b>*</b></span>
                  <input type="date" value={form.date} onChange={(event) => update("date", event.target.value)} required style={{ borderColor: dateMessage ? "var(--red)" : "" }} />
                  {dateMessage && <small style={{ color: "var(--red)", marginTop: "4px", display: "block", fontSize: "11px", fontWeight: "600" }}>{dateMessage}</small>}
                </label>
                <label className="field-label" style={{ flex: 1 }}>
                  <span>Horário pretendido de início</span>
                  <input type="time" value={form.start_time} onChange={(event) => update("start_time", event.target.value)} max="18:00" required />
                </label>
              </div>
              <div className="field-card">
                <strong>Quantidade de acoes pretendidas</strong>
                <div className="radio-list" role="radiogroup" aria-label="Quantidade de acoes pretendidas">
                  {["1", "2", "3"].map((option) => (
                    <label className="radio-option compact-radio option-tile" key={option}>
                      <input
                        type="radio"
                        name="actions_count"
                        checked={form.actions_count === option}
                        onChange={() => updateActionsCount(option)}
                        required
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            {message && <div className="alert">{message}</div>}
            <button disabled={loading}><CalendarPlus size={18} /> {loading ? "Enviando..." : "Confirmar alteração de data"}</button>
          </form>
        </section>
        {successData && (
          <div className="modal-backdrop">
            <article className="modal" style={{ textAlign: "center", padding: "40px 20px", maxWidth: "400px" }}>
              <h2 style={{ color: "var(--primary)", marginBottom: "16px" }}>Sucesso!</h2>
              <p style={{ fontSize: "16px", marginBottom: "24px", color: "var(--text)" }}>{successData.detail}</p>
              <div style={{ background: "#f6bd16", color: "#001338", padding: "12px 24px", borderRadius: "8px", display: "inline-block", fontWeight: "bold", fontSize: "18px", marginBottom: "32px" }}>
                Protocolo: {successData.protocol}
              </div>
              <div>
                <button onClick={() => setSuccessData(null)} style={{ width: "100%" }}>Fechar</button>
              </div>
            </article>
          </div>
        )}
      </main>
    );
  }

  return (
    <main className="public-page">
      <section className="public-form">
        <div className="public-header">
          <img className="public-mascot" src={soprinhoMascot} alt="Mascote da Operação Lei Seca" />
          <div>
            <h1>{internalRequest ? "Solicitação interna" : "Solicitação de evento"}</h1>
            <p>Preencha os dados da palestra, campanha ou ação educativa.</p>
          </div>
        </div>
        <div className="public-intro-card">
          <div style={{ textAlign: "center", marginBottom: "10px" }}>
            <img src={leiSecaLogo} alt="Operação Lei Seca" style={{ maxWidth: "250px", width: "100%" }} />
          </div>
          <div className="public-intro-title">SOLICITAÇÃO DE AGENDAMENTO</div>
          <p>
            A Operação Lei Seca atua sobre dois pilares: fiscalização e educação. A educação dispõe de palestras direcionadas
            ao público infantil, adolescente e adulto. As palestras e dinâmicas têm duração média de 60 (sessenta) minutos
            e são ministradas por uma equipe composta por integrantes da Operação Lei Seca, todos devidamente uniformizados.
          </p>
          <p><strong>Ressaltamos que nossa palestra é INTEIRAMENTE GRATUITA.</strong></p>
          <p><strong><em>Sua solicitação será avaliada e confirmada posteriormente através do e-mail cadastrado.</em></strong></p>
        </div>
        <form className="stack-form" onSubmit={submit}>
          <div className="form-section">
            <div className="split">
              <div className="field-card" style={{ flex: 1 }}>
                <strong>Tipo de solicitante: <b>*</b></strong>
                <div className="radio-list" role="radiogroup" aria-label="Tipo de solicitante">
                  {["Instituição de Ensino", "Empresa/Órgão", "Organização de evento", "Ação de Rua"].map((option) => (
                    <label className="radio-option compact-radio option-tile" key={option}>
                      <input
                        type="radio"
                        name="requester_entity_kind"
                        checked={form.requester_entity_kind === option}
                        onChange={() => {
                          const isAcaoRua = option === "Ação de Rua";
                          setForm((current) => ({
                            ...current,
                            requester_entity_kind: option,
                            ...(isAcaoRua && internalRequest && user ? {
                              external_responsible: user.full_name || "",
                              external_email: user.email || "",
                              external_responsible_phone: user.phone ? String(user.phone).replace(/\D/g, "") : "",
                              institution_location: user.sector_name || user.sector?.name || "Operação Lei Seca RJ",
                              requester_role: user.role || "Agente",
                            } : {})
                          }));
                        }}
                        required
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
              {form.requester_entity_kind !== "Ação de Rua" ? (
                <div className="field-card" style={{ flex: 1 }}>
                  <strong>Público ou Privado? <b>*</b></strong>
                  <div className="radio-list" role="radiogroup" aria-label="Natureza da entidade">
                    {["Público", "Privado"].map((option) => (
                      <label className="radio-option compact-radio option-tile" key={option}>
                        <input
                          type="radio"
                          name="requester_entity_nature"
                          checked={form.requester_entity_nature === option}
                          onChange={() => update("requester_entity_nature", option)}
                          required
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="field-card" style={{ flex: 1 }}>
                  <label className="field-label" style={{ marginBottom: 0 }}>
                    <strong>Nome do evento / Ação: <b>*</b></strong>
                    <input
                      type="text"
                      value={form.institution_location || ""}
                      onChange={(e) => update("institution_location", e.target.value)}
                      placeholder="Ex: Operação na Praia de Copacabana"
                      required
                      style={{ marginTop: "0.5rem" }}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>

          <div className="form-section">
            <h3>Dados da ação</h3>
            {form.requester_entity_kind !== "Ação de Rua" && (
              <div className="field-card selection-card">
                <strong>MODALIDADE PRETENDIDA <b>*</b></strong>
                <div className="radio-list" role="radiogroup" aria-label="Modalidade pretendida">
                  {actionTypes.map((option) => (
                    <label className="radio-option option-tile" key={option}>
                      <input
                        type="radio"
                        name="action_type"
                        checked={form.action_type === option}
                        onChange={() => update("action_type", option)}
                        required={form.requester_entity_kind !== "Ação de Rua"}
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="split">
              <label className="field-label" style={{ flex: 1 }}>
                <span>{form.requester_entity_kind === "Ação de Rua" ? "DATA" : "DATA PRETENDIDA"} <b>*</b></span>
                <input type="date" value={form.date} onChange={(event) => update("date", event.target.value)} required style={{ borderColor: dateMessage ? "var(--red)" : "" }} />
                {dateMessage && <small style={{ color: "var(--red)", marginTop: "4px", display: "block", fontSize: "11px", fontWeight: "600" }}>{dateMessage}</small>}
              </label>
              <label className="field-label" style={{ flex: 1 }}>
                <span>HORÁRIO PRETENDIDO / Informar horário pretendido de início <b>*</b></span>
                <input type="time" value={form.start_time} onChange={(event) => update("start_time", event.target.value)} max={internalRequest ? undefined : "18:00"} required />
              </label>
            </div>
            {form.requester_entity_kind === "Ação de Rua" && internalRequest && (
              <div className="field-card" style={{ marginTop: "16px" }}>
                <strong>Número aproximado de pessoas (para relatório/estatística) <b>*</b></strong>
                <input
                  type="number"
                  min="1"
                  placeholder="Ex: 50"
                  value={form.quantity}
                  onChange={(event) => update("quantity", event.target.value)}
                  required
                  style={{ marginTop: "8px", maxWidth: "200px" }}
                />
              </div>
            )}
          </div>

          {form.requester_entity_kind !== "Ação de Rua" && (
            <div className="form-section">
              <h3>Sobre a ação pretendida</h3>
              <div className="notice-card compact-notice">
                <strong>Período não superior a 4 (quatro) horas</strong>
              </div>
              <div className="field-card">
                <strong>Faixa etária do público <b>*</b></strong>
                <p>(em caso de mais de uma faixa etária, preencher outro formulário)</p>
                <div className="radio-list" role="radiogroup" aria-label="Faixa etária do público">
                  {ageRangeOptions.map((option) => (
                    <label className="radio-option compact-radio option-tile" key={option}>
                      <input
                        type="radio"
                        name="age_ranges"
                        checked={form.age_ranges === option}
                        onChange={() => update("age_ranges", option)}
                        required={form.requester_entity_kind !== "Ação de Rua"}
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="field-card">
                <strong>Número aproximado de participantes <b>*</b></strong>
                <div className="radio-list" role="radiogroup" aria-label="Número aproximado de participantes">
                  {participantRangeOptions.map((option) => (
                    <label className="radio-option compact-radio option-tile" key={option.label}>
                      <input
                        type="radio"
                        name="participant_range"
                        checked={form.participant_range === option.label}
                        onChange={() => setForm((current) => ({
                          ...current,
                          participant_range: option.label,
                          quantity: String(option.quantity),
                        }))}
                        required={form.requester_entity_kind !== "Ação de Rua"}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="form-section">
            <h3>Local</h3>
            <div className="cep-row">
              <label className="field-label">
                <span>CEP <b>*</b></span>
                <input
                  inputMode="numeric"
                  maxLength="9"
                  value={form.cep}
                  onBlur={() => form.cep && lookupCep()}
                  onChange={(event) => update("cep", event.target.value)}
                  required
                />
              </label>
              <button className="secondary cep-button" disabled={cepLoading} onClick={lookupCep} type="button">
                {cepLoading ? "Buscando..." : "Buscar CEP"}
              </button>
            </div>
            {cepMessage && <small className="field-hint">{cepMessage}</small>}
            <label className="field-label">
              <span>Endereço de realização <b>*</b></span>
              <input value={form.address} onChange={(event) => update("address", event.target.value)} required />
            </label>
            <div className="compact-grid">
              <label className="field-label">
                <span>Número <b>*</b></span>
                <input value={form.address_number} onChange={(event) => update("address_number", event.target.value)} required />
              </label>
              <label className="field-label">
                <span>Complemento</span>
                <input value={form.address_complement} onChange={(event) => update("address_complement", event.target.value)} />
              </label>
            </div>
            <div className="compact-grid">
              <label className="field-label">
                <span>Bairro <b>*</b></span>
                <input value={form.neighborhood} onChange={(event) => update("neighborhood", event.target.value)} required />
              </label>
              <label className="field-label">
                <span>Cidade <b>*</b></span>
                <input value={form.city} onChange={(event) => update("city", event.target.value)} required />
              </label>
            </div>
            <label className="field-label">
              <span>UF <b>*</b></span>
              <input maxLength="2" value={form.state} onChange={(event) => update("state", event.target.value.toUpperCase())} required />
            </label>
          </div>

          <div className="form-section">
            <h3>Informações do requisitante</h3>
            <label className="field-label">
              <span>Nome completo <b>*</b></span>
              <input value={form.external_responsible} onChange={(event) => update("external_responsible", event.target.value)} required />
            </label>
            <label className="field-label">
              <span>E-mail <b>*</b></span>
              <input type="email" value={form.external_email} onChange={(event) => update("external_email", event.target.value)} required />
            </label>
            <label className="field-label">
              <span>Telefone (com DDD) <b>*</b></span>
              <input value={form.external_responsible_phone} onChange={(event) => update("external_responsible_phone", event.target.value)} required />
            </label>
            {form.requester_entity_kind !== "Ação de Rua" && (
              <label className="field-label">
                <span>Instituição/Organização <b>*</b></span>
                <input value={form.institution_location} onChange={(event) => update("institution_location", event.target.value)} required />
              </label>
            )}
            
            <label className="field-label">
              <span>Cargo/Função do requisitante <b>*</b></span>
              <input value={form.requester_role} onChange={(event) => update("requester_role", event.target.value)} required />
            </label>
          </div>

          {form.requester_entity_kind !== "Ação de Rua" && (
            <div className="form-section">
              <h3>Sobre o local</h3>
              <div className="notice-card">
                <p>Por contar com agentes cadeirantes, necessitamos que o local esteja apto a recebê-los.</p>
                <p>
                  <b>A presença de itens de acessibilidade é condição essencial para a viabilidade técnica da palestra;</b>
                  {" "}a divergência entre as informações prestadas e a realidade do local poderá acarretar o
                  {" "}<b>cancelamento imediato do evento.</b>
                </p>
              </div>
              <div className="field-card selection-card">
                <div className="accessibility-question-list">
                  <div className="selection-group">
                    <span>Possui rampas ou elevador de acesso ao local da apresentação da palestra? <b>*</b></span>
                    <div className="radio-list" role="radiogroup" aria-label="Acesso por rampas ou elevador">
                      {accessibilityAccessOptions.map((option) => (
                        <label className="radio-option option-tile" key={option}>
                          <input
                            type="radio"
                            name="accessibility_access"
                            checked={form.accessibility_access === option}
                            onChange={() => update("accessibility_access", option)}
                            required={form.requester_entity_kind !== "Ação de Rua"}
                          />
                          <span>{option}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="selection-group">
                    <span>
                      Possui banheiro adaptado para cadeirante? <b>*</b><br />
                      <small>(Norma Técnica ABNT NBR 9050 - assento para cadeirante, barra de apoio, portas com vão superior a 80 cm, espaço para manobra da cadeira e diâmetro de pelo menos 1,5m)</small>
                    </span>
                    <div className="radio-list" role="radiogroup" aria-label="Banheiro adaptado para cadeirante?">
                      {["Sim", "Não"].map((option) => (
                        <label className="radio-option option-tile" key={option}>
                          <input
                            type="radio"
                            name="has_accessible_bathrooms"
                            checked={form.has_accessible_bathrooms === option}
                            onChange={() => update("has_accessible_bathrooms", option)}
                            required={form.requester_entity_kind !== "Ação de Rua"}
                          />
                          <span>{option}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {form.requester_entity_kind !== "Ação de Rua" && (
            <div className="form-section">
              <h3>Recursos disponíveis</h3>
              <div className="field-card resource-card">
                <strong>Recursos disponíveis no local</strong>
                <div className="choice-grid resource-grid">
                  {mediaEquipmentOptions.map((option) => (
                    <label className="checkbox option-tile" key={option}>
                      <input type="checkbox" checked={form.media_equipment.includes(option)} onChange={() => toggleList("media_equipment", option)} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="field-card resource-card">
                <strong>Autorização de uso de imagem <b>*</b></strong>
                <div className="radio-list image-auth-list" role="radiogroup" aria-label="Autorização de uso de imagem">
                  {imageAuthorizationOptions.map((option) => (
                    <label className="radio-option option-tile" key={option}>
                      <input
                        type="radio"
                        name="image_authorization"
                        checked={form.image_authorization === option}
                        onChange={() => update("image_authorization", option)}
                        required={form.requester_entity_kind !== "Ação de Rua"}
                      />
                      <span>{option === "Outro" ? "Outro:" : option}</span>
                      {option === "Outro" && (
                        <input
                          className="inline-other-input"
                          value={form.image_authorization_other}
                          onChange={(event) => update("image_authorization_other", event.target.value)}
                          required={form.image_authorization === "Outro"}
                          aria-label="Outra autorização de imagem"
                        />
                      )}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="form-section">
            <label className="field-label">
              <span>Comentários ou sugestões</span>
              <textarea value={form.notes} onChange={(event) => update("notes", event.target.value)} />
            </label>
          </div>

          {message && <div className="alert">{message}</div>}
          <button disabled={loading}><CalendarPlus size={18} /> {loading ? "Enviando..." : internalRequest ? "Registrar solicitação interna" : "Enviar solicitação"}</button>
        </form>
      </section>
      {successData && (
        <div className="modal-backdrop">
          <article className="modal" style={{ textAlign: "center", padding: "40px 20px", maxWidth: "400px" }}>
            <h2 style={{ color: "var(--primary)", marginBottom: "16px" }}>Sucesso!</h2>
            <p style={{ fontSize: "16px", marginBottom: "24px", color: "var(--text)" }}>{successData.detail}</p>
            <div style={{ background: "#f6bd16", color: "#001338", padding: "12px 24px", borderRadius: "8px", display: "inline-block", fontWeight: "bold", fontSize: "18px", marginBottom: "32px" }}>
              Protocolo: {successData.protocol}
            </div>
            <div>
              <button onClick={() => setSuccessData(null)} style={{ width: "100%" }}>Fechar e fazer nova solicitação</button>
            </div>
          </article>
        </div>
      )}
    </main>
  );
}

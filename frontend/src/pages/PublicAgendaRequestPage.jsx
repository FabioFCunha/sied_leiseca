import { CalendarPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import soprinhoMascot from "../assets/soprinho-transparent.png";

const actionTypes = [
  "Palestra Empresa",
  "Palestra Escola",
  "Ação educativa (Espaço interno)",
  "Palestra Virtual",
  "Palestra Presencial",
  "Campanha educativa/conscientização",
];

const entityTypes = [
  "Empresa Privada",
  "Escola Privada",
  "Escola Municipal",
  "Escola Estadual",
  "Órgão Público",
  "Escola Federal",
  "Empresa Pública",
  "ONG",
  "Fundação",
  "Sistema S",
  "Associação",
  "Hospital",
  "Universidade",
  "Outro",
];

const ageRangeOptions = [
  "04 até 8 anos",
  "09 até 13 anos",
  "14 até 17 anos",
  "acima de 18 anos",
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
  "Não se aplica por envolver crianças e adolescentes.",
  "Não autorizo o uso de imagem.",
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
  requester_entity_type: "",
  requester_entity_other: "",
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
  age_ranges: [],
  has_ramps: "",
  has_elevators: "",
  has_accessible_bathrooms: "",
  media_equipment: [],
  image_authorization: "",
  notes: "",
};

function optionList(options) {
  return options.map((option) => (
    <option key={option} value={option}>
      {option}
    </option>
  ));
}

function addOneHour(time) {
  if (!time) return "";
  const [hours, minutes] = time.split(":").map(Number);
  const date = new Date(2000, 0, 1, hours, minutes);
  date.setHours(date.getHours() + 1);
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export default function PublicAgendaRequestPage({ internalRequest = false }) {
  const { token } = useParams();
  const editMode = Boolean(token);
  const [form, setForm] = useState(empty);
  const [message, setMessage] = useState("");
  const [cepMessage, setCepMessage] = useState("");
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
      setCepMessage("Informe um CEP com 8 dígitos.");
      return;
    }
    setCepLoading(true);
    setCepMessage("");
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await response.json();
      if (data.erro) {
        setCepMessage("CEP não encontrado.");
        return;
      }
      setForm((current) => ({
        ...current,
        address: data.logradouro || current.address,
        neighborhood: data.bairro || current.neighborhood,
        city: data.localidade || current.city,
        state: data.uf || current.state,
      }));
      setCepMessage("Endereço localizado. Complete o número e o complemento, se houver.");
    } catch {
      setCepMessage("Não foi possível buscar o CEP agora.");
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
    if (editMode) {
      setLoading(true);
      setMessage("");
      try {
        const response = await api(`/public/agenda-request/${token}/`, {
          method: "PATCH",
          body: JSON.stringify({
            date: form.date,
            start_time: form.start_time,
            end_time: addOneHour(form.start_time),
            actions_count: form.actions_count === "" ? null : Number(form.actions_count),
            time_2: null,
            time_3: null,
          }),
        });
        setMessage(`${response.detail} Protocolo: ${response.protocol}`);
      } catch (err) {
        setMessage(err.message);
      } finally {
        setLoading(false);
      }
      return;
    }
    if (!form.age_ranges.length) {
      setMessage("Selecione pelo menos uma faixa etária do público.");
      return;
    }
    if (!form.has_ramps || !form.has_elevators || !form.has_accessible_bathrooms) {
      setMessage("Responda todas as perguntas sobre acessibilidade do local.");
      return;
    }
    if (!form.image_authorization) {
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
        requester_entity_type:
          form.requester_entity_type === "Outro"
            ? form.requester_entity_other
            : form.requester_entity_type,
        end_time: addOneHour(form.start_time),
        quantity: form.quantity === "" ? null : Number(form.quantity),
        actions_count: form.actions_count === "" ? null : Number(form.actions_count),
        time_2: null,
        time_3: null,
        age_ranges: form.age_ranges.join(", "),
        media_equipment: form.media_equipment.join(", "),
      };
      delete payload.requester_entity_other;
      delete payload.cep;
      delete payload.address_number;
      delete payload.address_complement;
      const response = await api(internalRequest ? "/internal/agenda-request/" : "/public/agenda-request/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setForm(empty);
      setMessage(`${response.detail} Protocolo: ${response.protocol}`);
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
                <label className="field-label">
                  <span>Data</span>
                  <input type="date" value={form.date} onChange={(event) => update("date", event.target.value)} required />
                </label>
                <label className="field-label">
                  <span>Horario pretendido de inicio</span>
                  <input type="time" value={form.start_time} onChange={(event) => update("start_time", event.target.value)} required />
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
            <button disabled={loading}><CalendarPlus size={18} /> {loading ? "Enviando..." : "Reenviar formulario"}</button>
          </form>
        </section>
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
          <div className="lei-seca-wordmark">
            <small>OPERAÇÃO</small>
            <strong>LEI SECA</strong>
          </div>
          <div className="public-intro-title">SOLICITAÇÃO DE AGENDAMENTO</div>
          <p>
            A palestra <strong><em>Mudança de comportamento na Sociedade</em></strong> tem duração média de 60 minutos
            e é ministrada por uma equipe composta por integrantes da Operação Lei Seca todos devidamente uniformizados.
          </p>
          <p><strong>Ressaltamos que nossa palestra é INTEIRAMENTE GRATUITA.</strong></p>
          <p><strong><em>Sua solicitação será avaliada e confirmada posteriormente através do e-mail cadastrado.</em></strong></p>
        </div>
        <form className="stack-form" onSubmit={submit}>
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
            <label className="field-label">
              <span>Instituição/Organização <b>*</b></span>
              <input value={form.institution_location} onChange={(event) => update("institution_location", event.target.value)} required />
            </label>
            <div className="field-card">
              <strong>Descrição da entidade solicitante <b>*</b></strong>
              <div className="radio-list" role="radiogroup" aria-label="Descrição da entidade solicitante">
                {entityTypes.map((option) => (
                  <label className="radio-option compact-radio option-tile" key={option}>
                    <input
                      type="radio"
                      name="requester_entity_type"
                      checked={form.requester_entity_type === option}
                      onChange={() => update("requester_entity_type", option)}
                      required
                    />
                    <span>{option === "Outro" ? "Outro:" : option}</span>
                    {option === "Outro" && (
                      <input
                        className="inline-other-input"
                        value={form.requester_entity_other}
                        onChange={(event) => update("requester_entity_other", event.target.value)}
                        required={form.requester_entity_type === "Outro"}
                        aria-label="Outra entidade solicitante"
                      />
                    )}
                  </label>
                ))}
              </div>
            </div>
            <label className="field-label">
              <span>Cargo/Função do requisitante <b>*</b></span>
              <input value={form.requester_role} onChange={(event) => update("requester_role", event.target.value)} required />
            </label>
          </div>

          <div className="form-section">
            <h3>Dados da ação</h3>
            <div className="field-card selection-card">
              <strong>Tipo de ação <b>*</b></strong>
              <div className="choice-grid selection-grid" role="radiogroup" aria-label="Tipo de ação">
                {actionTypes.map((option) => (
                  <label className="radio-option option-tile" key={option}>
                    <input
                      type="radio"
                      name="action_type"
                      checked={form.action_type === option}
                      onChange={() => update("action_type", option)}
                      required
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="split">
              <label className="field-label">
                <span>Data</span>
                <input type="date" value={form.date} onChange={(event) => update("date", event.target.value)} required />
              </label>
              <label className="field-label">
                <span>Horário pretendido de início <b>*</b></span>
                <input type="time" value={form.start_time} onChange={(event) => update("start_time", event.target.value)} required />
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3>Sobre a ação pretendida</h3>
            <div className="notice-card compact-notice">
              <strong>Período total de até 4 horas.</strong>
            </div>
            <div className="field-card">
              <strong>Quantidade de ações pretendidas <b>*</b></strong>
              <p><b>Exemplo:</b> Realização de 3 palestras para públicos distintos.</p>
              <div className="radio-list" role="radiogroup" aria-label="Quantidade de ações pretendidas">
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
            <label className="field-label">
              <span>Número aproximado de participantes <b>*</b></span>
              <small>Em caso de mais de uma ação, indicar a média por ação.</small>
              <input type="number" min="1" value={form.quantity} onChange={(event) => update("quantity", event.target.value)} required />
            </label>
            <div className="field-card">
              <strong>Faixa etária do público <b>*</b></strong>
              <div className="choice-grid">
                {ageRangeOptions.map((option) => (
                  <label className="checkbox option-tile" key={option}>
                    <input type="checkbox" checked={form.age_ranges.includes(option)} onChange={() => toggleList("age_ranges", option)} />
                    {option}
                  </label>
                ))}
              </div>
            </div>
          </div>

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
            <h3>Público e acessibilidade</h3>
            <div className="notice-card">
              <strong>SOBRE O LOCAL</strong>
              <p>Por contar com agentes cadeirantes, necessitamos que o local esteja apto a recebê-los.</p>
              <p>
                <b>A presença de itens de acessibilidade é condição essencial para a viabilidade técnica da palestra;</b>
                {" "}a divergência entre as informações prestadas e a realidade do local poderá acarretar o
                {" "}<b>cancelamento imediato do evento.</b>
              </p>
            </div>
            <div className="field-card selection-card">
              <strong>Condições de acessibilidade <b>*</b></strong>
              <div className="accessibility-grid">
                <div className="selection-group">
                  <span>Possui rampa?</span>
                  <div className="segmented-options" role="radiogroup" aria-label="Possui rampa?">
                    {["Sim", "Não"].map((option) => (
                      <label className="radio-option option-tile" key={option}>
                        <input
                          type="radio"
                          name="has_ramps"
                          checked={form.has_ramps === option}
                          onChange={() => update("has_ramps", option)}
                          required
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="selection-group">
                  <span>Possui elevador?</span>
                  <div className="segmented-options" role="radiogroup" aria-label="Possui elevador?">
                    {["Sim", "Não"].map((option) => (
                      <label className="radio-option option-tile" key={option}>
                        <input
                          type="radio"
                          name="has_elevators"
                          checked={form.has_elevators === option}
                          onChange={() => update("has_elevators", option)}
                          required
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="selection-group">
                  <span>Banheiro adaptado?</span>
                  <div className="segmented-options" role="radiogroup" aria-label="Banheiro adaptado?">
                    {["Sim", "Não"].map((option) => (
                      <label className="radio-option option-tile" key={option}>
                        <input
                          type="radio"
                          name="has_accessible_bathrooms"
                          checked={form.has_accessible_bathrooms === option}
                          onChange={() => update("has_accessible_bathrooms", option)}
                          required
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

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
                      required
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </div>
            <label className="field-label">
              <span>Comentários ou sugestões</span>
              <textarea value={form.notes} onChange={(event) => update("notes", event.target.value)} />
            </label>
          </div>

          {message && <div className="alert">{message}</div>}
          <button disabled={loading}><CalendarPlus size={18} /> {loading ? "Enviando..." : internalRequest ? "Registrar solicitação interna" : "Enviar solicitação"}</button>
        </form>
      </section>
    </main>
  );
}

import { Send } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";

import soprinhoMascot from "../assets/soprinho-transparent.png";
import leiSecaLogo from "../assets/logo lei seca preto.jpg.jpeg";

const fields = [
  ["audiovisual_resources", "Recursos áudio-visuais: apresentação (slides) e vídeos exibidos durante a palestra."],
  ["speaker_knowledge", "Clareza, didática e domínio do tema por parte do(a) palestrante."],
  ["wheelchair_testimony", "Depoimento dos cadeirantes."],
  ["workshops", "Dinâmicas/oficinas realizadas."],
  ["support_material", "Material de apoio às atividades."],
  ["punctuality", "Pontualidade da equipe."],
  ["team_enthusiasm", "Entusiasmo e dinamismo da equipe."],
  ["overall_rating", "Que nota daria de forma geral para a atividade."],
];

const empty = Object.fromEntries(fields.map(([key]) => [key, ""]));

export default function SatisfactionSurveyPage() {
  const { token } = useParams();
  const [survey, setSurvey] = useState(null);
  const [form, setForm] = useState({ ...empty, suggestion: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api(`/public/satisfaction-survey/${token}/`)
      .then(setSurvey)
      .catch((err) => setMessage(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, key === "suggestion" ? value : Number(value)])
      );
      const response = await api(`/public/satisfaction-survey/${token}/`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setMessage(response.detail);
    } catch (err) {
      setMessage(err.message);
    }
  };

  return (
    <main className="public-page">
      <section className="public-form">
        <div className="public-header">
          <img className="public-mascot" src={soprinhoMascot} alt="Mascote da Operação Lei Seca" />
          <div>
            <h1>Pesquisa de satisfação</h1>
            <p>{survey?.protocol ? `Protocolo #${survey.protocol}` : "Avaliação da palestra"}</p>
          </div>
        </div>
        <div className="public-intro-card">
          <div style={{ textAlign: "center", marginBottom: "10px" }}>
            <img src={leiSecaLogo} alt="Operação Lei Seca" style={{ maxWidth: "250px", width: "100%" }} />
          </div>
          <div className="public-intro-title">AVALIAÇÃO DE AGENDAMENTO</div>
          <p>Prezados,</p>
          <p>Solicitamos que avaliem a nossa palestra para que possamos aprimorar as ações futuras.</p>
        </div>
        {loading ? (
          <div className="dashboard-skeleton"><span /><span /></div>
        ) : (
          <form className="stack-form" onSubmit={submit}>
            {fields.map(([key, label]) => (
              <div className="field-card" key={key}>
                <strong>{label}</strong>
                <div className="rating-scale">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((rating) => (
                    <label className="rating-option" key={rating}>
                      <input
                        type="radio"
                        name={key}
                        value={rating}
                        checked={String(form[key]) === String(rating)}
                        onChange={() => setForm((current) => ({ ...current, [key]: String(rating) }))}
                        required
                      />
                      <span>{rating}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <label className="field-label">
              <span>Deixe aqui sua sugestão para aprimorarmos as ações educativas.</span>
              <textarea value={form.suggestion} onChange={(event) => setForm((current) => ({ ...current, suggestion: event.target.value }))} />
            </label>
            {message && <div className="alert">{message}</div>}
            <button><Send size={18} /> Enviar pesquisa</button>
          </form>
        )}
      </section>
    </main>
  );
}

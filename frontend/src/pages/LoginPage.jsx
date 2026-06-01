import { CalendarDays, ChevronRight, Eye, Lock, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@agenda.local");
  const [password, setPassword] = useState("Admin@12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = await api("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      login(payload);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const recover = async () => {
    setError("");
    try {
      const payload = await api("/auth/password-reset/", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setError(payload.detail);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <main className="login-page">
      <section className="login-panel lei-seca-login">
        <aside className="login-showcase" aria-label="Operação Lei Seca">
          <div className="showcase-title">
            <span>Operação</span>
            <strong>Lei Seca</strong>
            <em>Colabore</em>
          </div>
          <div className="showcase-copy">
            <p>Dirigir é sua <strong>responsabilidade.</strong></p>
            <p>A segurança é <strong>de todos!</strong></p>
          </div>
          <div className="showcase-pills">
            <span><ShieldCheck size={18} /> Fiscalização</span>
            <span><ShieldCheck size={18} /> Prevenção</span>
            <span><ShieldCheck size={18} /> Cidadania</span>
          </div>
        </aside>
        <form onSubmit={submit} className="login-form">
          <div className="login-mascot" />
          <div className="login-brand">
            <span className="login-calendar"><CalendarDays size={34} /></span>
            <div>
              <span className="eyebrow">Operação Lei Seca</span>
              <h1>Agenda Educação</h1>
              <p>Sistema de Agendamento de Ações e Atividades</p>
            </div>
          </div>
          <label>
            E-mail
            <span className="input-icon">
              <Mail size={18} />
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Digite seu e-mail" required />
            </span>
          </label>
          <label>
            Senha
            <span className="input-icon">
              <Lock size={18} />
              <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Digite sua senha" required />
              <Eye className="input-action-icon" size={20} />
            </span>
          </label>
          <div className="login-options">
            <label className="remember-option">
              <input type="checkbox" />
              Lembrar meu acesso
            </label>
            <button className="link-button" type="button" onClick={recover}>
              Esqueci minha senha
            </button>
          </div>
          {error && <div className="alert">{error}</div>}
          <button className="login-submit" disabled={loading}>
            <Lock size={22} />
            {loading ? "Entrando..." : "Entrar"}
            <ChevronRight size={24} />
          </button>
          <div className="login-restricted">
            <ShieldCheck size={22} />
            <span>Acesso restrito aos usuários autorizados.</span>
          </div>
        </form>
      </section>
    </main>
  );
}

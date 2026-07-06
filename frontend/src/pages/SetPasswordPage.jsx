import { Lock, Eye, EyeOff } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";

export default function SetPasswordPage() {
  const [params] = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const tokenData = useMemo(() => ({
    uid: params.get("uid"),
    token: params.get("token"),
  }), [params]);

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    if (password !== confirm) {
      setMessage("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      const payload = await api("/auth/set-password/", {
        method: "POST",
        body: JSON.stringify({ ...tokenData, password }),
      });
      setMessage(payload.detail);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-panel single set-password-panel">
        <div className="set-password-heading">
          <span className="eyebrow">SISTEMA INTEGRADO DA EDUCAÇÃO</span>
          <h1>Definir senha de acesso</h1>
          <p>Cadastre uma senha para entrar no sistema com seu e-mail.</p>
        </div>
        <form onSubmit={submit} className="login-form">
          <label>
            Nova senha
            <span className="input-icon">
              <Lock size={18} />
              <input value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? "text" : "password"} minLength="8" required />
              <button
                className="input-action-button"
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                title={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </span>
          </label>
          <label>
            Confirmar senha
            <span className="input-icon">
              <Lock size={18} />
              <input value={confirm} onChange={(e) => setConfirm(e.target.value)} type={showConfirm ? "text" : "password"} minLength="8" required />
              <button
                className="input-action-button"
                type="button"
                onClick={() => setShowConfirm((value) => !value)}
                aria-label={showConfirm ? "Ocultar senha" : "Mostrar senha"}
                title={showConfirm ? "Ocultar senha" : "Mostrar senha"}
              >
                {showConfirm ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </span>
          </label>
          {message && <div className="alert">{message}</div>}
          <button disabled={loading}>{loading ? "Salvando..." : "Cadastrar senha"}</button>
          <Link className="link-button" to="/login">Voltar ao login</Link>
        </form>
      </section>
    </main>
  );
}

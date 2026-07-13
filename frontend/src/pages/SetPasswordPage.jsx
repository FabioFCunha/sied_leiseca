import { Lock, Eye, EyeOff } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";

const passwordRules = [
  { test: (pw) => pw.length >= 8, label: "Mínimo de 8 caracteres" },
  { test: (pw) => /[A-Z]/.test(pw), label: "Pelo menos uma letra maiúscula" },
  { test: (pw) => /[a-z]/.test(pw), label: "Pelo menos uma letra minúscula" },
  { test: (pw) => /[0-9]/.test(pw), label: "Pelo menos um número" },
];

function validatePassword(pw) {
  return passwordRules.map((rule) => ({ ...rule, valid: rule.test(pw) }));
}

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

  const validation = validatePassword(password);
  const allValid = validation.every((r) => r.valid);

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    if (!allValid) {
      setMessage("A senha não atende a todos os requisitos.");
      return;
    }
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
          {password.length > 0 && (
            <ul style={{ listStyle: "none", padding: 0, margin: "4px 0 8px", fontSize: "13px" }}>
              {validation.map((rule) => (
                <li key={rule.label} style={{ color: rule.valid ? "var(--success, #16a34a)" : "var(--danger, #dc2626)", display: "flex", alignItems: "center", gap: "6px", lineHeight: "1.8" }}>
                  <span>{rule.valid ? "✓" : "✗"}</span> {rule.label}
                </li>
              ))}
            </ul>
          )}
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
          {confirm.length > 0 && password !== confirm && (
            <div style={{ color: "var(--danger, #dc2626)", fontSize: "13px", margin: "4px 0 8px" }}>
              ✗ As senhas não conferem.
            </div>
          )}
          {message && <div className="alert">{message}</div>}
          <button disabled={loading || !allValid}>{loading ? "Salvando..." : "Cadastrar senha"}</button>
          <Link className="link-button" to="/login">Voltar ao login</Link>
        </form>
      </section>
    </main>
  );
}

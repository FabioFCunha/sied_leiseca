import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { api } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";

export default function MobileLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
        redirectOnUnauthorized: false,
      });

      login(payload);
      navigate("/app/inicio", { replace: true });
    } catch (err) {
      setError(err.message || "Não foi possível entrar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      className="mobile-app"
      style={{
        minHeight: "100vh",
        backgroundColor: "#f1f5f9",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <form
        onSubmit={submit}
        style={{
          width: "100%",
          maxWidth: "420px",
          backgroundColor: "#ffffff",
          borderRadius: "16px",
          padding: "28px 22px",
          boxShadow: "0 4px 18px rgba(15, 23, 42, 0.08)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              margin: "0 auto 14px",
              borderRadius: "50%",
              backgroundColor: "#0a1e44",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: "700",
              fontSize: "22px",
            }}
          >
            SIED
          </div>

          <h1
            style={{
              margin: 0,
              color: "#0a1e44",
              fontSize: "22px",
            }}
          >
            SIED Operacional
          </h1>

          <p
            style={{
              margin: "6px 0 0",
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Entre com seu acesso institucional
          </p>
        </div>

        <label
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            marginBottom: "16px",
            color: "#334155",
            fontWeight: "600",
            fontSize: "14px",
          }}
        >
          E-mail

          <div style={{ position: "relative" }}>
            <Mail
              size={19}
              style={{
                position: "absolute",
                left: "12px",
                top: "14px",
                color: "#64748b",
              }}
            />

            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
              style={{
                boxSizing: "border-box",
                width: "100%",
                padding: "13px 12px 13px 42px",
                border: "1px solid #cbd5e1",
                borderRadius: "8px",
                fontSize: "16px",
              }}
            />
          </div>
        </label>

        <label
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            marginBottom: "20px",
            color: "#334155",
            fontWeight: "600",
            fontSize: "14px",
          }}
        >
          Senha

          <div style={{ position: "relative" }}>
            <Lock
              size={19}
              style={{
                position: "absolute",
                left: "12px",
                top: "14px",
                color: "#64748b",
              }}
            />

            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              style={{
                boxSizing: "border-box",
                width: "100%",
                padding: "13px 44px 13px 42px",
                border: "1px solid #cbd5e1",
                borderRadius: "8px",
                fontSize: "16px",
              }}
            />

            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              style={{
                position: "absolute",
                right: "8px",
                top: "7px",
                border: 0,
                background: "transparent",
                padding: "7px",
                color: "#64748b",
                cursor: "pointer",
              }}
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
        </label>

        {error && (
          <div
            style={{
              marginBottom: "16px",
              padding: "12px",
              borderRadius: "8px",
              backgroundColor: "#fee2e2",
              color: "#991b1b",
              fontSize: "14px",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          className="mobile-btn mobile-btn-primary"
          disabled={loading}
          style={{
            width: "100%",
            opacity: loading ? 0.7 : 1,
          }}
        >
          <Lock size={19} />
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}
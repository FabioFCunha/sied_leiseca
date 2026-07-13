import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Shield } from "lucide-react";

export default function LGPDModal({ onConsent }) {
  const { user, updateUser } = useAuth();
  const [policyText, setPolicyText] = useState("Carregando política de privacidade...");
  const [loading, setLoading] = useState(true);
  const [consenting, setConsenting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/auth/privacy-policy/", { redirectOnUnauthorized: false })
      .then((data) => {
        setPolicyText(data.policy);
        setLoading(false);
      })
      .catch((err) => {
        setError("Não foi possível carregar a política de privacidade.");
        setLoading(false);
      });
  }, []);

  const handleConsent = async () => {
    setConsenting(true);
    setError("");
    try {
      const data = await api("/auth/lgpd-consent/", { method: "POST" });
      const updatedUser = { ...user, lgpd_consent_at: data.lgpd_consent_at };
      updateUser(updatedUser);
      if (onConsent) onConsent(updatedUser);
    } catch (err) {
      setError(err.message || "Erro ao registrar consentimento.");
      setConsenting(false);
    }
  };

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      zIndex: 99999,
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      backdropFilter: "blur(4px)",
      padding: "20px"
    }}>
      <div style={{
        background: "var(--background)",
        borderRadius: "12px",
        width: "100%",
        maxWidth: "600px",
        maxHeight: "90vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        overflow: "hidden"
      }}>
        <div style={{ padding: "24px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "12px" }}>
          <Shield style={{ color: "var(--primary)" }} size={28} />
          <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: "600" }}>Aviso de Privacidade (LGPD)</h2>
        </div>
        
        <div style={{ padding: "24px", overflowY: "auto", flex: 1, fontSize: "14px", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
          <p style={{ marginBottom: "16px", fontWeight: "500", color: "var(--text)" }}>
            Para continuar utilizando o SIED, é necessário ler e aceitar nossa Política de Privacidade.
          </p>
          <div style={{ padding: "16px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text-muted)" }}>
            {loading ? "Aguarde..." : policyText}
          </div>
          {error && <div style={{ marginTop: "16px", color: "var(--danger)" }}>{error}</div>}
        </div>
        
        <div style={{ padding: "24px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={handleConsent}
            disabled={loading || consenting}
            style={{
              padding: "10px 24px",
              background: "var(--primary)",
              color: "white",
              border: "none",
              borderRadius: "6px",
              fontWeight: "500",
              cursor: (loading || consenting) ? "not-allowed" : "pointer",
              opacity: (loading || consenting) ? 0.7 : 1
            }}
          >
            {consenting ? "Registrando..." : "Li e Aceito"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { CheckCircle2, Clock, RefreshCw } from "lucide-react";

export default function VersionChecker() {
  const [showModal, setShowModal] = useState(false);
  const [newVersionData, setNewVersionData] = useState(null);

  useEffect(() => {
    // If the user previously clicked "Lembrar mais tarde" in this session, skip check.
    if (sessionStorage.getItem("version_update_snoozed")) {
      return;
    }

    let intervalId;

    const checkVersion = async () => {
      if (sessionStorage.getItem("version_update_snoozed")) return;
      
      try {
        const response = await fetch(`/version.json?t=${Date.now()}`, {
          cache: "no-store",
        });
        
        if (!response.ok) return;
        
        const data = await response.json();
        
        // __APP_VERSION__ is injected by Vite at build time
        if (data.version && data.version !== __APP_VERSION__) {
          setNewVersionData(data);
          setShowModal(true);
        }
      } catch (err) {
        // Silently ignore fetch errors
      }
    };

    // Check immediately on mount
    checkVersion();

    // Check every 3 minutes
    intervalId = setInterval(checkVersion, 3 * 60 * 1000);

    // Check when window gets focus
    window.addEventListener("focus", checkVersion);

    return () => {
      clearInterval(intervalId);
      window.removeEventListener("focus", checkVersion);
    };
  }, []);

  const handleUpdateNow = () => {
    window.location.reload();
  };

  const handleSnooze = () => {
    sessionStorage.setItem("version_update_snoozed", "true");
    setShowModal(false);
  };

  if (!showModal || !newVersionData) return null;

  return (
    <div className="modal-backdrop">
      <article className="modal" style={{ maxWidth: "500px" }}>
        <div className="modal-header">
          <h2>🚀 Nova versão disponível</h2>
        </div>
        
        <div style={{ marginTop: "1rem" }}>
          <p>Uma atualização do SIED foi publicada.</p>
          
          <div style={{ padding: "12px", background: "var(--pico-muted-border-color)", borderRadius: "8px", margin: "1rem 0" }}>
            <strong>Versão {newVersionData.version}</strong>
          </div>
          
          <h4>Novidades</h4>
          <ul style={{ listStyle: "none", padding: 0, margin: "1rem 0" }}>
            {(newVersionData.notes || []).map((note, index) => (
              <li key={index} style={{ display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "8px" }}>
                <CheckCircle2 size={16} color="var(--pico-primary)" style={{ flexShrink: 0, marginTop: "3px" }} />
                <span>{note}</span>
              </li>
            ))}
          </ul>
          
          <p style={{ fontSize: "14px", color: "var(--pico-muted-color)" }}>
            Para utilizar todas as melhorias é necessário atualizar a página.
          </p>
        </div>

        <div className="review-actions" style={{ justifyContent: "flex-end", marginTop: "1.5rem" }}>
          <button type="button" className="secondary" onClick={handleSnooze} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={16} /> Lembrar mais tarde
          </button>
          <button type="button" onClick={handleUpdateNow} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <RefreshCw size={16} /> Atualizar agora
          </button>
        </div>
      </article>
    </div>
  );
}

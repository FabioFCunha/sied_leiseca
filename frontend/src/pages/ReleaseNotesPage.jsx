export default function ReleaseNotesPage() {
  const versionData = window.__APP_VERSION_DATA__ || { history: [] };
  const history = versionData.history || [];

  return (
    <div style={{ padding: "16px", maxWidth: "800px", margin: "0 auto" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ marginBottom: "0.5rem" }}>Novidades do Sistema</h1>
        <p style={{ color: "var(--pico-muted-color)", margin: 0 }}>
          Acompanhe as atualizações e melhorias lançadas no SIED.
        </p>
      </header>

      {history.length === 0 ? (
        <p>Nenhuma nota de versão disponível.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          {history.map((release, index) => (
            <article key={index} style={{ margin: 0 }}>
              <header style={{ padding: "1rem", background: index === 0 ? "rgba(246, 189, 22, 0.1)" : "var(--pico-card-sectioning-background-color)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                    Versão {release.version}
                    {index === 0 && (
                      <span style={{ fontSize: "11px", background: "var(--pico-primary)", color: "#fff", padding: "2px 8px", borderRadius: "12px" }}>Atual</span>
                    )}
                  </h3>
                  <span style={{ color: "var(--pico-muted-color)", fontSize: "14px" }}>{release.releaseDate}</span>
                </div>
              </header>
              <div style={{ padding: "1rem" }}>
                <ul style={{ margin: 0, paddingLeft: "20px" }}>
                  {(release.notes || []).map((note, idx) => (
                    <li key={idx} style={{ marginBottom: "8px" }}>{note}</li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

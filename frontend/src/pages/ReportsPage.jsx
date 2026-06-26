import { Eye, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { formatDateBR } from "../utils/date.js";
import { buildPreview, reportName } from "../utils/reportPreview.js";

export default function ReportsPage() {
  const [techReports, setTechReports] = useState([]);
  const [techFilters, setTechFilters] = useState({ protocol: "", team: "", date: "" });
  const [pendingTechFilters, setPendingTechFilters] = useState({ protocol: "", team: "", date: "" });
  const [previewModal, setPreviewModal] = useState(null);

  const loadTecnico = () => {
    const params = new URLSearchParams({ page_size: "1000" });
    Object.entries(techFilters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    api(`/education-reports/?${params.toString()}`)
      .then((data) => {
        const results = data?.results || data;
        setTechReports(Array.isArray(results) ? results : []);
      })
      .catch((err) => {
        console.error("Erro ao carregar relatórios:", err);
        setTechReports([]);
      });
  };

  useEffect(() => {
    loadTecnico();
  }, [techFilters]);

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Relatórios Técnicos</h1>
          <p>Visão geral unificada dos relatórios e execuções técnicas.</p>
        </div>
      </div>

      <div style={{ animation: "fadeIn 0.4s ease" }}>
        <div className="filters glass-card" style={{ marginBottom: 24, display: 'flex', gap: 16 }}>
          <div className="filter-field">
            <span>Protocolo</span>
            <input placeholder="Ex: 123" value={pendingTechFilters.protocol} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, protocol: e.target.value })} />
          </div>
          <div className="filter-field">
            <span>Equipe</span>
            <input placeholder="Ex: E1" value={pendingTechFilters.team} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, team: e.target.value })} />
          </div>
          <div className="filter-field">
            <span>Data</span>
            <input type="date" value={pendingTechFilters.date} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, date: e.target.value })} />
          </div>
          <div style={{ alignSelf: 'flex-end' }}>
            <button onClick={() => setTechFilters(pendingTechFilters)}>Pesquisar</button>
          </div>
        </div>

        <div className="premium-table-wrap">
          <h2>Relatórios Técnicos Registrados</h2>
          <table>
            <thead>
              <tr>
                <th>Protocolo</th>
                <th>Nome da Equipe</th>
                <th>Data</th>
                <th>Status</th>
                <th>Ações Realizadas</th>
                <th style={{ width: 100 }}>Detalhes</th>
              </tr>
            </thead>
            <tbody>
              {techReports.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 32 }}>Nenhum relatório encontrado.</td></tr>
              )}
              {techReports.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.agenda ? `#${r.agenda}` : "-"}</strong></td>
                  <td>{reportName(r)}</td>
                  <td>{formatDateBR(r.operation_date)}</td>
                  <td>
                    <span style={{ 
                      background: r.status === "SUBMITTED" ? "var(--success)" : "var(--warning)", 
                      color: "#fff", padding: "4px 8px", borderRadius: 4, fontSize: 11, fontWeight: "bold" 
                    }}>
                      {r.status === "SUBMITTED" ? "ENVIADO" : "RASCUNHO"}
                    </span>
                  </td>
                  <td>{r.actions_count || 0} ações</td>
                  <td>
                    <button className="secondary icon-button" onClick={() => setPreviewModal(r)} title="Visualizar">
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {previewModal && (
        <div className="modal-overlay" onClick={() => setPreviewModal(null)}>
          <div className="premium-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header-premium">
              <h2>Detalhes do Relatório</h2>
              <button className="secondary icon-button" onClick={() => setPreviewModal(null)}><X size={20} /></button>
            </div>
            <div className="modal-body-premium">
              <pre>{buildPreview(previewModal)}</pre>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

const escapeHtml = (text) => {
  const div = document.createElement("div");
  div.innerText = String(text ?? "");
  return div.innerHTML;
};

const buildTableRows = (rows) => rows.map(row => `<tr><td>${escapeHtml(row.label)}</td><td class="value">${escapeHtml(row.value)}</td></tr>`).join("");
const buildFilterRows = (filters) => filters.map(filter => `<div class="filter-item"><span>${escapeHtml(filter.label)}</span><strong>${escapeHtml(filter.value)}</strong></div>`).join("");
const integer = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "Público total"], ["AUDIENCE - PALESTRAS", "Público em palestras"], ["AUDIENCE - ACOES", "Público em ações"],
  ["LECTURES - Geral", "Palestra"], ["ACTION - Empresa", "Empresa"], ["ACTION - Escola", "Escola"], ["ACTION - Universidade", "Universidade"],
  ["STREET_ACTIONS - Geral", "Ações"], ["ACTION - Bares", "Bares/Restaurantes"], ["ACTION - Pedágio", "Pedágio"], ["ACTION - Praças Esportivas", "Praças Esportivas"],
  ["ACTION - Praia", "Praia"], ["ACTION - Eventos", "Eventos"], ["ACTION - Shopping", "Shopping/Centro Comerciais"], ["ACTION - Praças/Parques Públicos", "Praças/Parques Públicos"], ["ACTION - Pontos turísticos", "Pontos Turísticos"],
  ["MATERIAL - Geral", "Materiais de divulgação"], ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];

export function generateStatisticsPdf({ viewModel, filters, issuedAt, logoUrl }) {
  if (!viewModel || !viewModel.demand || !viewModel.displaySummary) {
    throw new Error("Dados estatísticos incompletos para gerar o PDF.");
  }

  const {
    demand,
    displaySummary,
    dailySeries,
    categoryData,
    ageRows,
    requesterRows,
    administrativeDemandRows,
    heatmapValues,
    municipalities,
    teams,
    annual,
    insights,
    awaitingExecution,
    reportsWithoutPublic
  } = viewModel;

  const appliedFilters = [
    { label: "Período", value: `${filters.date_from} a ${filters.date_to}` },
    { label: "Município", value: filters.municipality || "Todos" },
    { label: "Equipe", value: filters.team || "Todos" },
    { label: "Categoria", value: filters.entity || "Todas" },
  ];

  const renderSimpleTable = (data, nameKey, valueKey, valueLabel) => {
    if (!data || data.length === 0) return `<tr><td colspan="2" class="empty-state">Nenhum dado encontrado</td></tr>`;
    return data.map(row => `<tr><td>${escapeHtml(row[nameKey])}</td><td class="value">${escapeHtml(row[valueKey])}</td></tr>`).join("");
  };

  const renderDetailedTable = (data, nameKey) => {
    if (!data || data.length === 0) return `<tr><td colspan="3" class="empty-state">Nenhum dado encontrado</td></tr>`;
    return data.map(row => `<tr>
        <td>${escapeHtml(row[nameKey])}</td>
        <td class="value">${escapeHtml(row.actionsLabel)}</td>
        <td class="value">${escapeHtml(row.percentageLabel)}</td>
      </tr>`).join("");
  };

  const weekDays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const hourSlots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00"];

  return `<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <title>Relatório Estatístico Institucional</title>
    <style>
      @page {
        size: A4;
        margin: 20mm 16mm 22mm;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family: "Segoe UI", Arial, sans-serif;
        color: #10213d;
        background: #ffffff;
      }
      .page {
        width: 100%;
      }
      .header {
        display: flex;
        align-items: center;
        gap: 18px;
        background: #0f2f67;
        color: #ffffff;
        padding: 18px 20px;
        border-radius: 14px;
        margin-bottom: 14px;
      }
      .header img {
        width: 86px;
        height: auto;
        object-fit: contain;
        flex: 0 0 auto;
      }
      .header-text {
        min-width: 0;
      }
      .eyebrow {
        display: block;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        opacity: 0.86;
        margin-bottom: 6px;
      }
      h1 {
        margin: 0;
        font-size: 24px;
        line-height: 1.2;
      }
      .header-subtitle {
        margin: 6px 0 0;
        font-size: 13px;
        line-height: 1.5;
        opacity: 0.92;
      }
      .meta {
        margin-top: 8px;
        font-size: 12.5px;
        line-height: 1.6;
      }
      .filters-box {
        border: 1px solid #d4dce8;
        background: #f8fbff;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 16px;
      }
      .filters-box h2 {
        margin: 0 0 10px;
        font-size: 14px;
        color: #0f2f67;
      }
      .filters-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 16px;
      }
      .filter-item span {
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #51627f;
        margin-bottom: 3px;
      }
      .filter-item strong {
        display: block;
        font-size: 13px;
        color: #10213d;
      }
      .section {
        margin-bottom: 16px;
        page-break-inside: avoid;
        break-inside: avoid;
      }
      .section h2 {
        margin: 0 0 10px;
        font-size: 16px;
        color: #0f2f67;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
      }
      thead {
        display: table-header-group;
      }
      tr {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      th, td {
        border: 1px solid #d4dce8;
        padding: 8px 10px;
        vertical-align: top;
      }
      th {
        background: #eef3fb;
        color: #0f2f67;
        text-align: left;
        font-weight: 700;
      }
      tbody tr:nth-child(even) {
        background: #f7f9fc;
      }
      .value {
        text-align: right;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
      }
      .empty-state {
        text-align: center;
        color: #6b7b95;
        font-style: italic;
      }
      .grid-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .insights-box {
        border: 1px solid #d4dce8;
        background: #f8fbff;
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 13px;
        line-height: 1.65;
      }
      .insights-box p {
        margin: 0 0 8px 0;
      }
      .insights-box p:last-child {
        margin: 0;
      }
      
      .heatmap-table th {
          font-size: 10px;
          padding: 4px;
          text-align: center;
      }
      .heatmap-table td {
          font-size: 10px;
          padding: 4px;
          text-align: center;
      }

      @media print {
        .section,
        .filters-box,
        .grid-layout > div {
          break-inside: avoid;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <header class="header">
        <img src="${logoUrl}" alt="Lei Seca" />
        <div class="header-text">
          <span class="eyebrow">LEI SECA – EDUCAÇÃO</span>
          <h1>RELATÓRIO ESTATÍSTICO INSTITUCIONAL</h1>
          <p class="header-subtitle">Sistema Integrado da Educação – SIED</p>
          <div class="meta">
            <div><strong>Período:</strong> ${escapeHtml(filters.date_from)} a ${escapeHtml(filters.date_to)}</div>
            <div><strong>Data de emissão:</strong> ${escapeHtml(issuedAt)}</div>
          </div>
        </div>
      </header>

      <section class="filters-box">
        <h2>Filtros aplicados</h2>
        <div class="filters-grid">${buildFilterRows(appliedFilters)}</div>
      </section>

      <section class="section">
        <h2>01 — Síntese dos Indicadores</h2>
        <table>
          <thead>
            <tr><th>Indicador</th><th class="value">Valor</th></tr>
          </thead>
          <tbody>
            <tr><td>Público alcançado</td><td class="value">${integer(displaySummary["AUDIENCE - Geral"])}</td></tr>
            <tr><td>Público previsto</td><td class="value">${integer(displaySummary.FUTURE_PUBLIC)}</td></tr>
            <tr><td>Palestras realizadas</td><td class="value">${integer(displaySummary["LECTURES - Geral"])}</td></tr>
            <tr><td>Ações de rua</td><td class="value">${integer(displaySummary["STREET_ACTIONS - Geral"])}</td></tr>
            <tr><td>Materiais distribuídos</td><td class="value">${integer(displaySummary["MATERIAL - Geral"])}</td></tr>
            <tr><td>Revistinhas distribuídas</td><td class="value">${integer(displaySummary["MATERIAL - Soprinho"])}</td></tr>
            <tr><td>Solicitações internas</td><td class="value">${integer(displaySummary.INTERNAL_REQUESTS)}</td></tr>
            <tr><td>Solicitações públicas</td><td class="value">${integer(displaySummary.PUBLIC_REQUESTS)}</td></tr>
          </tbody>
        </table>
      </section>

      <section class="section">
        <h2>02 — Produção x Demanda</h2>
        <table>
          <thead>
            <tr><th>Etapa</th><th class="value">Quantidade</th></tr>
          </thead>
          <tbody>
            <tr><td>Solicitações recebidas</td><td class="value">${integer(demand.total)}</td></tr>
            <tr><td>Solicitações aprovadas</td><td class="value">${integer(demand.approved)}</td></tr>
            <tr><td>Ações executadas</td><td class="value">${integer(demand.executed)}</td></tr>
            <tr><td>Aguardando execução</td><td class="value">${integer(awaitingExecution)}</td></tr>
            <tr><td>Canceladas/Recusadas</td><td class="value">${integer(demand.cancelled + demand.refused)}</td></tr>
          </tbody>
        </table>
      </section>

      <div class="grid-layout">
        <section class="section">
          <h2>03 — Evolução Diária</h2>
          <table>
            <thead>
              <tr><th>Data</th><th class="value">Ações</th><th class="value">Público</th></tr>
            </thead>
            <tbody>
              ${dailySeries.length > 0 ? dailySeries.map(row => `<tr><td>${escapeHtml(row.day)}</td><td class="value">${integer(row.actions)}</td><td class="value">${integer(row.audience)}</td></tr>`).join("") : `<tr><td colspan="3" class="empty-state">Nenhum dado encontrado</td></tr>`}
            </tbody>
          </table>
        </section>

        <div>
            <section class="section">
            <h2>04 — Ações de Rua</h2>
            <table>
                <thead>
                <tr><th>Categoria</th><th class="value">Ações</th><th class="value">%</th></tr>
                </thead>
                <tbody>${renderDetailedTable(categoryData, 'label')}</tbody>
            </table>
            </section>
            
            <section class="section">
            <h2>05 — Demandas Administrativas</h2>
            <table>
                <thead>
                <tr><th>Categoria</th><th class="value">Ações</th><th class="value">%</th></tr>
                </thead>
                <tbody>${renderDetailedTable(administrativeDemandRows, 'label')}</tbody>
            </table>
            </section>
        </div>
      </div>

      <div class="grid-layout">
        <section class="section">
          <h2>06 — Perfil Institucional</h2>
          <table>
            <thead>
              <tr><th>Solicitante</th><th class="value">Ações</th><th class="value">%</th></tr>
            </thead>
            <tbody>${renderDetailedTable(requesterRows, 'label')}</tbody>
          </table>
        </section>

        <section class="section">
          <h2>Faixa Etária do Público</h2>
          <table>
            <thead>
              <tr><th>Faixa</th><th class="value">Ações</th><th class="value">%</th></tr>
            </thead>
            <tbody>${renderDetailedTable(ageRows, 'label')}</tbody>
          </table>
        </section>
      </div>

      <section class="section">
        <h2>07 — Distribuição por Dia e Horário</h2>
        <table class="heatmap-table">
          <thead>
            <tr>
              <th>Dia</th>
              ${hourSlots.map(slot => `<th>${slot}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${weekDays.map((day, dayIndex) => `
              <tr>
                <td><strong>${day}</strong></td>
                ${hourSlots.map(slot => {
                  const val = heatmapValues.get(dayIndex + '-' + slot) || 0;
                  return `<td>${val > 0 ? val : ''}</td>`;
                }).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>

      <div class="grid-layout">
        <section class="section">
          <h2>08 — Indicadores Geográficos</h2>
          <table>
            <thead>
              <tr><th>Município</th><th class="value">Ações</th><th class="value">Público</th></tr>
            </thead>
            <tbody>
              ${municipalities.length > 0 ? municipalities.map(row => `<tr><td>${escapeHtml(row.agenda__city)}</td><td class="value">${escapeHtml(row.actionsLabel)}</td><td class="value">${escapeHtml(row.audienceLabel)}</td></tr>`).join("") : `<tr><td colspan="3" class="empty-state">Nenhum dado encontrado</td></tr>`}
            </tbody>
          </table>
        </section>

        <section class="section">
          <h2>09 — Ranking Operacional</h2>
          <table>
            <thead>
              <tr><th>Equipe</th><th class="value">Ações</th><th class="value">Público</th></tr>
            </thead>
            <tbody>
              ${teams.length > 0 ? teams.map(row => `<tr><td>${escapeHtml(row.team)}</td><td class="value">${escapeHtml(row.actionsLabel)}</td><td class="value">${escapeHtml(row.audienceLabel)}</td></tr>`).join("") : `<tr><td colspan="3" class="empty-state">Nenhum dado encontrado</td></tr>`}
            </tbody>
          </table>
        </section>
      </div>
      
      <section class="section">
        <h2>Insights Automáticos</h2>
        <div class="insights-box">
          ${insights.map(insight => `<p>${escapeHtml(insight)}</p>`).join("")}
        </div>
      </section>

      <section class="section">
        <h2>10 — Série Histórica Institucional</h2>
        <table>
          <thead>
            <tr>
              <th>Indicador</th>
              ${annual.map(row => `<th>${row.year}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${HISTORICAL_ROWS.map(([key, label]) => `
              <tr>
                <td>${label}</td>
                ${annual.map(row => `<td class="value">${integer(row[key])}</td>`).join("")}
              </tr>
            `).join("")}
          </tbody>
        </table>
      </section>
    </main>
    <script>
      window.addEventListener("load", () => {
        window.focus();
        window.print();
      }, { once: true });
    </script>
  </body>
</html>`;
}

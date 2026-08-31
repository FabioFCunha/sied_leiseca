import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { ANNUAL_TABLE_GROUPS } from "./statisticsAnnualTable.js";

// ── Helper: Load image as base64 for jsPDF ───────────────────────────────
function loadImageAsBase64(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = reject;
    img.src = url;
  });
}

// ── Design Tokens (shared with reportPdfGenerator) ───────────────────────
const NAVY        = [10, 30, 68];
const NAVY_LIGHT  = [20, 55, 110];
const GRAY_900    = [30, 30, 30];
const GRAY_600    = [100, 100, 100];
const GRAY_300    = [190, 190, 195];
const GRAY_100    = [242, 243, 245];
const ACCENT_GOLD = [180, 150, 60];
const WHITE       = [255, 255, 255];
const MARGIN_L    = 15;
const MARGIN_R    = 15;

const integer = (value) =>
  Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });

// ── Historical indicator rows (labels only) ──────────────────────────────
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "Público total"],
  ["AUDIENCE - PALESTRAS", "Público em palestras"],
  ["AUDIENCE - ACOES", "Público em ações"],
  ["LECTURES - Geral", "Palestra"],
  ["ACTION - Empresa", "Empresa"],
  ["ACTION - Escola", "Escola"],
  ["ACTION - Universidade", "Universidade"],
  ["STREET_ACTIONS - Geral", "Ações"],
  ["ACTION - Bares", "Bares/Restaurantes"],
  ["ACTION - Pedágio", "Pedágio"],
  ["ACTION - Praças Esportivas", "Praças Esportivas"],
  ["ACTION - Praia", "Praia"],
  ["ACTION - Eventos", "Eventos"],
  ["ACTION - Shopping", "Shopping/Centro Comerciais"],
  ["ACTION - Praças/Parques Públicos", "Praças/Parques Públicos"],
  ["ACTION - Pontos turísticos", "Pontos Turísticos"],
  ["MATERIAL - Geral", "Materiais de divulgação"],
  ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];

/**
 * Generates a real PDF file for the Statistics module.
 *
 * This function receives a pre-computed viewModel (from buildStatisticsViewModel)
 * and renders it into a jsPDF document. It performs NO calculations, NO API calls,
 * and has NO dependency on filteredAgendas or raw data.
 *
 * @param {Object} params
 * @param {Object} params.viewModel - The consolidated statistics view model.
 * @param {Object} params.filters - The applied filter values.
 * @param {Date}   params.issuedAt - The date/time of emission.
 * @param {string} params.logoUrl - The URL to the institutional logo.
 * @param {boolean} [params.openInNewTab=true] - Whether to open in a new tab or download.
 */
export async function generateStatisticsPdf({
  viewModel,
  filters,
  issuedAt,
  logoUrl,
  openInNewTab = true,
}) {
  // ── Contract barrier ─────────────────────────────────────────────────
  if (!viewModel || !viewModel.demand || !viewModel.displaySummary) {
    throw new Error(
      "Dados estatísticos incompletos para gerar o PDF. Aguarde o carregamento completo do painel."
    );
  }

  // ── Destructure viewModel (display-only, no computation) ─────────────
  const {
    demand,
    displaySummary,
    awaitingExecution,
    dailySeries,
    categoryData,
    ageRows,
    requesterRows,
    administrativeDemandRows,
    heatmapValues,
    municipalities,
    teams,
    insights,
    annual,
  } = viewModel;

  // ── Initialise jsPDF ────────────────────────────────────────────────
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.width;
  const pageHeight = doc.internal.pageSize.height;
  const CONTENT_W = pageWidth - MARGIN_L - MARGIN_R;

  let sectionCounter = 0;

  // ── Load logo ──────────────────────────────────────────────────────
  let logoBase64;
  try {
    logoBase64 = await loadImageAsBase64(logoUrl);
  } catch (_) {
    logoBase64 = null;
  }

  // ── Format helpers ─────────────────────────────────────────────────
  const issuedDate =
    issuedAt instanceof Date ? issuedAt : new Date(issuedAt || Date.now());
  const issuedStr = `${issuedDate.toLocaleDateString(
    "pt-BR"
  )} às ${issuedDate.toLocaleTimeString("pt-BR")}`;
  const periodFrom = filters.date_from || "—";
  const periodTo = filters.date_to || "—";

  // ── Utility: horizontal rule ───────────────────────────────────────
  const drawRule = (y, color = GRAY_300, thickness = 0.3) => {
    doc.setDrawColor(...color);
    doc.setLineWidth(thickness);
    doc.line(MARGIN_L, y, pageWidth - MARGIN_R, y);
  };

  // ── Utility: section header (numbered badge) ───────────────────────
  const drawSectionHeader = (title, y) => {
    sectionCounter++;
    const num = String(sectionCounter).padStart(2, "0");

    if (y > pageHeight - 30) {
      doc.addPage();
      y = 20;
    }

    doc.setFillColor(...NAVY);
    doc.roundedRect(MARGIN_L, y - 4.5, 9, 6, 1, 1, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(...WHITE);
    doc.text(num, MARGIN_L + 4.5, y, { align: "center" });

    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.setTextColor(...NAVY);
    doc.text(title, MARGIN_L + 12, y);

    drawRule(y + 2, NAVY_LIGHT, 0.5);
    return y + 7;
  };

  // ── Utility: ensure space or page-break ────────────────────────────
  const ensureSpace = (needed, currentY) => {
    if (currentY > pageHeight - needed - 20) {
      doc.addPage();
      return 20;
    }
    return currentY;
  };

  // ── Shared autoTable styles ────────────────────────────────────────
  const gridTableDefaults = {
    theme: "grid",
    headStyles: {
      fillColor: NAVY,
      textColor: WHITE,
      fontStyle: "bold",
      fontSize: 8.5,
      cellPadding: 3,
    },
    styles: {
      fontSize: 8.5,
      cellPadding: 2.5,
      textColor: GRAY_900,
      overflow: "linebreak",
    },
    alternateRowStyles: { fillColor: GRAY_100 },
    tableLineColor: GRAY_300,
    tableLineWidth: 0.15,
    margin: { left: MARGIN_L, right: MARGIN_R },
  };

  // ════════════════════════════════════════════════════════════════════
  //  PAGE 1 — DOCUMENT HEADER WITH LOGO
  // ════════════════════════════════════════════════════════════════════

  let startY = 12;

  // Navy banner
  const bannerH = 22;
  doc.setFillColor(...NAVY);
  doc.rect(0, 0, pageWidth, bannerH, "F");

  // Gold accent line under banner
  doc.setFillColor(...ACCENT_GOLD);
  doc.rect(0, bannerH, pageWidth, 0.8, "F");

  // Logo centered on banner
  if (logoBase64) {
    const logoH = 14;
    const logoW = logoH * 3.3;
    const logoX = (pageWidth - logoW) / 2;
    const logoY = (bannerH - logoH) / 2;
    doc.addImage(logoBase64, "PNG", logoX, logoY, logoW, logoH);
  }

  startY = bannerH + 9;

  // Title block
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(...ACCENT_GOLD);
  doc.text("EDUCAÇÃO", pageWidth / 2, startY, { align: "center" });
  startY += 7;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  doc.setTextColor(...GRAY_900);
  doc.text("RELATÓRIO ESTATÍSTICO INSTITUCIONAL", pageWidth / 2, startY, {
    align: "center",
  });
  startY += 4;

  // Decorative double rule under header
  drawRule(startY, NAVY, 0.8);
  drawRule(startY + 1.2, ACCENT_GOLD, 0.4);
  startY += 6;

  // Meta line
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(...GRAY_600);
  doc.text(
    `Sistema Integrado da Educação — SIED   |   Período: ${periodFrom} a ${periodTo}   |   Emitido em: ${issuedStr}`,
    pageWidth / 2,
    startY,
    { align: "center" }
  );
  startY += 8;

  // ── Filtros aplicados ──────────────────────────────────────────────
  const filterData = [
    ["Período", `${periodFrom} a ${periodTo}`],
    ["Município", filters.municipality || "Todos"],
    ["Equipe", filters.team || "Todos"],
    ["Categoria", filters.entity || "Todas"],
  ];

  autoTable(doc, {
    startY,
    body: filterData,
    theme: "plain",
    margin: { left: MARGIN_L, right: MARGIN_R },
    tableWidth: CONTENT_W,
    styles: {
      fontSize: 9,
      cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 },
      textColor: GRAY_900,
    },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
    },
    alternateRowStyles: { fillColor: GRAY_100 },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 01 — SÍNTESE DOS INDICADORES
  // ════════════════════════════════════════════════════════════════════

  startY = drawSectionHeader("SÍNTESE DOS INDICADORES", startY);

  autoTable(doc, {
    startY,
    head: [["Indicador", "Valor"]],
    body: [
      ["Público alcançado", integer(displaySummary["AUDIENCE - Geral"])],
      ["Público previsto", integer(displaySummary.FUTURE_PUBLIC)],
      ["Palestras realizadas", integer(displaySummary["LECTURES - Geral"])],
      ["Ações de rua", integer(displaySummary["STREET_ACTIONS - Geral"])],
      ["Materiais distribuídos", integer(displaySummary["MATERIAL - Geral"])],
      ["Revistinhas distribuídas", integer(displaySummary["MATERIAL - Soprinho"])],
      ["Solicitações internas", integer(displaySummary.INTERNAL_REQUESTS)],
      ["Solicitações públicas", integer(displaySummary.PUBLIC_REQUESTS)],
    ],
    ...gridTableDefaults,
    columnStyles: {
      1: { halign: "right", cellWidth: 35, fontStyle: "bold" },
    },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 02 — PRODUÇÃO x DEMANDA
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(60, startY);
  startY = drawSectionHeader("PRODUÇÃO x DEMANDA", startY);

  autoTable(doc, {
    startY,
    head: [["Etapa", "Quantidade"]],
    body: [
      ["Solicitações recebidas", integer(demand.total)],
      ["Solicitações aprovadas", integer(demand.approved)],
      ["Ações executadas", integer(demand.executed)],
      ["Aguardando execução", integer(awaitingExecution)],
      ["Canceladas/Recusadas", integer(demand.cancelledOrRefused)],
    ],
    ...gridTableDefaults,
    columnStyles: {
      1: { halign: "right", cellWidth: 35, fontStyle: "bold" },
    },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 03 — EVOLUÇÃO DIÁRIA
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("EVOLUÇÃO DIÁRIA", startY);

  if (dailySeries.length > 0) {
    autoTable(doc, {
      startY,
      head: [["Data", "Ações", "Público"]],
      body: dailySeries.map((row) => [
        row.day,
        integer(row.actions),
        integer(row.audience),
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 28 },
        2: { halign: "right", cellWidth: 28 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhum dado de evolução diária no período.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 04 — AÇÕES DE RUA
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("AÇÕES DE RUA", startY);

  if (categoryData.length > 0) {
    autoTable(doc, {
      startY,
      head: [["Categoria", "Ações", "%"]],
      body: categoryData.map((row) => [
        row.label,
        row.actionsLabel,
        row.percentageLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 22 },
        2: { halign: "right", cellWidth: 20 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhuma ação de rua no período.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 05 — DEMANDAS ADMINISTRATIVAS
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("DEMANDAS ADMINISTRATIVAS", startY);

  if (administrativeDemandRows.length > 0) {
    autoTable(doc, {
      startY,
      head: [["Subtipo", "Ações", "%"]],
      body: administrativeDemandRows.map((row) => [
        row.label,
        row.actionsLabel,
        row.percentageLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 22 },
        2: { halign: "right", cellWidth: 20 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhuma demanda administrativa no período.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 06 — PERFIL DO PÚBLICO E INSTITUCIONAL
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("PERFIL DO PÚBLICO E INSTITUCIONAL", startY);

  // 6a — Perfil Institucional
  if (requesterRows.length > 0) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...NAVY_LIGHT);
    doc.text("Tipo de Solicitante", MARGIN_L + 4, startY);
    startY += 5;

    autoTable(doc, {
      startY,
      head: [["Solicitante", "Ações", "%"]],
      body: requesterRows.map((row) => [
        row.label,
        row.actionsLabel,
        row.percentageLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 22 },
        2: { halign: "right", cellWidth: 20 },
      },
    });
    startY = doc.lastAutoTable.finalY + 8;
  }

  // 6b — Faixa Etária
  if (ageRows.length > 0) {
    startY = ensureSpace(30, startY);

    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...NAVY_LIGHT);
    doc.text("Faixa Etária do Público", MARGIN_L + 4, startY);
    startY += 5;

    autoTable(doc, {
      startY,
      head: [["Faixa", "Ações", "%"]],
      body: ageRows.map((row) => [
        row.label,
        row.actionsLabel,
        row.percentageLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 22 },
        2: { halign: "right", cellWidth: 20 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 07 — DISTRIBUIÇÃO POR DIA E HORÁRIO (HEATMAP)
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(50, startY);
  startY = drawSectionHeader("DISTRIBUIÇÃO POR DIA E HORÁRIO", startY);

  const weekDays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const hourSlots = [
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00",
  ];

  const heatmapBody = weekDays.map((day, dayIndex) => {
    const cells = [day];
    hourSlots.forEach((slot) => {
      const val = heatmapValues.get(`${dayIndex}-${slot}`) || 0;
      cells.push(val > 0 ? String(val) : "");
    });
    return cells;
  });

  autoTable(doc, {
    startY,
    head: [["Dia", ...hourSlots]],
    body: heatmapBody,
    ...gridTableDefaults,
    styles: {
      ...gridTableDefaults.styles,
      fontSize: 7,
      cellPadding: 1.5,
      halign: "center",
    },
    headStyles: {
      ...gridTableDefaults.headStyles,
      fontSize: 6.5,
      cellPadding: 1.5,
    },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 14 },
    },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 08 — INDICADORES GEOGRÁFICOS
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("INDICADORES GEOGRÁFICOS", startY);

  if (municipalities.length > 0) {
    autoTable(doc, {
      startY,
      head: [["Município", "Ações", "Público"]],
      body: municipalities.map((row) => [
        row.agenda__city,
        row.actionsLabel,
        row.audienceLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 25 },
        2: { halign: "right", cellWidth: 25 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhum dado geográfico no período.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 09 — RANKING OPERACIONAL
  // ════════════════════════════════════════════════════════════════════

  startY = ensureSpace(40, startY);
  startY = drawSectionHeader("RANKING OPERACIONAL", startY);

  if (teams.length > 0) {
    autoTable(doc, {
      startY,
      head: [["Equipe", "Ações", "Público"]],
      body: teams.map((row) => [
        row.team,
        row.actionsLabel,
        row.audienceLabel,
      ]),
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 25 },
        2: { halign: "right", cellWidth: 25 },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhum dado de equipes no período.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ── Insights automáticos (before historical, inline) ───────────────
  if (insights.length > 0) {
    startY = ensureSpace(40, startY);

    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...NAVY);
    doc.text("Insights Automáticos", MARGIN_L, startY);
    startY += 5;

    drawRule(startY - 2, NAVY_LIGHT, 0.3);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(...GRAY_900);

    insights.forEach((insight) => {
      startY = ensureSpace(12, startY);
      const lines = doc.splitTextToSize(`• ${insight}`, CONTENT_W - 4);
      doc.text(lines, MARGIN_L + 4, startY);
      startY += lines.length * 4 + 2;
    });
    startY += 4;
  }

  // ════════════════════════════════════════════════════════════════════
  //  SECTION 10 — SÉRIE HISTÓRICA INSTITUCIONAL
  // ════════════════════════════════════════════════════════════════════
  //
  //  Strategy: If annual data has many years, we split into blocks of
  //  MAX_YEARS_PER_BLOCK columns. Each block repeats the "Indicador"
  //  column. If a single block fits, no splitting occurs.
  // ════════════════════════════════════════════════════════════════════

  if (annual.length > 0) {
    startY = ensureSpace(50, startY);
    startY = drawSectionHeader("SÉRIE HISTÓRICA INSTITUCIONAL", startY);

    const MAX_YEARS_PER_BLOCK = 6;
    const yearsList = annual.map((r) => r.year);
    const blockCount = Math.ceil(yearsList.length / MAX_YEARS_PER_BLOCK);

    for (let b = 0; b < blockCount; b++) {
      const blockYears = yearsList.slice(
        b * MAX_YEARS_PER_BLOCK,
        (b + 1) * MAX_YEARS_PER_BLOCK
      );
      const blockAnnual = annual.filter((r) => blockYears.includes(r.year));

      if (b > 0) {
        startY = ensureSpace(40, startY);
        doc.setFont("helvetica", "italic");
        doc.setFontSize(7.5);
        doc.setTextColor(...GRAY_600);
        doc.text(`(continuação — anos ${blockYears[0]} a ${blockYears[blockYears.length - 1]})`, MARGIN_L + 4, startY);
        startY += 5;
      }

      autoTable(doc, {
        startY,
        head: [["Indicador", ...blockYears.map(String)]],
        body: ANNUAL_TABLE_GROUPS.flatMap((group) => [
          [{ content: group.title, colSpan: blockYears.length + 1, styles: { fontStyle: "bold", fillColor: [229, 231, 235] } }],
          ...group.rows.map(([key, label]) => [label, ...blockAnnual.map((row) => integer(row[key]))]),
        ]),
        ...gridTableDefaults,
        styles: {
          ...gridTableDefaults.styles,
          fontSize: 7.5,
          cellPadding: 2,
        },
        headStyles: {
          ...gridTableDefaults.headStyles,
          fontSize: 7.5,
          cellPadding: 2,
        },
        columnStyles: {
          0: { fontStyle: "bold", cellWidth: 52 },
          ...Object.fromEntries(
            blockYears.map((_, i) => [i + 1, { halign: "right" }])
          ),
        },
      });
      startY = doc.lastAutoTable.finalY + 8;
    }
  }

  // ── Final accent bar ───────────────────────────────────────────────
  startY = ensureSpace(20, startY);
  drawRule(startY, NAVY, 0.6);
  drawRule(startY + 1, ACCENT_GOLD, 0.3);

  // ════════════════════════════════════════════════════════════════════
  //  FOOTER — Applied to all pages (after content is complete)
  // ════════════════════════════════════════════════════════════════════

  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);

    // Top rule on subsequent pages
    if (i > 1) {
      drawRule(10, NAVY, 0.6);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(7);
      doc.setTextColor(...GRAY_600);
      doc.text(
        "SIED — RELATÓRIO ESTATÍSTICO INSTITUCIONAL",
        MARGIN_L,
        8
      );
      doc.text(`Pág. ${i}/${pageCount}`, pageWidth - MARGIN_R, 8, {
        align: "right",
      });
    }

    // Bottom border
    drawRule(pageHeight - 16, GRAY_300, 0.3);

    // Footer left
    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.5);
    doc.setTextColor(...GRAY_600);
    doc.text(
      `SIED — Relatório Estatístico Institucional  |  Emitido em: ${issuedStr}`,
      MARGIN_L,
      pageHeight - 12
    );

    // Footer right — page number
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7);
    doc.text(`${i} / ${pageCount}`, pageWidth - MARGIN_R, pageHeight - 12, {
      align: "right",
    });

    // Confidentiality line
    doc.setFont("helvetica", "italic");
    doc.setFontSize(5.5);
    doc.setTextColor(...GRAY_300);
    doc.text(
      "Uso institucional — Lei Seca Educação / Governo do Estado do Rio de Janeiro",
      pageWidth / 2,
      pageHeight - 8,
      { align: "center" }
    );
  }

  // ════════════════════════════════════════════════════════════════════
  //  OUTPUT — Real PDF blob
  // ════════════════════════════════════════════════════════════════════

  const filename = `relatorio_estatistico_sied_${periodFrom}_a_${periodTo}.pdf`;

  if (openInNewTab) {
    const blobUrl = doc.output("bloburl");
    window.open(blobUrl, "_blank");
    return;
  }

  doc.save(filename);
}

import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

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

// ── Design Tokens (shared with reportPdfGenerator / statisticsPdfGenerator) ──
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

// ── Format helpers ───────────────────────────────────────────────────────
const fmtDecimal = (value) => {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const fmtInt = (value) => {
  if (value === null || value === undefined) return "—";
  return Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
};

const fmtPercent = (value) => {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
};

const fmtDateBR = (isoStr) => {
  if (!isoStr) return "—";
  const parts = String(isoStr).split("-");
  if (parts.length !== 3) return isoStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
};

/**
 * Generates a professional PDF report for the Avaliações (Evaluations) module.
 *
 * This function receives the pre-loaded page state (data + filters) and renders
 * it into a jsPDF document. It performs NO API calls — all data comes from the
 * React state that is already displayed on screen.
 *
 * @param {Object} params
 * @param {Object} params.data - The analytics data from /surveys/analytics/
 * @param {Object} params.filters - The currently applied filter values.
 * @param {Date}   [params.issuedAt] - The date/time of emission.
 * @param {string} params.logoUrl - The URL to the institutional logo.
 * @param {string} [params.userName] - Name of the authenticated user (optional).
 */
export async function generateEvaluationsPdf({
  data,
  filters,
  issuedAt,
  logoUrl,
  userName,
}) {
  // ── Contract barrier ─────────────────────────────────────────────────
  if (!data) {
    throw new Error(
      "Dados de avaliações indisponíveis para gerar o PDF. Aguarde o carregamento completo."
    );
  }

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
  const periodFrom = filters.date_from ? fmtDateBR(filters.date_from) : "Todos";
  const periodTo = filters.date_to ? fmtDateBR(filters.date_to) : "Todos";
  const periodLabel =
    filters.date_from || filters.date_to
      ? `${periodFrom} a ${periodTo}`
      : "Todo o período";

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

  // ── Check for empty data ───────────────────────────────────────────
  const isEmpty = !data.cards || data.cards.total_surveys === 0;

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
  doc.text("AVALIAÇÕES", pageWidth / 2, startY, { align: "center" });
  startY += 7;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  doc.setTextColor(...GRAY_900);
  doc.text("RELATÓRIO DE AVALIAÇÕES", pageWidth / 2, startY, {
    align: "center",
  });
  startY += 4;

  // Decorative double rule under header
  drawRule(startY, NAVY, 0.8);
  drawRule(startY + 1.2, ACCENT_GOLD, 0.4);
  startY += 6;

  // Meta line
  const metaParts = [
    "Operação Lei Seca — SIED",
    `Período: ${periodLabel}`,
    `Emitido em: ${issuedStr}`,
  ];
  if (userName) metaParts.push(`Usuário: ${userName}`);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(...GRAY_600);
  doc.text(metaParts.join("   |   "), pageWidth / 2, startY, {
    align: "center",
  });
  startY += 8;

  // ── Filtros aplicados ──────────────────────────────────────────────
  const filterLabel = (value, fallback = "Todos") => value || fallback;

  const regionName = filters.region
    ? (data.regions || []).find((r) => String(r.id) === String(filters.region))?.name || filters.region
    : "";
  const municipalityName = filters.municipality
    ? (data.municipalities || []).find((m) => String(m.id) === String(filters.municipality))?.name || filters.municipality
    : "";

  const filterData = [
    ["Período", periodLabel],
    ["Estado", filterLabel(filters.state)],
    ["Região", filterLabel(regionName, "Todas")],
    ["Município", filterLabel(municipalityName)],
    ["Equipe", filterLabel(filters.team, "Todas")],
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

  // ── Empty state ────────────────────────────────────────────────────
  if (isEmpty) {
    startY = ensureSpace(40, startY);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.setTextColor(...GRAY_600);
    doc.text(
      "Nenhuma avaliação encontrada para os filtros selecionados.",
      pageWidth / 2,
      startY + 20,
      { align: "center" }
    );

    // Skip to footer
  } else {
    // ════════════════════════════════════════════════════════════════════
    //  SECTION 01 — RESUMO EXECUTIVO
    // ════════════════════════════════════════════════════════════════════

    startY = drawSectionHeader("RESUMO EXECUTIVO", startY);

    if (data.executive_summary) {
      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      doc.setTextColor(...GRAY_900);
      const summaryLines = doc.splitTextToSize(data.executive_summary, CONTENT_W - 8);
      doc.text(summaryLines, MARGIN_L + 4, startY);
      startY += summaryLines.length * 4.5 + 8;
    } else {
      startY += 4;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 02 — INDICADORES DE SATISFAÇÃO
    // ════════════════════════════════════════════════════════════════════

    startY = ensureSpace(60, startY);
    startY = drawSectionHeader("INDICADORES DE SATISFAÇÃO", startY);

    const cards = data.cards || {};
    const indicatorsBody = [
      ["Avaliações Recebidas", fmtInt(cards.total_surveys)],
      ["Índice de Satisfação", fmtPercent(cards.satisfaction_index)],
      ["Nota Palestrante", fmtDecimal(cards.speaker_avg)],
      ["Recursos Audiovisuais", fmtDecimal(cards.resources_avg)],
      ["Pontualidade", fmtDecimal(cards.punctuality_avg)],
      ["Entusiasmo da Equipe", fmtDecimal(cards.enthusiasm_avg)],
      ["Dinâmicas", fmtDecimal(cards.workshops_avg)],
      ["Material Distribuído", fmtDecimal(cards.support_material_avg)],
      ["Depoimento Cadeirantes", fmtDecimal(cards.wheelchair_avg)],
      ["Melhor Critério", cards.best_criteria || "—"],
      ["Menor Avaliação", cards.worst_criteria || "—"],
      ["Maior Aumento", cards.most_improved || "—"],
    ];

    autoTable(doc, {
      startY,
      head: [["Indicador", "Valor"]],
      body: indicatorsBody,
      ...gridTableDefaults,
      columnStyles: {
        1: { halign: "right", cellWidth: 45, fontStyle: "bold" },
      },
    });
    startY = doc.lastAutoTable.finalY + 10;

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 03 — RADAR DE CRITÉRIOS
    // ════════════════════════════════════════════════════════════════════

    if (data.radar && data.radar.length > 0) {
      startY = ensureSpace(40, startY);
      startY = drawSectionHeader("MÉDIAS POR CRITÉRIO", startY);

      autoTable(doc, {
        startY,
        head: [["Critério", "Nota Média"]],
        body: data.radar.map((item) => [
          item.criteria,
          fmtDecimal(item.value),
        ]),
        ...gridTableDefaults,
        columnStyles: {
          1: { halign: "right", cellWidth: 35, fontStyle: "bold" },
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 04 — EVOLUÇÃO MENSAL
    // ════════════════════════════════════════════════════════════════════

    if (data.monthly_evolution && data.monthly_evolution.length > 0) {
      startY = ensureSpace(40, startY);
      startY = drawSectionHeader("EVOLUÇÃO MENSAL DA NOTA GERAL", startY);

      autoTable(doc, {
        startY,
        head: [["Mês", "Nota Média"]],
        body: data.monthly_evolution.map((item) => [
          item.label,
          fmtDecimal(item.value),
        ]),
        ...gridTableDefaults,
        columnStyles: {
          1: { halign: "right", cellWidth: 35, fontStyle: "bold" },
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 05 — DISTRIBUIÇÃO DAS NOTAS POR CRITÉRIO
    // ════════════════════════════════════════════════════════════════════

    if (data.distribution && Object.keys(data.distribution).length > 0) {
      startY = ensureSpace(50, startY);
      startY = drawSectionHeader("DISTRIBUIÇÃO DAS NOTAS POR CRITÉRIO", startY);

      const distKeys = Object.keys(data.distribution);
      const distHead = [["Critério", ...Array.from({ length: 10 }, (_, i) => String(i + 1)), "Total"]];

      const distBody = distKeys.map((crit) => {
        const counts = data.distribution[crit];
        const row = [crit];
        let total = 0;
        for (let score = 1; score <= 10; score++) {
          const count = Number(counts[String(score)] || 0);
          total += count;
          row.push(String(count));
        }
        row.push(String(total));
        return row;
      });

      autoTable(doc, {
        startY,
        head: distHead,
        body: distBody,
        ...gridTableDefaults,
        styles: {
          ...gridTableDefaults.styles,
          fontSize: 7,
          cellPadding: 1.8,
        },
        headStyles: {
          ...gridTableDefaults.headStyles,
          fontSize: 7,
          cellPadding: 2,
        },
        columnStyles: {
          0: { fontStyle: "bold", cellWidth: 38 },
          ...Object.fromEntries(
            Array.from({ length: 11 }, (_, i) => [i + 1, { halign: "center" }])
          ),
          11: { halign: "center", fontStyle: "bold" },
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 06 — MAPA DE CALOR — CRITÉRIOS POR MÊS
    // ════════════════════════════════════════════════════════════════════

    if (data.heatmap && data.heatmap.length > 0) {
      startY = ensureSpace(50, startY);
      startY = drawSectionHeader("MAPA DE CALOR — CRITÉRIOS POR MÊS", startY);

      // Build unique criteria and months
      const criteriaSet = new Set();
      const monthsSet = new Set();
      data.heatmap.forEach((h) => {
        criteriaSet.add(h.criteria);
        monthsSet.add(h.month);
      });
      const criteriaList = Array.from(criteriaSet);
      const monthsList = Array.from(monthsSet).sort();

      // Format month labels: "mm/yy"
      const monthLabels = monthsList.map((m) => {
        const [yy, mm] = m.split("-");
        return `${mm}/${yy.slice(2)}`;
      });

      const getValue = (crit, m) => {
        const item = data.heatmap.find((h) => h.criteria === crit && h.month === m);
        return item ? item.value : null;
      };

      const heatHead = [["Critério", ...monthLabels]];
      const heatBody = criteriaList.map((crit) => [
        crit,
        ...monthsList.map((m) => {
          const val = getValue(crit, m);
          return val !== null ? fmtDecimal(val) : "—";
        }),
      ]);

      autoTable(doc, {
        startY,
        head: heatHead,
        body: heatBody,
        ...gridTableDefaults,
        styles: {
          ...gridTableDefaults.styles,
          fontSize: 7,
          cellPadding: 1.8,
        },
        headStyles: {
          ...gridTableDefaults.headStyles,
          fontSize: 7,
          cellPadding: 2,
        },
        columnStyles: {
          0: { fontStyle: "bold", cellWidth: 38 },
          ...Object.fromEntries(
            monthLabels.map((_, i) => [i + 1, { halign: "center" }])
          ),
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 07 — INTELIGÊNCIA
    // ════════════════════════════════════════════════════════════════════

    if (data.intelligence) {
      startY = ensureSpace(40, startY);
      startY = drawSectionHeader("INTELIGÊNCIA E TENDÊNCIAS", startY);

      const intel = data.intelligence;
      const trendLabel =
        intel.trend === "up"
          ? `Subindo (+${intel.trend_delta})`
          : intel.trend === "down"
            ? `Caindo (${intel.trend_delta > 0 ? "-" : ""}${intel.trend_delta})`
            : "—";

      const intelBody = [
        ["Índice de Excelência", fmtPercent(intel.excellence_index)],
        ["Maior Destaque", intel.best_criteria || "—"],
        ["Maior Crescimento", intel.most_improved || "—"],
        ["Maior Queda", intel.most_declined || "—"],
        ["Tendência (Período)", trendLabel],
      ];

      autoTable(doc, {
        startY,
        head: [["Indicador", "Valor"]],
        body: intelBody,
        ...gridTableDefaults,
        columnStyles: {
          1: { halign: "right", cellWidth: 55, fontStyle: "bold" },
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 08 — FEEDBACK DOS RESPONDENTES
    // ════════════════════════════════════════════════════════════════════

    const messages = data.satisfaction_panel?.messages || [];
    if (messages.length > 0) {
      startY = ensureSpace(40, startY);
      startY = drawSectionHeader("FEEDBACK DOS RESPONDENTES", startY);

      autoTable(doc, {
        startY,
        head: [["Data", "Equipe", "Nota", "Comentário"]],
        body: messages.map((msg) => [
          msg.answered_at
            ? new Date(msg.answered_at).toLocaleDateString("pt-BR")
            : "—",
          msg.team || "—",
          msg.overall_rating != null
            ? Number(msg.overall_rating).toFixed(1)
            : "—",
          msg.moderated_comment || msg.suggestion || "—",
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
        },
        columnStyles: {
          0: { cellWidth: 22 },
          1: { cellWidth: 28 },
          2: { halign: "center", cellWidth: 15 },
          3: { cellWidth: 0 }, // auto-fill remaining
        },
      });
      startY = doc.lastAutoTable.finalY + 10;
    }

    // ════════════════════════════════════════════════════════════════════
    //  SECTION 10 — NOTA METODOLÓGICA
    // ════════════════════════════════════════════════════════════════════

    startY = ensureSpace(30, startY);
    startY = drawSectionHeader("NOTA METODOLÓGICA", startY);

    const methodNotes = [
      "As avaliações são obtidas por meio de pesquisas de satisfação aplicadas aos participantes das ações educativas da Operação Lei Seca.",
      "As médias são calculadas com base nas notas atribuídas na escala de 1 a 10 para cada critério avaliado.",
      `O índice de satisfação representa o percentual de avaliações com nota geral igual ou superior a 4 (escala de 1 a 5 normalizada).`,
      "Os dados apresentados refletem o estado do sistema no momento da emissão do relatório e respeitam os filtros aplicados.",
    ];

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...GRAY_600);

    methodNotes.forEach((note) => {
      startY = ensureSpace(12, startY);
      const lines = doc.splitTextToSize(`• ${note}`, CONTENT_W - 8);
      doc.text(lines, MARGIN_L + 4, startY);
      startY += lines.length * 3.8 + 2;
    });
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
        "SIED — RELATÓRIO DE AVALIAÇÕES",
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
      `SIED — Relatório de Avaliações  |  Operação Lei Seca  |  Emitido em: ${issuedStr}`,
      MARGIN_L,
      pageHeight - 12
    );

    // Footer right — page number
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7);
    doc.text(`Página ${i} de ${pageCount}`, pageWidth - MARGIN_R, pageHeight - 12, {
      align: "right",
    });

    // Confidentiality line
    doc.setFont("helvetica", "italic");
    doc.setFontSize(5.5);
    doc.setTextColor(...GRAY_300);
    doc.text(
      "Documento gerado automaticamente pelo SIED — Uso institucional — Operação Lei Seca / Governo do Estado do Rio de Janeiro",
      pageWidth / 2,
      pageHeight - 8,
      { align: "center" }
    );
  }

  // ════════════════════════════════════════════════════════════════════
  //  OUTPUT — Save PDF with descriptive filename
  // ════════════════════════════════════════════════════════════════════

  const fileFrom = filters.date_from || "inicio";
  const fileTo = filters.date_to || issuedDate.toISOString().slice(0, 10);
  const filename = `relatorio_avaliacoes_${fileFrom.replace(/-/g, "-")}_a_${fileTo.replace(/-/g, "-")}.pdf`;

  doc.save(filename);

  return { filename, pageCount };
}

import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { formatDateBR } from "./date.js";

export async function generateTechnicalReportPdf(form, selectedAgenda, attendanceForm) {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.width;
  const pageHeight = doc.internal.pageSize.height;

  // ── Design Tokens ──────────────────────────────────────────────────────
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
  const CONTENT_W   = pageWidth - MARGIN_L - MARGIN_R;

  let sectionCounter = 0;

  // ── Utility: Draw a thin horizontal rule ───────────────────────────────
  const drawRule = (y, color = GRAY_300, thickness = 0.3) => {
    doc.setDrawColor(...color);
    doc.setLineWidth(thickness);
    doc.line(MARGIN_L, y, pageWidth - MARGIN_R, y);
  };

  // ── Utility: Section Header ────────────────────────────────────────────
  const drawSectionHeader = (title, y) => {
    sectionCounter++;
    const num = String(sectionCounter).padStart(2, "0");

    // Section number badge
    doc.setFillColor(...NAVY);
    doc.roundedRect(MARGIN_L, y - 4.5, 9, 6, 1, 1, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(...WHITE);
    doc.text(num, MARGIN_L + 4.5, y, { align: "center" });

    // Section title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.setTextColor(...NAVY);
    doc.text(title, MARGIN_L + 12, y);

    // Thin accent line beneath
    drawRule(y + 2, NAVY_LIGHT, 0.5);

    return y + 7;
  };

  // ── Utility: Safe page-break check ─────────────────────────────────────
  const ensureSpace = (needed) => {
    const currentY = doc._currentY || 0;
    if (currentY > pageHeight - needed - 20) {
      doc.addPage();
      return 20;
    }
    return currentY;
  };

  // ── Footer (applied to all pages at end) ───────────────────────────────
  const addFooter = () => {
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);

      // Top rule on every page except page 1 (page 1 has its own header)
      if (i > 1) {
        drawRule(10, NAVY, 0.6);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(7);
        doc.setTextColor(...GRAY_600);
        doc.text("LEI SECA EDUCAÇÃO — RELATÓRIO TÉCNICO DE ATIVIDADE", MARGIN_L, 8);
        doc.text(`Pág. ${i}/${pageCount}`, pageWidth - MARGIN_R, 8, { align: "right" });
      }

      // Bottom border
      drawRule(pageHeight - 16, GRAY_300, 0.3);

      // Footer left — institutional
      doc.setFont("helvetica", "normal");
      doc.setFontSize(6.5);
      doc.setTextColor(...GRAY_600);
      const now = new Date();
      const dateStr = now.toLocaleDateString("pt-BR");
      const timeStr = now.toLocaleTimeString("pt-BR");
      doc.text(
        `SIED — Sistema Integrado da Educação  |  Documento gerado automaticamente em ${dateStr} às ${timeStr}`,
        MARGIN_L,
        pageHeight - 12
      );

      // Footer right — page number
      doc.setFont("helvetica", "bold");
      doc.setFontSize(7);
      doc.text(`${i} / ${pageCount}`, pageWidth - MARGIN_R, pageHeight - 12, { align: "right" });

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
  };

  // ════════════════════════════════════════════════════════════════════════
  //  PAGE 1 — DOCUMENT HEADER
  // ════════════════════════════════════════════════════════════════════════

  let startY = 12;

  // Top accent line
  doc.setFillColor(...NAVY);
  doc.rect(0, 0, pageWidth, 2, "F");

  // Gold thin line accent
  doc.setFillColor(...ACCENT_GOLD);
  doc.rect(0, 2, pageWidth, 0.6, "F");

  startY = 18;

  // Main title block
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(...GRAY_600);
  doc.text("GOVERNO DO ESTADO DO RIO DE JANEIRO", pageWidth / 2, startY, { align: "center" });
  startY += 5;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(...NAVY);
  doc.text("LEI SECA EDUCAÇÃO", pageWidth / 2, startY, { align: "center" });
  startY += 7;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  doc.setTextColor(...GRAY_900);
  doc.text("RELATÓRIO TÉCNICO DE ATIVIDADE", pageWidth / 2, startY, { align: "center" });
  startY += 4;

  // Decorative double rule under header
  drawRule(startY, NAVY, 0.8);
  drawRule(startY + 1.2, ACCENT_GOLD, 0.4);
  startY += 6;

  // Document meta line (protocol & OS inline)
  const osNum = selectedAgenda?.service_order_number;
  const proto = form.agenda;
  const docDate = form.operation_date ? formatDateBR(form.operation_date) : "--";

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(...GRAY_600);

  const metaParts = [];
  if (proto) metaParts.push(`Protocolo #${proto}`);
  if (osNum) metaParts.push(`OS ${osNum}`);
  metaParts.push(`Data: ${docDate}`);
  doc.text(metaParts.join("   |   "), pageWidth / 2, startY, { align: "center" });
  startY += 8;

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 1 — IDENTIFICAÇÃO DA ATIVIDADE
  // ════════════════════════════════════════════════════════════════════════

  startY = drawSectionHeader("IDENTIFICAÇÃO DA ATIVIDADE", startY);

  const identData = [
    ["Protocolo", form.agenda ? `#${form.agenda}` : "—"],
    ["Ordem de Serviço", selectedAgenda?.service_order_number || "—"],
    ["Data da Operação", form.operation_date ? formatDateBR(form.operation_date) : "—"],
    ["Horário Programado", selectedAgenda ? `${selectedAgenda.start_time?.slice(0,5) || "--"} às ${selectedAgenda.end_time?.slice(0,5) || "--"}` : "—"],
    ["Natureza da Atividade", form.agenda_title || "—"],
    ["Instituição / Local", form.agenda_location || "—"],
    ["Endereço", selectedAgenda?.address || "—"],
    ["Município", selectedAgenda?.city || selectedAgenda?.municipality_ref_name || "—"],
  ].filter(row => row[1] && row[1] !== "—" && row[1] !== "-" && row[1] !== "null" && row[1] !== "undefined");

  autoTable(doc, {
    startY,
    body: identData,
    theme: "plain",
    styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900 },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
      1: { cellWidth: CONTENT_W - 48 },
    },
    alternateRowStyles: { fillColor: GRAY_100 },
    didDrawPage: () => {},
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 2 — RESPONSABILIDADE OPERACIONAL
  // ════════════════════════════════════════════════════════════════════════

  const chief = form.education_agents ? form.education_agents.match(/Chefe(?: respons[áa]vel)?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  const agents = form.education_agents ? form.education_agents.match(/Agentes?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  const supports = form.education_agents ? form.education_agents.match(/Apoio?:\s*([^\n]+)/i)?.[1]?.trim() : "";

  const respData = [];
  if (form.team) respData.push(["Equipe Designada", form.team]);
  if (chief) respData.push(["Chefe Responsável", chief]);
  if (agents) respData.push(["Agentes de Educação", agents]);
  if (supports) respData.push(["Apoio Operacional", supports]);

  if (respData.length) {
    startY = drawSectionHeader("RESPONSABILIDADE OPERACIONAL", startY);

    autoTable(doc, {
      startY,
      body: respData,
      theme: "plain",
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
        1: { cellWidth: CONTENT_W - 48 },
      },
      alternateRowStyles: { fillColor: GRAY_100 },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 3 — FREQUÊNCIA DOS PARTICIPANTES
  // ════════════════════════════════════════════════════════════════════════

  const absences = Object.values(attendanceForm || {}).filter(d => d.is_absent === true);

  startY = drawSectionHeader("FREQUÊNCIA DOS PARTICIPANTES", startY);

  if (absences.length === 0) {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhuma ausência registrada.", MARGIN_L + 4, startY);
    startY += 8;
  } else {
    const absData = absences.map(a => [
      a.member?.name || "Desconhecido",
      a.member?.typeLabel || "N/I",
      (a.reason || "").trim() || "Justificativa não informada",
    ]);
    autoTable(doc, {
      startY,
      head: [["Participante Ausente", "Função", "Justificativa"]],
      body: absData,
      theme: "grid",
      headStyles: { fillColor: NAVY, textColor: WHITE, fontStyle: "bold", fontSize: 8.5, cellPadding: 3 },
      styles: { fontSize: 8.5, cellPadding: 2.5, textColor: GRAY_900 },
      alternateRowStyles: { fillColor: GRAY_100 },
      tableLineColor: GRAY_300,
      tableLineWidth: 0.15,
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 4 — AÇÕES EXECUTADAS
  // ════════════════════════════════════════════════════════════════════════

  const actions = form.actions || [];
  let totalsEstimado = 0;
  let totalsAlcancado = 0;

  if (actions.length > 0) {
    startY = drawSectionHeader("AÇÕES EXECUTADAS", startY);
  }

  actions.forEach((action, index) => {
    totalsEstimado += Number(action.approach || 0);
    totalsAlcancado += Number(action.approached_actions || 0);

    // Sub-header for each action
    if (startY > pageHeight - 50) {
      doc.addPage();
      startY = 20;
    }

    const actionNum = String(index + 1).padStart(2, "0");
    const actionLabel = (action.type_action || "NÃO ESPECIFICADA").toUpperCase();

    // Action badge
    doc.setFillColor(...NAVY_LIGHT);
    doc.roundedRect(MARGIN_L, startY - 3.5, CONTENT_W, 6.5, 1.2, 1.2, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...WHITE);
    doc.text(`AÇÃO ${actionNum} — ${actionLabel}`, MARGIN_L + 4, startY + 0.5);
    startY += 8;

    const actionData = [
      ["Tipo da Ação", action.type_action || "—"],
      ["Instituição / Local", action.institution_name || "—"],
      ["Endereço", action.place_action || "—"],
      ["Horário", `${action.start_time || "--"} às ${action.final_hour || "--"}`],
      ["Público Estimado", action.approach || "0"],
      ["Público Alcançado", action.approached_actions || "0"],
    ].filter(r => r[1] && r[1] !== "—" && r[1] !== "-- às --" && r[1] !== "0" && r[1] !== "-");

    autoTable(doc, {
      startY,
      body: actionData,
      theme: "plain",
      styles: { fontSize: 8.5, cellPadding: { top: 2, bottom: 2, left: 4, right: 4 }, textColor: GRAY_900 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 45, textColor: NAVY_LIGHT },
        1: { cellWidth: CONTENT_W - 45 },
      },
      alternateRowStyles: { fillColor: GRAY_100 },
    });
    startY = doc.lastAutoTable.finalY + 4;

    // Materiais Distribuídos
    if (action.distribution_materials_distributed) {
      const lines = action.distribution_materials_distributed.split("\n");
      const materials = [];
      lines.forEach(line => {
        const parts = line.split("|");
        if (parts.length >= 2) {
          const name = parts[0].trim();
          const rawQ = parts[1].replace(/\D/g, "");
          const qty = parseInt(rawQ, 10);
          if (name && !isNaN(qty) && qty > 0) {
            materials.push([name, qty.toLocaleString("pt-BR")]);
          }
        }
      });
      if (materials.length > 0) {
        autoTable(doc, {
          startY,
          head: [["Material Distribuído", "Qtd."]],
          body: materials,
          theme: "grid",
          headStyles: { fillColor: GRAY_100, textColor: NAVY, fontStyle: "bold", fontSize: 8 },
          styles: { fontSize: 8, cellPadding: 2, textColor: GRAY_900 },
          columnStyles: { 1: { halign: "center", cellWidth: 20 } },
          alternateRowStyles: { fillColor: [250, 250, 252] },
          tableLineColor: GRAY_300,
          tableLineWidth: 0.1,
        });
        startY = doc.lastAutoTable.finalY + 8;
      } else {
        startY += 4;
      }
    } else {
      startY += 4;
    }
  });

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 5 — PÚBLICO E RESULTADOS (CONSOLIDADO)
  // ════════════════════════════════════════════════════════════════════════

  if (startY > pageHeight - 50) {
    doc.addPage();
    startY = 20;
  }

  startY = drawSectionHeader("PÚBLICO E RESULTADOS CONSOLIDADOS", startY);

  autoTable(doc, {
    startY,
    head: [["Indicador", "Valor"]],
    body: [
      ["Público Estimado (total)", totalsEstimado.toLocaleString("pt-BR")],
      ["Público Alcançado (total)", totalsAlcancado.toLocaleString("pt-BR")],
      ["Ações Realizadas", actions.length.toString()],
      ["Taxa de Alcance", totalsEstimado > 0 ? `${((totalsAlcancado / totalsEstimado) * 100).toFixed(1)}%` : "N/A"],
    ],
    theme: "grid",
    headStyles: { fillColor: NAVY, textColor: WHITE, fontStyle: "bold", fontSize: 8.5, cellPadding: 3 },
    styles: { fontSize: 9, cellPadding: 3, textColor: GRAY_900 },
    columnStyles: { 1: { halign: "center", cellWidth: 35, fontStyle: "bold" } },
    alternateRowStyles: { fillColor: GRAY_100 },
    tableLineColor: GRAY_300,
    tableLineWidth: 0.15,
  });
  startY = doc.lastAutoTable.finalY + 10;

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 6 — RECURSOS OPERACIONAIS
  // ════════════════════════════════════════════════════════════════════════

  const recursos = [];
  if (form.cars) recursos.push(["Viaturas", form.cars.split(",").map(c => c.trim()).filter((v,i,a) => a.indexOf(v)===i).join(", ")]);
  if (form.breathalyzers) recursos.push(["Etilômetros", form.breathalyzers]);

  if (recursos.length > 0) {
    if (startY > pageHeight - 40) {
      doc.addPage();
      startY = 20;
    }

    startY = drawSectionHeader("RECURSOS OPERACIONAIS", startY);

    autoTable(doc, {
      startY,
      body: recursos,
      theme: "plain",
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
        1: { cellWidth: CONTENT_W - 48 },
      },
      alternateRowStyles: { fillColor: GRAY_100 },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 7 — OCORRÊNCIAS
  // ════════════════════════════════════════════════════════════════════════

  if (startY > pageHeight - 40) {
    doc.addPage();
    startY = 20;
  }

  startY = drawSectionHeader("REGISTRO DE OCORRÊNCIAS", startY);

  if (form.has_exceptional_occurrence) {
    const ocType = form.exceptional_occurrence_type === "VEHICLE_BREAKDOWN" ? "Viatura"
                 : form.exceptional_occurrence_type === "WORK_ACCIDENT" ? "Efetivo"
                 : form.exceptional_occurrence_type;
    autoTable(doc, {
      startY,
      body: [
        ["Tipo da Ocorrência", ocType || "—"],
        ["Descrição", form.exceptional_occurrence_description || "—"],
        ["Providências Adotadas", form.exceptional_occurrence_actions_taken || "—"],
        ["Impacto na Atividade", form.exceptional_occurrence_impact || "—"],
      ],
      theme: "plain",
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
        1: { cellWidth: CONTENT_W - 48 },
      },
      alternateRowStyles: { fillColor: GRAY_100 },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_600);
    doc.text("Nenhuma ocorrência envolvendo viatura ou efetivo registrada.", MARGIN_L + 4, startY);
    startY += 10;
  }

  // ════════════════════════════════════════════════════════════════════════
  //  SECTION 8 — CONCLUSÃO INSTITUCIONAL
  // ════════════════════════════════════════════════════════════════════════

  if (startY > pageHeight - 50) {
    doc.addPage();
    startY = 20;
  }

  startY = drawSectionHeader("CONCLUSÃO INSTITUCIONAL", startY);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(...GRAY_900);
  const concText =
    "O presente documento consolida as informações registradas no Sistema Integrado da Educação – SIED " +
    "referentes à atividade identificada, incluindo execução operacional, frequência dos participantes, " +
    "ações realizadas, público estimado, público alcançado, materiais distribuídos e eventuais ocorrências. " +
    "Este relatório possui caráter técnico-institucional e integra o acervo documental do programa Lei Seca Educação.";
  const splitConc = doc.splitTextToSize(concText, CONTENT_W);
  doc.text(splitConc, MARGIN_L + 4, startY);
  startY += splitConc.length * 4 + 8;

  // Final accent bar
  drawRule(startY, NAVY, 0.6);
  drawRule(startY + 1, ACCENT_GOLD, 0.3);

  // ── Apply footers ──────────────────────────────────────────────────────
  addFooter();

  // ── Generate & Download ────────────────────────────────────────────────
  const blob = doc.output("blob");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;

  let filename = "relatorio-tecnico.pdf";
  if (osNum) {
    filename = `relatorio-tecnico-os-${osNum}.pdf`;
  } else if (proto) {
    filename = `relatorio-tecnico-protocolo-${proto}.pdf`;
  }

  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

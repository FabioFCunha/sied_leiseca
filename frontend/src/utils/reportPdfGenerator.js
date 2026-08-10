import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { formatDateBR } from "./date.js";
import logoUrl from "../assets/operacao-lei-seca-logo.png";
import { getSupports, getReachedAudienceForAction } from "./reportPreview.js";

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

export async function generateTechnicalReportPdf(form, selectedAgenda, attendanceForm, openInNewTab = false, showEstimatedPublic = true) {
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
  //  PAGE 1 — DOCUMENT HEADER WITH LOGO
  // ════════════════════════════════════════════════════════════════════════

  // Load logo
  let logoBase64;
  try {
    logoBase64 = await loadImageAsBase64(logoUrl);
  } catch (_) {
    logoBase64 = null;
  }

  let startY = 12;

  // Navy banner background for logo
  const bannerH = 22;
  doc.setFillColor(...NAVY);
  doc.rect(0, 0, pageWidth, bannerH, "F");

  // Gold accent line under banner
  doc.setFillColor(...ACCENT_GOLD);
  doc.rect(0, bannerH, pageWidth, 0.8, "F");

  // Logo centered on banner
  if (logoBase64) {
    const logoH = 14;
    const logoW = logoH * 3.3; // approximate aspect ratio of the logo
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
    margin: { left: MARGIN_L, right: MARGIN_R },
    tableWidth: CONTENT_W,
    styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900, overflow: "linebreak" },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
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
  const supportsList = getSupports(form, selectedAgenda);
  const supports = supportsList.join(" - ");

  const respData = [];
  if (form.team) respData.push(["Equipe Designada", form.team]);
  if (chief) respData.push(["Chefe Responsável", chief]);
  if (agents) respData.push(["Agentes de Educação", agents]);
  if (supports) respData.push(["Apoios", supports]);

  if (respData.length) {
    startY = drawSectionHeader("RESPONSABILIDADE OPERACIONAL", startY);

    autoTable(doc, {
      startY,
      body: respData,
      theme: "plain",
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: CONTENT_W,
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900, overflow: "linebreak" },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
      },
      alternateRowStyles: { fillColor: GRAY_100 },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // ════════════════════════════════════════════════════════════════════════
  //  ALTERAÇÕES DE EFETIVO
  // ════════════════════════════════════════════════════════════════════════
  if (form.changes_staff && form.changes_staff.trim()) {
    if (startY > pageHeight - 35) {
      doc.addPage();
      startY = 20;
    }

    startY = drawSectionHeader("ALTERAÇÕES DE EFETIVO", startY);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_900);

    const staffText = form.changes_staff;
    const splitStaff = doc.splitTextToSize(staffText, CONTENT_W - 8);
    const lineHeight = 4.5;

    for (let i = 0; i < splitStaff.length; i++) {
      if (startY > pageHeight - 22) {
        doc.addPage();
        startY = 20;
      }
      doc.text(splitStaff[i], MARGIN_L + 4, startY);
      startY += lineHeight;
    }
    startY += 10;
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
    const isFirstAction = index === 0;

    // Público Estimado: apenas Ação 1
    if (isFirstAction) {
      totalsEstimado += Number(action.approach ?? 0);
    }
    // Público Alcançado: approached_lectures na Ação 1, approached_actions nas extras
    const alcVal = getReachedAudienceForAction(action, index);
    const alcNum = Number(alcVal);
    totalsAlcancado += (alcVal !== "" && alcVal !== null && alcVal !== undefined && Number.isFinite(alcNum)) ? alcNum : 0;

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

    const alcDisplay = (alcVal !== "" && alcVal !== null && alcVal !== undefined) ? String(alcVal) : "Não informado";

    const actionData = [
      ["Tipo da Ação", action.type_action || "NÃO ESPECIFICADA"],
      ["Instituição / Local", action.institution_name || "Não informado"],
      ["Endereço", action.place_action || "Não informado"],
      ["Horário", `${action.start_time || "--"} às ${action.final_hour || "--"}`],
    ];

    // Público Estimado: somente Ação 1
    if (isFirstAction && showEstimatedPublic) {
      const estimadoDisplay = (action.approach && Number(action.approach) > 0) ? String(action.approach) : "Não informado";
      actionData.push(["Público Estimado", estimadoDisplay]);
    }

    actionData.push(["Público Alcançado", alcDisplay]);

    autoTable(doc, {
      startY,
      body: actionData,
      theme: "plain",
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: CONTENT_W,
      styles: { fontSize: 8.5, cellPadding: { top: 2, bottom: 2, left: 4, right: 4 }, textColor: GRAY_900, overflow: "linebreak" },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 45, textColor: NAVY_LIGHT },
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
        doc.setFont("helvetica", "italic");
        doc.setFontSize(8.5);
        doc.setTextColor(...GRAY_600);
        doc.text("Nenhum material distribuído nesta ação.", MARGIN_L + 4, startY);
        startY += 8;
      }
    } else {
      doc.setFont("helvetica", "italic");
      doc.setFontSize(8.5);
      doc.setTextColor(...GRAY_600);
      doc.text("Nenhum material distribuído nesta ação.", MARGIN_L + 4, startY);
      startY += 8;
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

  const taxaText = totalsEstimado > 0 ? `${((totalsAlcancado / totalsEstimado) * 100).toFixed(1)}%` : "N/A";
  const consolidadoData = [
    ...(showEstimatedPublic ? [["Público Estimado (total)", totalsEstimado.toLocaleString("pt-BR")]] : []),
    ["Público Alcançado (total)", totalsAlcancado.toLocaleString("pt-BR")],
    ["Ações Realizadas", String(actions.length)],
    ["Taxa de Alcance", taxaText],
  ];

  autoTable(doc, {
    startY,
    head: [["Indicador", "Valor"]],
    body: consolidadoData,
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
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: CONTENT_W,
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900, overflow: "linebreak" },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
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
      margin: { left: MARGIN_L, right: MARGIN_R },
      tableWidth: CONTENT_W,
      styles: { fontSize: 9, cellPadding: { top: 2.5, bottom: 2.5, left: 4, right: 4 }, textColor: GRAY_900, overflow: "linebreak" },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 48, textColor: NAVY_LIGHT },
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
  //  SECTION — RELATO OPERACIONAL DO CHEFE
  // ════════════════════════════════════════════════════════════════════════

  if (form.general_observations) {
    if (startY > pageHeight - 40) {
      doc.addPage();
      startY = 20;
    }

    startY = drawSectionHeader("RELATO OPERACIONAL DO CHEFE", startY);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(...GRAY_900);
    const relatoText = form.general_observations;
    const splitRelato = doc.splitTextToSize(relatoText, CONTENT_W);
    doc.text(splitRelato, MARGIN_L + 4, startY);
    startY += splitRelato.length * 4.5 + 8;
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
  const concText = `O presente documento consolida as informações registradas no Sistema Integrado da Educação – SIED referentes à atividade identificada, incluindo execução operacional, frequência dos participantes, ações realizadas, ${showEstimatedPublic ? "público estimado, " : ""}público alcançado, materiais distribuídos e eventuais ocorrências. Este relatório possui caráter técnico-institucional e integra o acervo documental do programa Lei Seca Educação.`;
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

  if (openInNewTab) {
    window.open(url, "_blank");
    return;
  }

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

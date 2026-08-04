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
  
  const addFooter = () => {
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(100);
      const now = new Date();
      const footerText = `LEI SECA EDUCAÇÃO | Sistema Integrado da Educação – SIED | Documento gerado automaticamente | ${now.toLocaleDateString("pt-BR")} às ${now.toLocaleTimeString("pt-BR")}`;
      doc.text(footerText, 15, pageHeight - 10);
      doc.text(`Página ${i}`, pageWidth - 15, pageHeight - 10, { align: "right" });
    }
  };

  let startY = 15;

  // Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(20, 50, 100);
  doc.text("LEI SECA EDUCAÇÃO", pageWidth / 2, startY, { align: "center" });
  startY += 7;
  doc.setFontSize(14);
  doc.text("RELATÓRIO TÉCNICO DE ATIVIDADE", pageWidth / 2, startY, { align: "center" });
  startY += 12;

  // 1. Identificação da atividade
  const identData = [
    ["Protocolo", form.agenda ? `#${form.agenda}` : "Não informado"],
    ["Ordem de Serviço", selectedAgenda?.service_order_number || "Não informada"],
    ["Data", form.operation_date ? formatDateBR(form.operation_date) : "Não informada"],
    ["Horário", selectedAgenda ? `${selectedAgenda.start_time?.slice(0,5) || "--"} às ${selectedAgenda.end_time?.slice(0,5) || "--"}` : "Não informado"],
    ["Natureza da atividade", form.agenda_title || "Não informada"],
    ["Instituição/Local", form.agenda_location || "Não informado"],
    ["Endereço", selectedAgenda?.address || "Não informado"],
    ["Município", selectedAgenda?.city || selectedAgenda?.municipality_ref_name || "Não informado"],
  ].filter(row => row[1] && row[1] !== "Não informado" && row[1] !== "-" && row[1] !== "null" && row[1] !== "undefined");

  autoTable(doc, {
    startY,
    head: [["Identificação da atividade", ""]],
    body: identData,
    theme: "plain",
    headStyles: { fillColor: [20, 50, 100], textColor: 255, fontStyle: "bold" },
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 } },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // 2. Responsabilidade operacional
  const chief = form.education_agents ? form.education_agents.match(/Chefe(?: respons[áa]vel)?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  const agents = form.education_agents ? form.education_agents.match(/Agentes?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  const supports = form.education_agents ? form.education_agents.match(/Apoio?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  
  const respData = [];
  if (form.team) respData.push(["Equipe", form.team]);
  if (chief) respData.push(["Chefe responsável", chief]);
  if (agents) respData.push(["Agentes de Educação", agents]);
  if (supports) respData.push(["Apoios", supports]);

  if (respData.length) {
    autoTable(doc, {
      startY,
      head: [["Responsabilidade operacional", ""]],
      body: respData,
      theme: "plain",
      headStyles: { fillColor: [20, 50, 100], textColor: 255, fontStyle: "bold" },
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 } },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // 3. Frequência dos participantes
  const absences = Object.values(attendanceForm || {}).filter(d => d.is_absent === true);
  
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(20, 50, 100);
  doc.text("FREQUÊNCIA DOS PARTICIPANTES", 15, startY);
  startY += 5;

  if (absences.length === 0) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(0);
    doc.text("Sem faltas.", 15, startY);
    startY += 10;
  } else {
    const absData = absences.map(a => [
      a.member?.name || "Desconhecido", 
      a.member?.typeLabel || "Não informado", 
      (a.reason || "").trim() || "Justificativa não informada."
    ]);
    autoTable(doc, {
      startY,
      head: [["Participante ausente", "Função", "Justificativa"]],
      body: absData,
      theme: "striped",
      headStyles: { fillColor: [200, 200, 200], textColor: 0, fontStyle: "bold" },
      styles: { fontSize: 10, cellPadding: 3 },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // 4. Ações executadas
  const actions = form.actions || [];
  let totalsEstimado = 0;
  let totalsAlcancado = 0;

  actions.forEach((action, index) => {
    totalsEstimado += Number(action.approach || 0);
    totalsAlcancado += Number(action.approached_actions || 0);

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(20, 50, 100);
    doc.text(`AÇÃO ${String(index + 1).padStart(2, '0')} — ${(action.type_action || "AÇÃO NÃO ESPECIFICADA").toUpperCase()}`, 15, startY);
    startY += 5;

    const actionData = [
      ["Tipo da ação", action.type_action || "Não informado"],
      ["Instituição/Local", action.institution_name || "Não informado"],
      ["Endereço", action.place_action || "Não informado"],
      ["Horário", `${action.start_time || "--"} às ${action.final_hour || "--"}`],
      ["Público estimado", action.approach || "0"],
      ["Público alcançado", action.approached_actions || "0"],
    ];

    autoTable(doc, {
      startY,
      body: actionData.filter(r => r[1] && r[1] !== "Não informado" && r[1] !== "-- às --" && r[1] !== "0" && r[1] !== "-"),
      theme: "plain",
      styles: { fontSize: 10, cellPadding: 2 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 } },
    });
    startY = doc.lastAutoTable.finalY + 5;

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
            materials.push([name, qty.toString()]);
          }
        }
      });
      if (materials.length > 0) {
        autoTable(doc, {
          startY,
          head: [["Material distribuído", "Quantidade"]],
          body: materials,
          theme: "striped",
          headStyles: { fillColor: [240, 240, 240], textColor: 0, fontStyle: "bold" },
          styles: { fontSize: 10, cellPadding: 2 },
        });
        startY = doc.lastAutoTable.finalY + 10;
      } else {
        startY += 5;
      }
    } else {
      startY += 5;
    }
  });

  // 5. Público e resultados
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(20, 50, 100);
  doc.text("PÚBLICO E RESULTADOS", 15, startY);
  startY += 5;

  autoTable(doc, {
    startY,
    head: [["Indicador", "Quantidade"]],
    body: [
      ["Público estimado", totalsEstimado.toString()],
      ["Público alcançado", totalsAlcancado.toString()],
      ["Quantidade de ações realizadas", actions.length.toString()]
    ],
    theme: "striped",
    headStyles: { fillColor: [240, 240, 240], textColor: 0, fontStyle: "bold" },
    styles: { fontSize: 10, cellPadding: 3 },
  });
  startY = doc.lastAutoTable.finalY + 10;

  // 6. Recursos operacionais
  const recursos = [];
  if (form.cars) recursos.push(["Viaturas", form.cars.split(",").map(c => c.trim()).filter((v,i,a) => a.indexOf(v)===i).join(", ")]); // viaturas sem duplicidade
  if (form.breathalyzers) recursos.push(["Etilômetros", form.breathalyzers]);
  
  if (recursos.length > 0) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(20, 50, 100);
    doc.text("RECURSOS OPERACIONAIS", 15, startY);
    startY += 5;
    
    autoTable(doc, {
      startY,
      body: recursos,
      theme: "plain",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 } },
    });
    startY = doc.lastAutoTable.finalY + 10;
  }

  // 7. Ocorrência envolvendo viatura ou efetivo
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(20, 50, 100);
  doc.text("OCORRÊNCIA (VIATURA OU EFETIVO)", 15, startY);
  startY += 5;

  if (form.has_exceptional_occurrence) {
    const ocType = form.exceptional_occurrence_type === "VEHICLE_BREAKDOWN" ? "Viatura" 
                 : form.exceptional_occurrence_type === "WORK_ACCIDENT" ? "Efetivo" 
                 : form.exceptional_occurrence_type;
    autoTable(doc, {
      startY,
      body: [
        ["Tipo", ocType || "Não informado"],
        ["Descrição", form.exceptional_occurrence_description || "Não informada"],
        ["Providências adotadas", form.exceptional_occurrence_actions_taken || "Não informadas"],
        ["Impacto na atividade", form.exceptional_occurrence_impact || "Não informado"],
      ],
      theme: "plain",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 } },
    });
    startY = doc.lastAutoTable.finalY + 10;
  } else {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(0);
    doc.text("Não houve ocorrência envolvendo viatura ou efetivo.", 15, startY);
    startY += 10;
  }

  // 8. Observações técnicas
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(20, 50, 100);
  doc.text("OBSERVAÇÕES TÉCNICAS", 15, startY);
  startY += 5;

  const obs = [];
  if (form.general_observations && form.general_observations.trim()) obs.push(form.general_observations);
  if (form.occurrence_observation && form.occurrence_observation.trim()) obs.push(form.occurrence_observation);
  
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(0);
  
  if (obs.length > 0) {
    const obsText = obs.join("\n\n");
    const splitObs = doc.splitTextToSize(obsText, pageWidth - 30);
    doc.text(splitObs, 15, startY);
    startY += splitObs.length * 4 + 10;
  } else {
    doc.text("Sem observações adicionais.", 15, startY);
    startY += 10;
  }

  // Check page break for signatures
  if (startY > pageHeight - 60) {
    doc.addPage();
    startY = 20;
  }

  // 9. Conclusão Institucional
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(20, 50, 100);
  doc.text("CONCLUSÃO", 15, startY);
  startY += 5;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(0);
  const concText = "O presente documento consolida as informações registradas no Sistema Integrado da Educação – SIED referentes à atividade identificada, incluindo execução operacional, frequência dos participantes, ações realizadas, público estimado, público alcançado, materiais distribuídos e eventuais ocorrências.";
  const splitConc = doc.splitTextToSize(concText, pageWidth - 30);
  doc.text(splitConc, 15, startY);
  startY += splitConc.length * 4 + 20;

  // 10. Assinaturas
  doc.text("____________________________________", pageWidth / 2, startY, { align: "center" });
  startY += 5;
  doc.text("Chefe responsável pela atividade", pageWidth / 2, startY, { align: "center" });
  startY += 15;
  doc.text("____________________________________", pageWidth / 2, startY, { align: "center" });
  startY += 5;
  doc.text("Validação institucional", pageWidth / 2, startY, { align: "center" });
  startY += 5;
  doc.text("Lei Seca Educação", pageWidth / 2, startY, { align: "center" });

  // Add footer to all pages
  addFooter();

  // Create Blob and download
  const blob = doc.output("blob");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  
  const osNum = selectedAgenda?.service_order_number;
  const proto = form.agenda;
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

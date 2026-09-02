import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

const text = (value) => (value === null || value === undefined || value === "" ? "Não informado" : String(value));

function addSection(doc, title, rows) {
  doc.setFontSize(12);
  doc.setTextColor(0, 48, 120);
  doc.text(title, 14, doc.lastAutoTable ? doc.lastAutoTable.finalY + 12 : 20);
  autoTable(doc, {
    startY: doc.lastAutoTable ? doc.lastAutoTable.finalY + 15 : 24,
    head: [["Campo", "Valor"]],
    body: rows.map(([label, value]) => [label, text(value)]),
    theme: "grid",
    styles: { fontSize: 8, cellWidth: "wrap", valign: "top" },
    headStyles: { fillColor: [0, 72, 215] },
    columnStyles: { 0: { cellWidth: 62 }, 1: { cellWidth: 120 } },
  });
}

export function generateInspectionReportPdf(report) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  doc.setFontSize(16);
  doc.setTextColor(0, 48, 120);
  doc.text("Relatório de Fiscalização", 14, 14);

  addSection(doc, "Dados da operação", [
    ["Equipe", report.team], ["Data da operação", report.operation_date],
    ["Chefe da equipe civil", report.civil_chief_name], ["Chefe da equipe militar", report.military_chief_name],
    ["Efetivo militar", report.segov_team_military], ["Efetivo civil", report.segov_team_civil],
    ["Viaturas OLS utilizadas na operação", report.cars], ["Agentes do Detran", report.agent_detran], ["Reboques", report.number_trailers],
  ]);
  addSection(doc, "Complemento", [
    ["OPM de apoio", report.support_opm], ["Efetivo PMERJ de apoio", report.support_pmerj_staff],
    ["Viaturas de apoio", report.support_vehicles], ["Motivos para baixa abordagem", report.low_approach_reasons],
    ["Autos de infração da equipe", report.team_violation_notices], ["Especifique os AI utilizados", report.specified_violation_notices],
  ]);
  addSection(doc, "Alterações", [
    ["Efetivo OLS", report.change_ols], ["Equipe de apoio", report.change_support],
    ["Alterações de material/equipamento/viatura", report.changes_material], ["Geral", report.miscellaneous_changes],
    ["Observações gerais", report.changes_general],
  ]);
  (report.operations || []).forEach((operation, index) => {
    addSection(doc, `Operação ${index + 1}`, [
      ["Endereço da operação", operation.address_operation], ["Outro endereço não listado", operation.another_not_listed],
      ["Saída do ponto de encontro", operation.departure_meeting_point], ["Montagem da operação", operation.operation_assembly],
      ["Primeira abordagem", operation.first_approach], ["Encerramento", operation.closing],
      ["Abordagens", operation.approach], ["Reconduzidos", operation.reconductor], ["Recusas", operation.refusal],
      ["Celebridades/Autoridades", operation.celebrities_authorities], ["Resultado 0,00 a 0,04", operation.four_ml],
      ["Resultado 0,05 a 0,33", operation.thirtythree_ml], ["Resultado maior ou igual a 0,34", operation.thirtyfour_ml],
      ["Quantidade de testes passivos realizados", operation.passive_tests_performed], ["CNH recolhidas", operation.cnh_collected],
      ["Multados", operation.fined], ["Rebocados", operation.towed], ["Deliberações de remoção", operation.removal_resolutions],
      ["Prisões por outros meios de prova de alcoolemia", operation.arrests_means_evidence], ["Art. 307 do CTB", operation.art307],
      ["Ocorrências criminais", operation.criminal_occurrences], ["Dirigir com CNH cassada", operation.driving_canceled_license],
      ["Observações das deliberações de veículos", operation.vehicle_resolutions], ["Observações dos testes administrativos", operation.administrative_tests],
      ["Alterações de material", operation.changes_material],
    ]);
    if ((operation.fines || []).length) {
      autoTable(doc, {
        startY: doc.lastAutoTable.finalY + 8,
        head: [["Autos / infrações detalhados", "Quantidade"]],
        body: operation.fines.map((fine) => [text(fine.art), text(fine.quant)]),
        theme: "grid",
        styles: { fontSize: 8 },
        headStyles: { fillColor: [0, 72, 215] },
      });
    }
  });
  doc.save(`relatorio-fiscalizacao-${report.operation_date || report.id}.pdf`);
}

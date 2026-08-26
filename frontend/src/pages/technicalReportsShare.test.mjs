import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { buildReportShareSummary } from "../utils/reportShareSummary.js";

const pageSource = fs.readFileSync(new URL("./TechnicalReportsPage.jsx", import.meta.url), "utf8");

test("relatório técnico desktop compartilha o resumo estruturado", () => {
  assert.match(pageSource, /import \{ buildReportShareSummary \} from "\.\.\/utils\/reportShareSummary\.js"/);
  assert.match(pageSource, /buildReportShareSummary\(form, selectedAgendaForPreview \|\| \{\}, attendanceStats\)/);
  assert.match(pageSource, /executeShare\(reportShareSummary,/);
  assert.match(pageSource, /Compartilhar relatório/);
});

test("resumo do desktop é estruturado e não inclui elementos da interface", () => {
  const summary = buildReportShareSummary(
    {
      operation_date: "2026-08-26",
      team: "Equipe Centro",
      agenda_location: "Auditório",
      actions: [{ type_action: "Palestra", approached_lectures: 40 }],
    },
    { action_type_ref_name: "Palestra" },
    { loaded: true, total: 1, present: 1, absent: 0 }
  );

  assert.match(summary, /^RELATÓRIO TÉCNICO - OPERAÇÃO LEI SECA/);
  assert.doesNotMatch(summary, /Dashboard|Sair|filtros|versão do sistema/i);
  assert.doesNotMatch(pageSource, /innerText|textContent|document\.body|getSelection/);
});

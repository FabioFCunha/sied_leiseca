import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./TechnicalReportsPage.jsx", import.meta.url), "utf8");

test("visualização carrega o relatório completo antes de gerar o resumo", () => {
  assert.match(source, /const completeReport = await api\(`\/education-reports\/\$\{report\.id\}\/`\)/);
  assert.match(source, /const reportAgendaPk = agendaPk\(completeReport\.agenda\)/);
  assert.match(source, /hydrateForm\(\{ \.\.\.completeReport, street_action_details: resolvedDetails \}/);
});

test("edição também carrega o relatório completo antes da hidratação", () => {
  const detailRequests = source.match(/const completeReport = await api\(`\/education-reports\/\$\{report\.id\}\/`\)/g) || [];
  assert.equal(detailRequests.length, 2);
  assert.match(source, /setEditing\(completeReport\.id\)/);
});

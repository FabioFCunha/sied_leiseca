import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const pageSource = fs.readFileSync(new URL("./TechnicalReportsPage.jsx", import.meta.url), "utf8");

test("desktop reutiliza o pré-preenchimento compartilhado da primeira ação", () => {
  assert.match(pageSource, /from "\.\.\/utils\/reportActionPrefill\.js"/);
  assert.match(pageSource, /buildFirstActionAgendaPrefill\(agenda, actionTypes\)/);
  assert.match(pageSource, /applyBlankActionPrefill\(currentAction, agendaPrefill\)/);
  assert.match(pageSource, /applyBlankActionPrefill\(action, agendaPrefill\)/);
});

test("desktop mantém abordagens e acessibilidade fora do pré-preenchimento", () => {
  assert.doesNotMatch(pageSource, /approached_actions:\s*[^\n]*agenda\.quantity/);
  assert.doesNotMatch(pageSource, /accessibility_conditions_met:\s*[^\n]*agenda\./);
});

test("Ação de Rua hidrata a primeira ação e carrega o detalhe da OS antes do prefill", () => {
  assert.match(pageSource, /meaningfulCurrentActions\.map\(\(action, index\) => buildAgendaAction\(action, index === 0\)\)/);
  assert.match(pageSource, /\[buildAgendaAction\(\{\}, true\)\]/);
  assert.match(pageSource, /const detailedAgenda = await api\(`\/agendas\/\$\{agendaId\}\/`\)/);
  assert.match(pageSource, /const detailedAgenda = await selectAgendaForReport\(agenda, \{ preserveCurrent: false \}\)/);
});

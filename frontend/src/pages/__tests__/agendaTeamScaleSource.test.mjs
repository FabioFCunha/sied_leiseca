import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const agendaPageSource = fs.readFileSync(new URL("../AgendaPage.jsx", import.meta.url), "utf8");
const calendarPageSource = fs.readFileSync(new URL("../CalendarPage.jsx", import.meta.url), "utf8");

test("AgendaPage avisa que o efetivo TEAM é vinculado à Escala", () => {
  assert.match(agendaPageSource, /Efetivo vinculado à Escala/);
  assert.match(agendaPageSource, /Ir para a Escala/);
  assert.match(
    agendaPageSource,
    /Nenhuma equipe foi encontrada na Escala para esta data\. Cadastre ou ajuste a equipe diretamente na Escala antes de criar a Ordem de Serviço\./
  );
});

test("AgendaPage não renderiza ações de inclusão manual de agentes no bloco TEAM", () => {
  assert.doesNotMatch(agendaPageSource, /Adicionar outro agente/);
  assert.doesNotMatch(agendaPageSource, /removeAgent\(/);
});

test("CalendarPage consome o aviso de efetivo ausente na Escala", () => {
  assert.match(calendarPageSource, /getAgendaStaffWarning/);
});

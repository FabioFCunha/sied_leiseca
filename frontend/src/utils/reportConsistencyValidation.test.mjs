import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { getReportConsistencyErrors } from "./reportConsistencyValidation.js";

const lecture = (start, end, publicReached, kits) => ({
  start_time: start,
  final_hour: end,
  approached_lectures: publicReached,
  approached_actions: publicReached,
  distribution_materials_distributed: `KIT COM 7 REVISTINHAS | ${kits}`,
});

test("bloqueia material distribuído maior que o público da ação", () => {
  const errors = getReportConsistencyErrors([lecture("09:00", "10:00", 50, 51)]);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /não pode ser maior que o público alcançado/);
});

test("bloqueia horários sobrepostos entre ações", () => {
  const errors = getReportConsistencyErrors([
    lecture("09:00", "11:00", 50, 20),
    lecture("10:30", "12:00", 30, 10),
  ]);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /conflita com a Ação 1/);
});

test("aceita horários consecutivos e kits iguais ao público", () => {
  const errors = getReportConsistencyErrors([
    lecture("09:00", "11:00", 50, 50),
    lecture("11:00", "12:00", 30, 10),
  ]);
  assert.deepEqual(errors, []);
});

test("usa abordados em ações para atividade de rua", () => {
  const errors = getReportConsistencyErrors([{
    ...lecture("09:00", "10:00", 0, 31),
    approached_actions: 30,
  }]);
  assert.match(errors[0], /\(31\).*\(30\)/);
});

test("usa o número de abordagens quando a primeira ação não tem público de palestra", () => {
  const errors = getReportConsistencyErrors([{
    ...lecture("10:00", "11:00", 0, 7),
    approached_actions: 5,
  }]);
  assert.match(errors[0], /\(7\).*\(5\)/);
});

test("aceita atividade que atravessa a meia-noite", () => {
  const errors = getReportConsistencyErrors([lecture("21:00", "01:00", 50, 20)]);
  assert.deepEqual(errors, []);
});

test("não soma materiais diferentes para comparar com o público", () => {
  const errors = getReportConsistencyErrors([{
    ...lecture("09:00", "10:00", 50, 50),
    distribution_materials_distributed: "KIT COM 7 REVISTINHAS | 50\nVENTAROLA FUTEBOL | 50",
  }]);
  assert.deepEqual(errors, []);
});

test("validação é acionada apenas no envio para conferência", () => {
  const desktop = fs.readFileSync(new URL("../pages/TechnicalReportsPage.jsx", import.meta.url), "utf8");
  const mobile = fs.readFileSync(new URL("../pages/mobile/MobileReportFormPage.jsx", import.meta.url), "utf8");

  const desktopDraft = desktop.slice(desktop.indexOf("const saveReport"), desktop.indexOf("const submit ="));
  const desktopReview = desktop.slice(desktop.indexOf("const submitFinal"), desktop.indexOf("const submitRectify"));
  const mobileDraft = mobile.slice(mobile.indexOf("const handleSaveDraft"), mobile.indexOf("const resetSharePrompt"));
  const mobileReview = mobile.slice(mobile.indexOf("const handleSubmitForReview"), mobile.indexOf("const handleSharePrompt"));

  assert.doesNotMatch(desktopDraft, /assertReportConsistency/);
  assert.match(desktopReview, /assertReportConsistency/);
  assert.doesNotMatch(mobileDraft, /assertReportConsistency/);
  assert.match(mobileReview, /assertReportConsistency/);
});

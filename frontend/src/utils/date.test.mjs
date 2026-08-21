import fs from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

import { buildWeekGridCells, formatLocalISODate } from "./date.js";

function datesOnly(cells) {
  return cells.filter(Boolean).map(formatLocalISODate);
}

test("agosto de 2026 mantém 01/08 no sábado e preenche as seis células anteriores", () => {
  const cells = buildWeekGridCells("2026-08-01", "2026-08-31");

  assert.deepEqual(cells.slice(0, 6), [null, null, null, null, null, null]);
  assert.equal(formatLocalISODate(cells[6]), "2026-08-01");
  assert.equal(cells[6].getDay(), 6);
  assert.equal(formatLocalISODate(cells[7]), "2026-08-02");
  assert.deepEqual(datesOnly(cells), Array.from({ length: 31 }, (_, index) => `2026-08-${String(index + 1).padStart(2, "0")}`));
});

test("intervalo iniciado no domingo não recebe preenchimento antes do primeiro dia", () => {
  const cells = buildWeekGridCells("2026-11-01", "2026-11-30");

  assert.equal(formatLocalISODate(cells[0]), "2026-11-01");
  assert.equal(cells[0].getDay(), 0);
  assert.deepEqual(cells.slice(-5), [null, null, null, null, null]);
});

test("intervalo iniciado na segunda-feira recebe uma célula vazia de domingo", () => {
  const cells = buildWeekGridCells("2026-06-01", "2026-06-30");

  assert.equal(cells[0], null);
  assert.equal(formatLocalISODate(cells[1]), "2026-06-01");
  assert.equal(cells[1].getDay(), 1);
});

test("intervalo que termina no meio da semana recebe somente células vazias até sábado", () => {
  const cells = buildWeekGridCells("2026-09-01", "2026-09-30");

  assert.equal(formatLocalISODate(cells.at(-4)), "2026-09-30");
  assert.equal(cells.at(-4).getDay(), 3);
  assert.deepEqual(cells.slice(-3), [null, null, null]);
  assert.equal(datesOnly(cells).at(-1), "2026-09-30");
});

test("Escala envia à API exatamente as datas informadas nos filtros", () => {
  const source = fs.readFileSync(new URL("../pages/ShiftSchedulePage.jsx", import.meta.url), "utf8");

  assert.match(source, /date_from:\s*periodFilter\.dateFrom/);
  assert.match(source, /date_to:\s*periodFilter\.dateTo/);
  assert.doesNotMatch(source, /buildWeekAlignedDays/);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../StatisticsPage.jsx", import.meta.url), "utf8");

assert.ok(source.includes('["MATERIAL - Geral", text.materials'));
assert.ok(source.includes('["MATERIAL - Kit com 7 Revistinhas", text.kitsWithSevenComics'));
assert.ok(source.includes('"Kits com 7 Revistinhas"'));
assert.ok(source.includes('"Total de kits distribuídos"'));
assert.ok(source.includes('Fonte: relatórios técnicos aprovados no SIED. Materiais distribuídos contabilizados a partir de 09/07/2026.'));
assert.equal(source.includes('["MATERIAL - Soprinho", text.comics'), false);

console.log("statisticsMaterialsCards.test.mjs: OK");

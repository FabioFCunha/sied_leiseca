import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./PublicAgendaRequestPage.jsx", import.meta.url), "utf8");

test("solicitação interna preserva a natureza pública ou privada", () => {
  assert.match(
    source,
    /: `\$\{form\.requester_entity_kind\} \$\{form\.requester_entity_nature\}`\.trim\(\)/,
  );
  assert.doesNotMatch(
    source,
    /requester_entity_type: internalRequest\s*\? form\.requester_entity_kind/,
  );
});

test("natureza é exigida também na solicitação interna comum", () => {
  assert.match(source, /!form\.requester_entity_nature/);
  assert.match(source, /Informe se a instituição solicitante é pública ou privada/);
  assert.ok(
    source.match(/aria-label="Natureza da entidade"/g)?.length >= 2,
    "os dois layouts devem oferecer a seleção da natureza",
  );
});

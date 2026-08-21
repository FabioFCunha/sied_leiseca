import test from "node:test";
import assert from "node:assert/strict";

import { formatApiError } from "./client.js";

test("formatApiError flattens nested action errors with action numbers", () => {
  const message = formatApiError({
    actions: {
      0: {
        type_action: [
          "Selecione o tipo de palestra ou ação educativa realizada.",
        ],
      },
      1: {
        approached_actions: [
          "Informe o público alcançado.",
        ],
      },
    },
  });

  assert.equal(
    message,
    [
      "Ação 01: Selecione o tipo de palestra ou ação educativa realizada.",
      "Ação 02: Informe o público alcançado.",
    ].join("\n"),
  );
});

test("formatApiError preserves top-level detail messages", () => {
  assert.equal(
    formatApiError({ detail: "Não foi possível localizar a escala vinculada a este relatório." }),
    "Não foi possível localizar a escala vinculada a este relatório.",
  );
});

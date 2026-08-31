import assert from "node:assert/strict";

import { canReviewInspectionStatistics } from "./permissions.js";

assert.equal(
  canReviewInspectionStatistics({ role: "MANAGER", cpf: "089.220.407-93" }),
  true,
  "Fabio é identificado pelo CPF, independentemente da formatação"
);
assert.equal(
  canReviewInspectionStatistics({ role: "MANAGER", email: "fabiocunhaosp@gmail.com" }),
  true,
  "o e-mail é apenas alternativa de compatibilidade"
);
assert.equal(
  canReviewInspectionStatistics({ role: "MANAGER", cpf: "00000000000", email: "outro@exemplo.com" }),
  false,
  "outro Gestor continua bloqueado"
);
assert.equal(canReviewInspectionStatistics({ role: "USER" }), false);
assert.equal(canReviewInspectionStatistics({ role: "VISITOR", sector_name: "Outro setor" }), false);
assert.equal(
  canReviewInspectionStatistics({ role: "VISITOR", sector_name: "OLS/CooAdm" }),
  true,
  "a autorização institucional existente é preservada"
);

console.log("permissions.test.mjs: OK");

import assert from "node:assert/strict";

import { canAccessRoute, canModify } from "./permissions.js";

const educationManager = { role: "MANAGER", access_areas: ["EDUCATION"], is_read_only: false };
assert.equal(canAccessRoute(educationManager, ["MANAGER"], "ESTATISTICAS"), true);
assert.equal(canAccessRoute(educationManager, ["MANAGER"], "FISCALIZACAO_ESTATISTICAS"), false);

const generalViewer = { role: "VISITOR", access_areas: ["EDUCATION", "INSPECTION"], is_read_only: true };
assert.equal(canAccessRoute(generalViewer, ["MANAGER"], "ESTATISTICAS"), true);
assert.equal(canAccessRoute(generalViewer, ["MANAGER"], "FISCALIZACAO_ESTATISTICAS"), true);
assert.equal(canAccessRoute(generalViewer, ["MANAGER"], "USUARIOS"), false);
assert.equal(canModify(generalViewer), false);

console.log("permissions tests passed");

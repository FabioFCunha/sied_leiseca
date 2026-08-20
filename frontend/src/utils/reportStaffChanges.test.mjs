import assert from "node:assert/strict";
import { buildStaffChanges } from "./reportStaffChanges.js";

const scheduleWithChanges = {
  members: {
    agents: [
      { id: 1, name: "Extra Valido", is_extra: true },
      { id: "swap-2", name: "Substituto", is_swap: true, swap_for: "Titular" },
    ],
  },
  removed_agents: [3],
  member_changes: [
    { action: "REMOVED", member_type: "AGENT", member_id: 3, member_name: "Removido" },
    { action: "REMOVED", member_type: "AGENT", member_id: 4, member_name: "Nao removido" },
  ],
};

assert.deepEqual(buildStaffChanges(scheduleWithChanges), [
  "Extra: Extra Valido",
  "Troca: Substituto (no lugar de Titular)",
  "Retirado: Removido",
]);
assert.deepEqual(buildStaffChanges({ members: { agents: [] } }), [], "sem alteracoes limpa o valor anterior");

console.log("reportStaffChanges.test.mjs: OK");

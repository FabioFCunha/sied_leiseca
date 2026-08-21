import assert from "node:assert/strict";
import { agendaPk } from "./reportPayload.js";

assert.equal(agendaPk({ id: 5807, title: "OS 5807" }), 5807);
assert.equal(agendaPk("", { id: 5807 }), 5807);
assert.equal(agendaPk(undefined, "5807"), 5807);
assert.equal(agendaPk("5807"), 5807);
assert.equal(agendaPk(5807), 5807);
assert.equal(agendaPk(null), null);

console.log("reportPayload tests passed");

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { normalizeCalendarText } from "./calendarText.js";

const internalRequest = normalizeCalendarText("SolicitaÃ§Ãµes internas");
const externalRequest = normalizeCalendarText("SolicitaÃÂ§ÃÂµes externas");
const actionType = normalizeCalendarText("AÃ§Ã£o de educaÃ§Ã£o/conscientizaÃ§Ã£o");

assert.equal(internalRequest, "Solicitações internas");
assert.equal(externalRequest, "Solicitações externas");
assert.equal(actionType, "Ação de educação/conscientização");
assert.doesNotMatch(`${internalRequest} ${externalRequest}`, /SolicitaÃ|Ã|Â|�/);
assert.equal(normalizeCalendarText("Agenda sem alteração"), "Agenda sem alteração");

const calendarPageSource = await readFile(
  new URL("../pages/CalendarPage.jsx", import.meta.url),
  "utf8",
);
assert.match(calendarPageSource, /agenda\.start_time\?\.slice\(0, 5\)/);
assert.match(calendarPageSource, /serviceTeamLabel\(agenda\)/);
assert.match(calendarPageSource, /statusClass\[agenda\.status\]/);

console.log("calendarText.test.mjs: OK");

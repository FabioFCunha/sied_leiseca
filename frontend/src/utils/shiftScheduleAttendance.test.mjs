import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  buildShiftScheduleDetailUrl,
  buildTeamAttendanceForm,
} from "./shiftScheduleAttendance.js";

assert.equal(
  buildShiftScheduleDetailUrl(153, 5836),
  "/shift-schedules/153/?agenda=5836",
  "carrega a escala no contexto da agenda quando ela foi informada",
);
assert.equal(
  buildShiftScheduleDetailUrl(153, null),
  "/shift-schedules/153/",
  "mantém o acesso direto por escala quando não há agenda",
);

const contextualMembers = {
  chiefs: [],
  agents: [
    { id: 10, name: "Douglas Jr. Lisboa Mazzoni", is_absent: false },
    { id: 11, name: "Marcio da Silva Alcantara", is_absent: null },
  ],
  supports: [],
};
const attendanceForm = buildTeamAttendanceForm(contextualMembers);
assert.deepEqual(
  Object.values(attendanceForm).map((member) => member.name),
  ["Douglas Jr. Lisboa Mazzoni", "Marcio da Silva Alcantara"],
  "preserva todos os agentes retornados pela composicao contextual da OS",
);

const reportFormSource = await readFile(
  new URL("../pages/mobile/MobileReportFormPage.jsx", import.meta.url),
  "utf8",
);
assert.match(
  reportFormSource,
  /frequencia\/escala\/\$\{reportSchedule\.id\}\/editar\?agenda=\$\{encodeURIComponent\(agenda\.id\)\}/,
  "o botao Gerenciar Frequencia preserva o contexto da agenda",
);

const editPageSource = await readFile(
  new URL("../pages/mobile/MobileShiftAttendanceEditPage.jsx", import.meta.url),
  "utf8",
);
assert.match(
  editPageSource,
  /api\(buildShiftScheduleDetailUrl\(id, agendaId\)/,
  "a edicao carrega a escala usando o contexto recebido na query string",
);
assert.match(
  editPageSource,
  /api\(`\/shift-schedules\/\$\{id\}\/`, \{\s*method: "PATCH"/,
  "o salvamento continua no mesmo endpoint da escala",
);

const viewPageSource = await readFile(
  new URL("../pages/mobile/MobileShiftAttendancePage.jsx", import.meta.url),
  "utf8",
);
assert.match(
  viewPageSource,
  /api\(buildShiftScheduleDetailUrl\(id, agendaId\)/,
  "a visualizacao tambem carrega a escala usando o contexto da agenda",
);

console.log("shiftScheduleAttendance tests passed");

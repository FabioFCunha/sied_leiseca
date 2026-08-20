import assert from "node:assert/strict";
import { buildReportShareSummary } from "../../utils/reportShareSummary.js";
import fs from "node:fs";

const message = buildReportShareSummary(
  {
    operation_date: "2026-08-20",
    team: "Equipe Ação",
    agenda_location: "Centro do Rio",
    actions: [{
      institution_name: "Escola São José",
      place_action: "Rua da Educação, 10",
      start_time: "08:30:00",
      final_hour: "10:15:00",
      approached_lectures: 125,
    }],
  },
  { action_type_ref_name: "Palestra" },
  { loaded: true, total: 3, present: 2, absent: 1 }
);

assert.doesNotMatch(message, /�/, "a mensagem nao deve conter caractere de substituicao");
assert.match(message, /• Data: 20\/08\/2026/, "preserva data");
assert.match(message, /• Equipe: Equipe Ação/, "preserva acentos na equipe");
assert.match(message, /• Local: Centro do Rio/, "preserva local");
assert.match(message, /• Modalidade: Palestra/, "preserva modalidade");
assert.match(message, /• Frequência: 2 presente\(s\), 1 ausente\(s\)/, "preserva frequencia");
assert.match(message, /• Endereço: Rua da Educação, 10/, "preserva endereco");
assert.match(message, /• Horário: 08:30 às 10:15/, "preserva horario");
assert.match(message, /• Abordados em palestras: 125/, "preserva abordados");

const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
assert.equal(decodeURIComponent(url.split("text=")[1]), message, "URL do WhatsApp decodifica para a mensagem original");

const detailsSource = fs.readFileSync(new URL("./MobileReportDetailsPage.jsx", import.meta.url), "utf8");
assert.match(detailsSource, /buildEducationAgentsText/, "detalhe mobile usa a composicao final estruturada");
assert.match(detailsSource, /agenda_service_order_mode === "TEAM"/, "detalhe mobile protege o modo TEAM contextualizado");

console.log("MobileReportFormPage.share.test.mjs: OK");

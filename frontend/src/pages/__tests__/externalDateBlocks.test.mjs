import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const calendar = fs.readFileSync(new URL("../CalendarPage.jsx", import.meta.url), "utf8");
const publicForm = fs.readFileSync(new URL("../PublicAgendaRequestPage.jsx", import.meta.url), "utf8");

test("Calendário remove apenas o painel de filtros e preserva controles e legenda", () => {
  assert.doesNotMatch(calendar, /<Filters/);
  assert.match(calendar, /Mês/);
  assert.match(calendar, /Semana/);
  assert.match(calendar, /Dia/);
  assert.match(calendar, /aria-label="Anterior"/);
  assert.match(calendar, /aria-label="Próximo"/);
  assert.match(calendar, /className="jump-date"/);
  assert.match(calendar, /Pendente \/ aguardando/);
  assert.match(calendar, /Aprovada \/ confirmada/);
  assert.match(calendar, /Cancelada \/ não confirmada/);
  assert.match(calendar, /Deslocamento de viagem/);
});

test("gerenciamento é visível apenas a ADMIN e MANAGER e não esconde agendas", () => {
  assert.match(calendar, /user\?\.role === "ADMIN" \|\| user\?\.role === "MANAGER"/);
  assert.match(calendar, /Gerenciar datas indisponíveis/);
  assert.match(calendar, /dayAgendas\.map/);
  assert.match(calendar, /Indisponível para solicitação externa/);
});

test("formulário público consulta disponibilidade, bloqueia envio e preserva campos", () => {
  assert.match(publicForm, /let url = `\/public\/agenda-request\/\?date=\$\{form\.date\}`/);
  assert.match(publicForm, /if \(editMode && protocol\)[\s\S]*agenda_id=\$\{protocol\}/);
  assert.match(publicForm, /if \(internalRequest\)[\s\S]*availabilityRequest\.then/);
  assert.match(publicForm, /Promise\.all\(\[/);
  assert.match(publicForm, /public\/external-request-date-blocks/);
  assert.match(publicForm, /existingAvailabilityMessage/);
  assert.match(publicForm, /externalBlockMessage/);
  assert.match(publicForm, /dateInputRef\.current\?\.focus/);
  assert.match(publicForm, /setMessage\(dateMessage\)/);
  assert.match(publicForm, /function externalBlockMessageFor/);
  assert.match(publicForm, /O período de \$\{startDate\} a \$\{endDate\} está indisponível para solicitações externas/);
  assert.match(publicForm, /A data \$\{startDate\} está indisponível para solicitações externas/);
  assert.match(publicForm, /formatDateBR\(block\.start_date\)/);
  assert.match(publicForm, /aria-invalid=\{Boolean\(dateMessage\)\}/);
  assert.match(publicForm, /String\(err\?\.message \|\| "Não foi possível enviar a solicitação\."\)/);
  assert.doesNotMatch(publicForm, /setForm\(empty\);\s*dateInputRef/);
});

import test from "node:test";
import assert from "node:assert/strict";
import { buildReportShareSummary } from "../reportShareSummary.js";

test("buildReportShareSummary - formato completo com emojis", () => {
  const report = {
    operation_date: "2026-10-12",
    team: "Equipe Alpha",
    agenda_location: "Zona Sul",
    actions: [
      {
        institution_name: "Ação 1",
        type_action: "Bares",
        place_action: "Av. Brasil",
        start_time: "09:00:00",
        final_hour: "12:00:00",
        approached_actions: 50,
        distribution_materials_distributed: "Panfletos - 100\nBafômetros desc. - 50",
      },
      {
        institution_name: "Ação 2",
        type_action: "Pedágio",
        place_action: "Av. das Américas",
        start_time: "14:00:00",
        final_hour: "17:00:00",
        approached_actions: 75,
      }
    ],
    has_exceptional_occurrence: true,
    exceptional_occurrence_type: "VEHICLE_BREAKDOWN",
    exceptional_occurrence_description: "Pneu furado",
    exceptional_occurrence_actions_taken: "Troca do pneu",
    exceptional_occurrence_impact: "PARTIAL",
    general_observations: "Tudo certo no geral.",
  };

  const agenda = {
    action_type_ref_name: "Ação de rua"
  };

  const attendanceStats = { loaded: true, total: 4, present: 4, absent: 0 };

  const summary = buildReportShareSummary(report, agenda, attendanceStats);

  // Emojis
  assert.match(summary, /📅 Data: 12\/10\/2026/);
  assert.match(summary, /👥 Equipe: Equipe Alpha/);
  assert.match(summary, /📍 Local: Zona Sul/);
  assert.match(summary, /🎯 Modalidade: Ação de Rua/);
  assert.match(summary, /✅ Frequência: 4 presente\(s\), 0 ausente\(s\)/);

  // Ações
  assert.match(summary, /AÇÕES REALIZADAS/);
  assert.match(summary, /Ação 01 - Bares\/Restaurantes/);
  assert.match(summary, /📍 Av\. Brasil/);
  assert.match(summary, /🕒 Horário: 09:00 às 12:00/);
  assert.match(summary, /👥 Abordagens: 50/);
  assert.match(summary, /📦 Material distribuído: Panfletos: 100; Bafômetros desc.: 50/);

  assert.match(summary, /Ação 02 - Pedágio/);
  assert.match(summary, /📍 Av\. das Américas/);
  assert.match(summary, /🕒 Horário: 14:00 às 17:00/);
  assert.match(summary, /👥 Abordagens: 75/);
  
  // Ocorrência
  assert.match(summary, /OCORRÊNCIA EXCEPCIONAL/);
  assert.match(summary, /⚠️ Tipo: Quebra de Viatura/);
  assert.match(summary, /Descrição: Pneu furado/);
  assert.match(summary, /Providências: Troca do pneu/);
  assert.match(summary, /Impacto: Parcial/);

  // Observações
  assert.match(summary, /📝 Observações: Tudo certo no geral\./);
  
  // Confirma ausência de interface
  assert.doesNotMatch(summary, /div|span|button|html/);
});

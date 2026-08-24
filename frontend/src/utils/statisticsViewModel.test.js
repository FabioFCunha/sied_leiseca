import { buildStatisticsViewModel } from "./statisticsViewModel.js";
import { describe, it, expect } from "vitest";

describe("buildStatisticsViewModel", () => {
  it("should handle empty or null inputs without crashing", () => {
    const vm = buildStatisticsViewModel({
      dashboardData: null,
      filteredAgendas: null,
      futureAgendas: null,
    });

    expect(vm.demand.total).toBe(0);
    expect(vm.categoryData).toEqual([]);
    expect(vm.ageRows).toEqual([]);
    expect(vm.requesterRows).toEqual([]);
    expect(vm.heatmapRows).toEqual([]);
    expect(vm.municipalities).toEqual([]);
    expect(vm.teams).toEqual([]);
    expect(vm.annual).toEqual([]);
    expect(vm.dailySeries).toEqual([]);
  });

  it("should calculate production vs demand correctly", () => {
    const vm = buildStatisticsViewModel({
      dashboardData: { summary: { "ACTION - Geral": "10" } },
      filteredAgendas: [
        { origin: "PUBLIC_FORM", status: "APPROVED" },
        { origin: "INTERNAL", status: "COMPLETED" },
        { origin: "INTERNAL", status: "CANCELLED" },
        { origin: "PUBLIC_FORM", status: "REJECTED" },
      ],
      futureAgendas: [],
    });

    expect(vm.demand.total).toBe(4);
    expect(vm.demand.publicForm).toBe(2);
    expect(vm.demand.internal).toBe(2);
    expect(vm.demand.approved).toBe(2);
    expect(vm.demand.cancelled).toBe(1);
    expect(vm.demand.refused).toBe(1);
    expect(vm.demand.executed).toBe(10);
  });

  it("should extract formatting labels and separate from raw values", () => {
    const vm = buildStatisticsViewModel({
      dashboardData: {
        categories: [
          { label: "ACTION - Escola", value: "5", audience: "100" },
          { label: "ACTION - Bares", value: "5", audience: "200" },
        ],
      },
      filteredAgendas: [],
      futureAgendas: [],
    });

    expect(vm.categoryData.length).toBe(2);
    expect(vm.categoryData[0].actionsLabel).toBe("5");
    expect(vm.categoryData[0].percentageValue).toBe(50);
    expect(vm.categoryData[0].percentageLabel).toBe("50,0%");
  });

  it("should consolidate official and legacy age ranges in pedagogical order", () => {
      const vm = buildStatisticsViewModel({
          dashboardData: {},
          filteredAgendas: [
              { age_ranges: "05 - 10 anos (ensino fundamental - anos iniciais)", audience: "10" },
              { age_ranges: "5 - 10 anos", audience: "20" },
              // Historic 4–13 records are consolidated as the initial-years group.
              { age_ranges: "4 a 13", audience: "30" },
              { age_ranges: "4 até 13", audience: "40" },
              { age_ranges: "11 - 14 anos", audience: "50" },
              { age_ranges: "09 até 13 anos", audience: "60" },
              { age_ranges: "15 - 17 anos (ensino médio)", audience: "70" },
              { age_ranges: "14 até 17 anos", audience: "80" },
              { age_ranges: "acima de 18 anos - Adultos", audience: "90" },
              { age_ranges: "acima de 18 anos", audience: "100" },
              { age_ranges: "Adultos", audience: "110" },
          ],
          futureAgendas: [],
      });

      expect(vm.ageRows.map(row => row.label)).toEqual([
          "05 - 10 anos (ensino fundamental - anos iniciais)",
          "11 - 14 anos (ensino fundamental - anos finais)",
          "15 - 17 anos (ensino médio)",
          "acima de 18 anos - Adultos",
      ]);
      expect(vm.ageRows.map(row => row.actions)).toEqual([4, 2, 2, 3]);
      expect(vm.ageRows.map(row => row.audience)).toEqual([100, 110, 150, 300]);
      expect(vm.ageRows.map(row => row.percentageValue)).toEqual([
          (4 / 11) * 100,
          (2 / 11) * 100,
          (2 / 11) * 100,
          (3 / 11) * 100,
      ]);
  });
  
  it("should process administrative demands from dashboardData correctly", () => {
      const vm = buildStatisticsViewModel({
          dashboardData: {
              administrative_demands: {
                  items: [
                      { code: "TRAVEL", label: "Deslocamento de viagem", value: "5" },
                      { code: "MEETING", label: "Reunião", value: "3" },
                  ]
              }
          },
          filteredAgendas: [],
          futureAgendas: [],
      });
      
      expect(vm.administrativeDemandRows.length).toBe(3); // Travel, Interview, Meeting
      
      const travel = vm.administrativeDemandRows.find(r => r.label === "Deslocamento de viagem");
      expect(travel.actions).toBe(5);
      
      const meeting = vm.administrativeDemandRows.find(r => r.label === "Reunião");
      expect(meeting.actions).toBe(3);
      
      const interview = vm.administrativeDemandRows.find(r => r.label === "Entrevista");
      expect(interview.actions).toBe(0);
  });

  it("should expose educational agreements without breaking older payloads", () => {
      const withAgreements = buildStatisticsViewModel({
          dashboardData: {
              educational_agreements: {
                  items: [
                      { code: "ESCOLINHA_NOTA_10", label: "Escolinha Nota 10", actions: 2, audience: 70 },
                      { code: "ESCOLA_NOTA_10", label: "Escola Nota 10", actions: 1, audience: 50 },
                  ]
              }
          },
          filteredAgendas: [],
          futureAgendas: [],
      });
      expect(withAgreements.educationalAgreementRows).toHaveLength(2);
      expect(withAgreements.educationalAgreementRows[0].actionsLabel).toBeDefined();

      const withoutAgreements = buildStatisticsViewModel({
          dashboardData: {},
          filteredAgendas: [],
          futureAgendas: [],
      });
      expect(withoutAgreements.educationalAgreementRows).toEqual([]);
  });
  
  it("should format teams correctly", () => {
      const vm = buildStatisticsViewModel({
          dashboardData: {
              teams: [
                  { team: "Equipe B", actions: "5", audience: "100" },
                  { team: "Equipe A", actions: "10", audience: "200" },
              ]
          },
          filteredAgendas: [],
          futureAgendas: [],
      });
      
      expect(vm.teams.length).toBe(2);
      expect(vm.teams[0].team).toBe("Equipe A");
      expect(vm.teams[0].actionsLabel).toBe("10");
  });
});

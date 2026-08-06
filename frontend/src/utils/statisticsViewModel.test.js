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

  it("should calculate percentage properly for age rows", () => {
      const vm = buildStatisticsViewModel({
          dashboardData: {},
          filteredAgendas: [
              { age_ranges: "Criança", audience: "10" },
              { age_ranges: "Criança", audience: "20" },
              { age_ranges: "Idoso", audience: "30" },
          ],
          futureAgendas: [],
      });
      
      expect(vm.ageRows.length).toBe(2);
      
      const criancaRow = vm.ageRows.find(r => r.label === "Criança");
      expect(criancaRow.actions).toBe(2);
      expect(criancaRow.audience).toBe(30);
      
      const idosoRow = vm.ageRows.find(r => r.label === "Idoso");
      expect(idosoRow.actions).toBe(1);
      expect(idosoRow.audience).toBe(30);
      
      expect(criancaRow.percentageValue).toBeCloseTo(66.66, 1);
      expect(idosoRow.percentageValue).toBeCloseTo(33.33, 1);
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

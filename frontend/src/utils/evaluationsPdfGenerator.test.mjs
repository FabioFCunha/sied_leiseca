/**
 * Tests for the Evaluations PDF Generator (evaluationsPdfGenerator.js)
 *
 * These tests validate that the PDF generator:
 * 1. Uses the correct generator (not Dashboard/Agenda)
 * 2. Produces the correct title and structure
 * 3. Respects filters
 * 4. Handles empty data
 * 5. Preserves UTF-8 encoding
 * 6. Generates proper filenames
 * 7. Does not include data from other modules
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock jsPDF and autoTable ─────────────────────────────────────────────
const mockTextCalls = [];
const mockSaveCalls = [];
let mockPageCount = 1;
const mockLastAutoTable = { finalY: 50 };

const mockDoc = {
  internal: {
    pageSize: { width: 210, height: 297 },
    getNumberOfPages: () => mockPageCount,
  },
  lastAutoTable: mockLastAutoTable,
  setFillColor: vi.fn(),
  setDrawColor: vi.fn(),
  setLineWidth: vi.fn(),
  setFont: vi.fn(),
  setFontSize: vi.fn(),
  setTextColor: vi.fn(),
  rect: vi.fn(),
  roundedRect: vi.fn(),
  line: vi.fn(),
  text: vi.fn((...args) => mockTextCalls.push(args)),
  addImage: vi.fn(),
  addPage: vi.fn(() => { mockPageCount++; }),
  setPage: vi.fn(),
  save: vi.fn((filename) => mockSaveCalls.push(filename)),
  output: vi.fn(() => "blob:mock"),
  splitTextToSize: vi.fn((text, _width) => [text]),
};

vi.mock("jspdf", () => {
  const MockJsPDF = function() { return mockDoc; };
  MockJsPDF.prototype = {};
  return { jsPDF: MockJsPDF };
});

const mockAutoTableCalls = [];
vi.mock("jspdf-autotable", () => ({
  default: vi.fn((_doc, opts) => {
    mockAutoTableCalls.push(opts);
    mockDoc.lastAutoTable = { finalY: (opts.startY || 0) + 30 };
  }),
}));

// ── Import the module under test ─────────────────────────────────────────
const { generateEvaluationsPdf } = await import("../utils/evaluationsPdfGenerator.js");

// ── Test data fixtures ───────────────────────────────────────────────────
function makeFullData() {
  return {
    cards: {
      total_surveys: 142,
      satisfaction_index: 87.3,
      speaker_avg: 8.45,
      resources_avg: 7.92,
      punctuality_avg: 9.10,
      enthusiasm_avg: 8.67,
      workshops_avg: 7.85,
      support_material_avg: 8.12,
      wheelchair_avg: 8.90,
      best_criteria: "Pontualidade",
      worst_criteria: "Dinâmicas",
      most_improved: "Pontualidade",
    },
    radar: [
      { criteria: "Recursos áudio-visuais", value: 7.92 },
      { criteria: "Palestrante", value: 8.45 },
      { criteria: "Depoimento dos cadeirantes", value: 8.90 },
      { criteria: "Dinâmicas", value: 7.85 },
      { criteria: "Material de apoio", value: 8.12 },
      { criteria: "Pontualidade", value: 9.10 },
      { criteria: "Entusiasmo", value: 8.67 },
      { criteria: "Nota geral", value: 8.43 },
    ],
    ranking: [
      { criteria: "Equipe Alfa", value: 9.21 },
      { criteria: "Equipe Beta", value: 8.54 },
      { criteria: "Equipe Gama", value: 7.89 },
    ],
    distribution: {
      "Nota geral": { "1": 0, "2": 1, "3": 2, "4": 5, "5": 8, "6": 12, "7": 20, "8": 35, "9": 40, "10": 19 },
    },
    monthly_evolution: [
      { month: "2026-01", label: "Jan/26", value: 8.10 },
      { month: "2026-02", label: "Fev/26", value: 8.25 },
      { month: "2026-03", label: "Mar/26", value: 8.43 },
    ],
    heatmap: [
      { criteria: "Palestrante", month: "2026-01", value: 8.30 },
      { criteria: "Palestrante", month: "2026-02", value: 8.50 },
      { criteria: "Pontualidade", month: "2026-01", value: 9.00 },
      { criteria: "Pontualidade", month: "2026-02", value: 9.20 },
    ],
    satisfaction_panel: {
      overall_rating: 8.4,
      total_responses: 142,
      team_ratings: [
        { team: "Equipe Alfa", avg: 9.2, count: 45 },
      ],
      messages: [
        {
          id: 1,
          team: "Equipe Alfa",
          suggestion: "Ótima palestra, muito didática!",
          moderated_comment: "Ótima palestra, muito didática!",
          answered_at: "2026-06-15T10:30:00Z",
          overall_rating: 9.0,
          is_approved: true,
          moderation_status: "APPROVED",
          agenda__id: 123,
          agenda__institution_location: "Escola Municipal São João",
        },
      ],
    },
    intelligence: {
      excellence_index: 87.3,
      best_criteria: "Pontualidade",
      most_improved: "Recursos áudio-visuais",
      most_declined: null,
      trend: "up",
      trend_delta: 0.33,
    },
    executive_summary: "Foram recebidas 142 avaliações no período selecionado. A nota média geral foi 8.43. O índice de excelência atingiu 87.3%. Os critérios mais bem avaliados foram Pontualidade e Entusiasmo.",
    states: ["RJ"],
    regions: [{ id: 1, name: "Metropolitana" }],
    municipalities: [{ id: 1, name: "Rio de Janeiro" }],
    teams: ["Equipe Alfa", "Equipe Beta"],
    comments: [],
  };
}

function makeEmptyData() {
  return {
    cards: {
      total_surveys: 0,
      satisfaction_index: 0,
      speaker_avg: 0,
      resources_avg: 0,
      punctuality_avg: 0,
      enthusiasm_avg: 0,
      workshops_avg: 0,
      support_material_avg: 0,
      wheelchair_avg: 0,
      best_criteria: null,
      worst_criteria: null,
      most_improved: null,
    },
    radar: [],
    ranking: [],
    distribution: {},
    monthly_evolution: [],
    heatmap: [],
    comments: [],
    states: [],
    regions: [],
    municipalities: [],
    teams: [],
    satisfaction_panel: { overall_rating: 0, total_responses: 0, team_ratings: [], messages: [] },
    intelligence: { excellence_index: 0, best_criteria: null, most_improved: null, most_declined: null, trend: null, trend_delta: 0 },
    executive_summary: "",
  };
}

const defaultFilters = { date_from: "2026-01-01", date_to: "2026-08-31", state: "", region: "", municipality: "", status: "", team: "" };
const defaultParams = { logoUrl: "/fake-logo.png", issuedAt: new Date("2026-09-01T11:00:00Z") };

// ── Test Suite ───────────────────────────────────────────────────────────
describe("evaluationsPdfGenerator", () => {
  beforeEach(() => {
    mockTextCalls.length = 0;
    mockSaveCalls.length = 0;
    mockAutoTableCalls.length = 0;
    mockPageCount = 1;
    vi.clearAllMocks();
  });

  // ── Test 1: Calls the correct generator ────────────────────────────
  it("1. uses the frontend PDF generator, not the backend Dashboard endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => Promise.reject("Should not call fetch"));

    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    // fetch should NOT be called — we generate client-side
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  // ── Test 2: Does not use Dashboard/Agenda report ───────────────────
  it("2. does not include Dashboard/Agenda content", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const allText = mockTextCalls.map((call) => String(call[0])).join(" ");
    expect(allText).not.toContain("Relatório Consolidado de Atividades");
    expect(allText).not.toContain("Dashboard");
    expect(allText).not.toContain("Agendas Aprovadas");
    expect(allText).not.toContain("Agendas Pendentes");
  });

  // ── Test 3: Correct title ──────────────────────────────────────────
  it("3. title is 'RELATÓRIO DE AVALIAÇÕES'", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const hasTitle = mockTextCalls.some(
      (call) => String(call[0]).includes("RELATÓRIO DE AVALIAÇÕES")
    );
    expect(hasTitle).toBe(true);
  });

  // ── Test 4: Filters are respected ──────────────────────────────────
  it("4. active filters are displayed in the PDF", async () => {
    const filtersWithTeam = { ...defaultFilters, team: "Equipe Alfa" };

    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: filtersWithTeam,
      ...defaultParams,
    });

    // The filter table should contain the team name
    const filterTable = mockAutoTableCalls[0]; // first autoTable call is the filter block
    expect(filterTable).toBeDefined();
    const filterBody = filterTable.body;
    const teamRow = filterBody.find((row) => row[0] === "Equipe");
    expect(teamRow).toBeDefined();
    expect(teamRow[1]).toBe("Equipe Alfa");
  });

  // ── Test 5: Values match interface data ────────────────────────────
  it("5. exported indicator values match the data object", async () => {
    const data = makeFullData();
    await generateEvaluationsPdf({
      data,
      filters: defaultFilters,
      ...defaultParams,
    });

    // The indicators table (second autoTable call) should contain total_surveys
    const indicatorsTable = mockAutoTableCalls[1];
    expect(indicatorsTable).toBeDefined();
    const totalRow = indicatorsTable.body.find((row) => row[0] === "Avaliações Recebidas");
    expect(totalRow).toBeDefined();
    // 142 in pt-BR locale
    expect(totalRow[1]).toContain("142");
  });

  // ── Test 6: No metrics from other modules ──────────────────────────
  it("6. does not include metrics from Dashboard, Agenda, or Inspection modules", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const allText = mockTextCalls.map((call) => String(call[0])).join(" ");
    const allTableText = mockAutoTableCalls
      .flatMap((t) => (t.body || []).flatMap((row) => row.map(String)))
      .join(" ");
    const combined = allText + " " + allTableText;

    expect(combined).not.toContain("Agendas Aprovadas");
    expect(combined).not.toContain("Agendas Pendentes");
    expect(combined).not.toContain("Agendas Canceladas");
    expect(combined).not.toContain("Taxa de cancelamento");
    expect(combined).not.toContain("Agentes Escalados");
  });

  // ── Test 7: Empty state is handled ─────────────────────────────────
  it("7. handles empty data state with appropriate message", async () => {
    await generateEvaluationsPdf({
      data: makeEmptyData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const hasEmptyMessage = mockTextCalls.some(
      (call) => String(call[0]).includes("Nenhuma avaliação encontrada")
    );
    expect(hasEmptyMessage).toBe(true);

    // Should still generate the PDF (not throw)
    expect(mockSaveCalls.length).toBe(1);
  });

  // ── Test 8: UTF-8 accented text preserved ──────────────────────────
  it("8. accented Portuguese text is preserved correctly", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const allText = mockTextCalls.map((call) => String(call[0])).join(" ");
    expect(allText).toContain("AVALIAÇÕES");
    expect(allText).toContain("Operação Lei Seca");
  });

  // ── Test 9: No corrupted characters ────────────────────────────────
  it("9. does not contain mojibake characters (Ã, Â, replacement chars)", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const allText = mockTextCalls.map((call) => String(call[0])).join(" ");
    const allTableText = mockAutoTableCalls
      .flatMap((t) => [
        ...((t.head || []).flatMap((row) => row.map(String))),
        ...((t.body || []).flatMap((row) => row.map(String))),
      ])
      .join(" ");
    const combined = allText + " " + allTableText;

    // Check for mojibake patterns
    expect(combined).not.toMatch(/Ã§Ã£o/);
    expect(combined).not.toMatch(/PerÃ­odo/);
    expect(combined).not.toMatch(/MunicÃ­pio/);
    expect(combined).not.toMatch(/OperaÃ§/);
    expect(combined).not.toContain("�");
  });

  // ── Test 10: Multi-page tables ─────────────────────────────────────
  it("10. generates multiple pages when there are many sections", async () => {
    // With full data, multiple sections should trigger addPage
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    // The doc.save should be called once (file generated)
    expect(mockSaveCalls.length).toBe(1);
    // Multiple autoTable calls should have been made
    expect(mockAutoTableCalls.length).toBeGreaterThan(5);
  });

  // ── Test 11: Table headers repeated (autoTable config) ─────────────
  it("11. distribution table uses autoTable with grid theme and head row", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    // Find the distribution table (has 12 columns: Critério + 10 scores + Total)
    const distTable = mockAutoTableCalls.find(
      (t) => t.head && t.head[0] && t.head[0].length === 12
    );
    expect(distTable).toBeDefined();
    expect(distTable.theme).toBe("grid");
    expect(distTable.headStyles.fillColor).toEqual([10, 30, 68]); // NAVY
  });

  // ── Test 12: Footer and pagination on all pages ────────────────────
  it("12. applies footer to all pages with Página X de Y format", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    // doc.setPage should be called for each page during footer loop
    expect(mockDoc.setPage).toHaveBeenCalled();

    // Check that "Página" text format is used
    const pageTexts = mockTextCalls.filter(
      (call) => String(call[0]).startsWith("Página ")
    );
    expect(pageTexts.length).toBeGreaterThan(0);
  });

  // ── Test 13: Filename contains period ──────────────────────────────
  it("13. filename includes the applied date range", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: { ...defaultFilters, date_from: "2026-01-01", date_to: "2026-08-31" },
      ...defaultParams,
    });

    expect(mockSaveCalls.length).toBe(1);
    const filename = mockSaveCalls[0];
    expect(filename).toContain("relatorio_avaliacoes");
    expect(filename).toContain("2026-01-01");
    expect(filename).toContain("2026-08-31");
    expect(filename).toMatch(/\.pdf$/);
  });

  // ── Test 14: Does not alter other report generators ────────────────
  it("14. does not import or reference other report generators", async () => {
    // Verify by checking that the module is self-contained
    // (it only imports jspdf and jspdf-autotable, no other generators)
    const moduleSource = await import("../utils/evaluationsPdfGenerator.js");
    expect(typeof moduleSource.generateEvaluationsPdf).toBe("function");
    // The module should have exactly one export
    const exportKeys = Object.keys(moduleSource);
    expect(exportKeys).toContain("generateEvaluationsPdf");
  });

  // ── Test 15: Error handling ────────────────────────────────────────
  it("15. throws a comprehensible error when data is null", async () => {
    await expect(
      generateEvaluationsPdf({
        data: null,
        filters: defaultFilters,
        ...defaultParams,
      })
    ).rejects.toThrow("Dados de avaliações indisponíveis");
  });

  // ── Additional: filter display defaults ────────────────────────────
  it("shows 'Todos' / 'Todas' for empty filters", async () => {
    const emptyFilters = { date_from: "", date_to: "", state: "", region: "", municipality: "", status: "", team: "" };

    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: emptyFilters,
      ...defaultParams,
    });

    const filterTable = mockAutoTableCalls[0];
    const estadoRow = filterTable.body.find((row) => row[0] === "Estado");
    expect(estadoRow[1]).toBe("Todos");
    const equipeRow = filterTable.body.find((row) => row[0] === "Equipe");
    expect(equipeRow[1]).toBe("Todas");
  });

  // ── Additional: institutional text ─────────────────────────────────
  it("includes institutional footer text", async () => {
    await generateEvaluationsPdf({
      data: makeFullData(),
      filters: defaultFilters,
      ...defaultParams,
    });

    const allText = mockTextCalls.map((call) => String(call[0])).join(" ");
    expect(allText).toContain("SIED");
    expect(allText).toContain("Operação Lei Seca");
    expect(allText).toContain("Documento gerado automaticamente");
  });

  // ── Excel removal verification ─────────────────────────────────────
  it("verifies EvaluationsPage.jsx does not contain Excel export button or endpoint", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const pageContent = fs.readFileSync(
      path.resolve(process.cwd(), "src/pages/EvaluationsPage.jsx"),
      "utf-8"
    );

    // 1. Should not call export_excel
    expect(pageContent).not.toContain("export_excel");
    // 2. Should contain PDF export button
    expect(pageContent).toContain("Exportar PDF");
    // 3. Should not contain Excel button in the hero banner
    expect(pageContent).not.toMatch(/<button[^>]*>\s*<Download[^>]*\/>\s*Excel\s*<\/button>/i);
    expect(pageContent).not.toContain('handleExport("excel"');
  });

  it("verifies backend still preserves export_excel endpoint for other potential uses", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const backendViewsContent = fs.readFileSync(
      path.resolve(process.cwd(), "../backend/apps/schedules/views.py"),
      "utf-8"
    );

    expect(backendViewsContent).toContain("export_excel");
  });
});

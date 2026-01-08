/**
 * Tests for handlers/planner.ts
 * Weekly planner operations (ids, dates, metrics, plans)
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  plannerIdsList,
  plannerDatesGet,
  plannerDatesSet,
  plannerMetricsGet,
  plannerPlanGet,
  plannerPlanSet,
} from "../planner";
import {
  resetAllMocks,
  mockSpreadsheetApp,
} from "../../__mocks__/gas-stubs";

// Helper to create a mock planner sheet with customizable data
function createPlannerMock(options: {
  abcd?: any[][];  // A4:D30 data (27 rows)
  weekStarts?: string[];  // D1, L1, T1, AB1, AJ1
  metrics?: any[][];  // Metrics data per week (E/F/G, M/N/O, etc.)
  plans?: string[][];  // Plan data per week (H, P, X, AF, AN columns)
} = {}) {
  const {
    abcd = [],
    weekStarts = ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25", ""],
    metrics = [],
    plans = [],
  } = options;

  // Create range mock that returns appropriate data based on A1 notation
  const createRangeMock = (a1: string) => {
    const cellMatch = a1.match(/^([A-Z]+)(\d+)$/);
    const rangeMatch = a1.match(/^([A-Z]+)(\d+):([A-Z]+)(\d+)$/);

    // Week start addresses
    if (["D1", "L1", "T1", "AB1", "AJ1"].includes(a1)) {
      const idx = ["D1", "L1", "T1", "AB1", "AJ1"].indexOf(a1);
      return {
        getDisplayValue: vi.fn(() => weekStarts[idx] || ""),
        getValue: vi.fn(() => weekStarts[idx] || ""),
        setValue: vi.fn(),
      };
    }

    // A4:D30 range (ABCD data)
    if (a1 === "A4:D30" || (rangeMatch && rangeMatch[1] === "A" && rangeMatch[3] === "D")) {
      return {
        getDisplayValues: vi.fn(() => {
          // Pad with empty rows to make 27 rows
          const padded = [...abcd];
          while (padded.length < 27) {
            padded.push(["", "", "", ""]);
          }
          return padded;
        }),
      };
    }

    // Plan columns (H, P, X, AF, AN) with row ranges
    const planCols = ["H", "P", "X", "AF", "AN"];
    for (let i = 0; i < planCols.length; i++) {
      const col = planCols[i];
      if (a1.startsWith(`${col}4:${col}`)) {
        return {
          getDisplayValues: vi.fn(() => {
            const weekPlans = plans[i] || [];
            return Array(27).fill(0).map((_, j) => [weekPlans[j] || ""]);
          }),
          setValues: vi.fn(),
        };
      }
    }

    // Metrics ranges (E4:G30, M4:O30, etc.)
    const metricRanges = ["E4:G30", "M4:O30", "U4:W30", "AC4:AE30", "AK4:AM30"];
    for (let i = 0; i < metricRanges.length; i++) {
      if (a1 === metricRanges[i] || a1.match(new RegExp(`^[EMUAC]4:[GOAK][EM]?30$`))) {
        return {
          getDisplayValues: vi.fn(() => {
            const weekMetrics = metrics[i] || [];
            return Array(27).fill(0).map((_, j) => weekMetrics[j] || ["", "", ""]);
          }),
        };
      }
    }

    // Individual cell access (for single row/col)
    if (cellMatch) {
      const col = cellMatch[1];
      const row = parseInt(cellMatch[2]);

      // Plan column single cell
      const planIdx = planCols.indexOf(col);
      if (planIdx >= 0 && row >= 4 && row <= 30) {
        const weekPlans = plans[planIdx] || [];
        return {
          getDisplayValue: vi.fn(() => weekPlans[row - 4] || ""),
          getValue: vi.fn(() => weekPlans[row - 4] || ""),
          setValue: vi.fn(),
          setValues: vi.fn(),
        };
      }

      // A column (for row check)
      if (col === "A" && row >= 4) {
        const rowData = abcd[row - 4] || ["", "", "", ""];
        return {
          getDisplayValue: vi.fn(() => rowData[0] || ""),
          getValue: vi.fn(() => rowData[0] || ""),
        };
      }

      // Time columns (E, M, U, AC, AK)
      const timeCols = ["E", "M", "U", "AC", "AK"];
      const timeIdx = timeCols.indexOf(col);
      if (timeIdx >= 0 && row >= 4 && row <= 30) {
        const weekMetrics = metrics[timeIdx] || [];
        const rowMetrics = weekMetrics[row - 4] || ["", "", ""];
        return {
          getDisplayValue: vi.fn(() => rowMetrics[0] || ""),
          getValue: vi.fn(() => rowMetrics[0] || ""),
        };
      }
    }

    // Default mock
    return {
      getDisplayValue: vi.fn(() => ""),
      getDisplayValues: vi.fn(() => []),
      getValue: vi.fn(() => ""),
      setValue: vi.fn(),
      setValues: vi.fn(),
    };
  };

  const mockSheet = {
    getName: vi.fn(() => "週間管理"),
    getMaxRows: vi.fn(() => 30),
    getLastRow: vi.fn(() => 30),
    getRange: vi.fn((a1OrRow: string | number, col?: number, numRows?: number, numCols?: number) => {
      if (typeof a1OrRow === "string") {
        return createRangeMock(a1OrRow);
      }
      // Row/col numeric access
      const row = a1OrRow;

      // Handle A4:D30 style access (4, 1, 27, 4)
      if (row === 4 && col === 1 && numRows === 27 && numCols === 4) {
        // A4:D30 - return ABCD data
        const padded = [...abcd];
        while (padded.length < 27) {
          padded.push(["", "", "", ""]);
        }
        return {
          getDisplayValues: vi.fn(() => padded),
          getValues: vi.fn(() => padded),
        };
      }

      if (col === 1) {
        // A column single cell
        const rowData = abcd[row - 4] || ["", "", "", ""];
        return {
          getDisplayValue: vi.fn(() => rowData[0] || ""),
          getValue: vi.fn(() => rowData[0] || ""),
        };
      }
      // Default
      return {
        getDisplayValue: vi.fn(() => ""),
        getValue: vi.fn(() => ""),
        setValue: vi.fn(),
        getDisplayValues: vi.fn(() => []),
      };
    }),
  };

  mockSpreadsheetApp.openById.mockReturnValue({
    getSheetByName: vi.fn((name: string) => {
      if (name === "週間管理" || name === "週間計画") return mockSheet;
      return null;
    }),
    getSheets: vi.fn(() => [mockSheet]),
  } as any);
}

// Sample ABCD data for testing
const SAMPLE_ABCD = [
  ["258gM001", "数学", "青チャートIA", "20問/週"],
  ["258gE001", "英語", "英文法・語法", "10問/週"],
  ["259gP001", "物理", "物理のエッセンス", "5問/週"],
];

// Sample metrics data (per week, each row has [time, unit, guide])
const SAMPLE_METRICS = [
  [["120", "2", "80"], ["60", "1", "40"], ["90", "3", "20"]],  // Week 1
  [["120", "2", "80"], ["60", "1", "40"], ["90", "3", "20"]],  // Week 2
  [["120", "2", "80"], ["60", "1", "40"], ["90", "3", "20"]],  // Week 3
  [["120", "2", "80"], ["60", "1", "40"], ["90", "3", "20"]],  // Week 4
  [["", "", ""], ["", "", ""], ["", "", ""]],  // Week 5 (empty)
];

// Sample plans data (per week, one value per row)
const SAMPLE_PLANS = [
  ["1-20", "1-10", "1-5"],  // Week 1
  ["21-40", "11-20", ""],   // Week 2
  ["", "", ""],             // Week 3
  ["", "", ""],             // Week 4
  ["", "", ""],             // Week 5
];

describe("planner handlers", () => {
  beforeEach(() => {
    resetAllMocks();
    createPlannerMock({
      abcd: SAMPLE_ABCD,
      metrics: SAMPLE_METRICS,
      plans: SAMPLE_PLANS,
    });
  });

  describe("plannerIdsList", () => {
    it("should return list of book IDs from A4:D30", () => {
      const result = plannerIdsList({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(true);
      expect(result.data.items.length).toBe(3);
      expect(result.data.count).toBe(3);
    });

    it("should parse book code correctly", () => {
      const result = plannerIdsList({ spreadsheet_id: "test-id" });
      const item = result.data.items[0];
      expect(item.row).toBe(4);
      expect(item.raw_code).toBe("258gM001");
      expect(item.month_code).toBe(258);
      expect(item.book_id).toBe("gM001");
      expect(item.subject).toBe("数学");
      expect(item.title).toBe("青チャートIA");
      expect(item.guideline_note).toBe("20問/週");
    });

    it("should stop at first empty A cell", () => {
      createPlannerMock({
        abcd: [
          ["258gM001", "数学", "青チャートIA", "20問/週"],
          ["", "", "", ""],  // Empty A stops processing
          ["259gP001", "物理", "物理のエッセンス", "5問/週"],
        ],
      });
      const result = plannerIdsList({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(true);
      expect(result.data.items.length).toBe(1);
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerIdsList({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when no spreadsheet_id", () => {
      const result = plannerIdsList({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("plannerDatesGet", () => {
    it("should return week start dates", () => {
      const result = plannerDatesGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(true);
      expect(result.data.week_starts).toHaveLength(5);
      expect(result.data.week_starts[0]).toBe("2025-08-04");
      expect(result.data.week_starts[4]).toBe("");
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerDatesGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("plannerDatesSet", () => {
    it("should set start date to D1", () => {
      const result = plannerDatesSet({ spreadsheet_id: "test-id", start_date: "2025-09-01" });
      expect(result.ok).toBe(true);
      expect(result.data.updated).toBe(true);
    });

    it("should return error when start_date is missing", () => {
      const result = plannerDatesSet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when start_date is invalid", () => {
      const result = plannerDatesSet({ spreadsheet_id: "test-id", start_date: "invalid" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_DATE");
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerDatesSet({ spreadsheet_id: "test-id", start_date: "2025-09-01" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("plannerMetricsGet", () => {
    it("should return metrics for all 5 weeks", () => {
      const result = plannerMetricsGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(true);
      expect(result.data.weeks).toHaveLength(5);
    });

    it("should include week index and column info", () => {
      const result = plannerMetricsGet({ spreadsheet_id: "test-id" });
      const week1 = result.data.weeks[0];
      expect(week1.week_index).toBe(1);
      expect(week1.column_time).toBe("E");
      expect(week1.column_unit).toBe("F");
      expect(week1.column_guide).toBe("G");
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerMetricsGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("plannerPlanGet", () => {
    it("should return plans for all 5 weeks", () => {
      const result = plannerPlanGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(true);
      expect(result.data.weeks).toHaveLength(5);
    });

    it("should include plan text for each row", () => {
      const result = plannerPlanGet({ spreadsheet_id: "test-id" });
      const week1 = result.data.weeks[0];
      expect(week1.week_index).toBe(1);
      expect(week1.column).toBe("H");
      expect(week1.items[0].row).toBe(4);
      expect(week1.items[0].plan_text).toBe("1-20");
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerPlanGet({ spreadsheet_id: "test-id" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("plannerPlanSet", () => {
    describe("single mode", () => {
      it("should return error when week_index is missing", () => {
        const result = plannerPlanSet({ spreadsheet_id: "test-id", row: 4, plan_text: "test" });
        expect(result.ok).toBe(false);
        expect(result.error?.code).toBe("BAD_REQUEST");
      });

      it("should return error when week_index is out of range", () => {
        const result = plannerPlanSet({ spreadsheet_id: "test-id", week_index: 6, row: 4, plan_text: "test" });
        expect(result.ok).toBe(false);
        expect(result.error?.code).toBe("BAD_REQUEST");
      });

      it("should return error when plan_text is too long", () => {
        const longText = "a".repeat(53);
        const result = plannerPlanSet({ spreadsheet_id: "test-id", week_index: 1, row: 4, plan_text: longText });
        expect(result.ok).toBe(false);
        expect(result.error?.code).toBe("TOO_LONG");
      });

      it("should return error when row not found", () => {
        const result = plannerPlanSet({ spreadsheet_id: "test-id", week_index: 1, plan_text: "test" });
        expect(result.ok).toBe(false);
        expect(result.error?.code).toBe("ROW_NOT_FOUND");
      });
    });

    describe("batch mode", () => {
      it("should accept items array", () => {
        const result = plannerPlanSet({
          spreadsheet_id: "test-id",
          items: [
            { week_index: 3, row: 4, plan_text: "41-60" },
            { week_index: 3, row: 5, plan_text: "21-30" },
          ],
        });
        expect(result.ok).toBe(true);
        expect(result.data.results.length).toBe(2);
      });

      it("should report errors for invalid items", () => {
        const result = plannerPlanSet({
          spreadsheet_id: "test-id",
          items: [
            { week_index: 6, row: 4, plan_text: "test" },  // Invalid week
            { week_index: 1, row: 4, plan_text: "a".repeat(53) },  // Too long
          ],
        });
        expect(result.ok).toBe(true);
        expect(result.data.results[0].ok).toBe(false);
        expect(result.data.results[0].error.code).toBe("BAD_WEEK");
        expect(result.data.results[1].ok).toBe(false);
        expect(result.data.results[1].error.code).toBe("TOO_LONG");
      });
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = plannerPlanSet({ spreadsheet_id: "test-id", week_index: 1, row: 4, plan_text: "test" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });
});

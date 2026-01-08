/**
 * Tests for handlers/planner_monthly.ts
 * Monthly planner filter operations
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { plannerMonthlyFilter } from "../planner_monthly";
import {
  resetAllMocks,
  mockSpreadsheetApp,
  createMockSheet,
  createMockSpreadsheet,
} from "../../__mocks__/gas-stubs";

// Sample monthly planner data (columns A-R, 18 columns)
// A: raw_code, B: year, C: month, D-F: (unused), G: book_id, H: subject, I: title, J: guideline_note
// K: unit_load, L: monthly_minutes, M: guideline_amount, N-R: weeks (5 weeks)
const MONTHLY_HEADERS = ["コード", "年", "月", "D", "E", "F", "参考書ID", "教科", "参考書名", "目安", "負荷", "時間", "目標", "週1", "週2", "週3", "週4", "週5"];

const MONTHLY_DATA = [
  MONTHLY_HEADERS,
  ["gM001", "25", "8", "", "", "", "gM001", "数学", "青チャートIA", "20問/週", "2", "120", "80", "1-20", "21-40", "41-60", "", ""],
  ["gM002", "25", "8", "", "", "", "gE001", "英語", "英文法・語法", "10問/週", "1", "60", "40", "1-10", "11-20", "", "", ""],
  ["gP001", "25", "9", "", "", "", "gP001", "物理", "物理のエッセンス", "5問/週", "3", "90", "20", "1-5", "", "", "", ""],
  ["gM003", "24", "12", "", "", "", "gM003", "数学", "Focus Gold", "15問/週", "2", "150", "60", "1-15", "16-30", "31-45", "46-60", ""],
];

function createMonthlyMock(data: any[][] = MONTHLY_DATA) {
  // Create a custom mock sheet that returns display values correctly
  const mockSheet = {
    getName: vi.fn(() => "月間管理"),
    getLastRow: vi.fn(() => data.length),
    getLastColumn: vi.fn(() => 18),
    getDataRange: vi.fn(() => ({
      getValues: vi.fn(() => data),
      getDisplayValues: vi.fn(() => data.map(row => row.map(String))),
    })),
    getRange: vi.fn((row: number, col: number, numRows?: number, numCols?: number) => ({
      getValues: vi.fn(() => {
        const sliced = data.slice(row - 1, row - 1 + (numRows || 1));
        return sliced.map(r => r.slice(col - 1, col - 1 + (numCols || 1)));
      }),
      getDisplayValues: vi.fn(() => {
        const sliced = data.slice(row - 1, row - 1 + (numRows || 1));
        return sliced.map(r => r.slice(col - 1, col - 1 + (numCols || 1)).map(String));
      }),
    })),
  };

  mockSpreadsheetApp.openById.mockReturnValue({
    getSheetByName: vi.fn((name: string) => {
      if (name === "月間管理") return mockSheet;
      return null;
    }),
    getSheets: vi.fn(() => [mockSheet]),
  } as any);
}

describe("plannerMonthlyFilter", () => {
  beforeEach(() => {
    resetAllMocks();
    createMonthlyMock();
  });

  describe("parameter validation", () => {
    it("should return error when year is missing", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", month: 8 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when month is missing", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when month is out of range", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 13 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when month is 0", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 0 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when year is invalid", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: "abc", month: 8 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });
  });

  describe("year normalization", () => {
    it("should accept 2-digit year", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(true);
      expect(result.data.year).toBe(25);
    });

    it("should convert 4-digit year to 2-digit", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 2025, month: 8 });
      expect(result.ok).toBe(true);
      expect(result.data.year).toBe(25);
    });

    it("should accept string year", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: "25", month: 8 });
      expect(result.ok).toBe(true);
      expect(result.data.year).toBe(25);
    });
  });

  describe("filtering", () => {
    it("should filter by year and month", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(true);
      expect(result.data.items.length).toBe(2);
      expect(result.data.count).toBe(2);
    });

    it("should return items for year 25 month 9", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 9 });
      expect(result.ok).toBe(true);
      expect(result.data.items.length).toBe(1);
      expect(result.data.items[0].subject).toBe("物理");
    });

    it("should return items for year 24 month 12", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 24, month: 12 });
      expect(result.ok).toBe(true);
      expect(result.data.items.length).toBe(1);
      expect(result.data.items[0].title).toBe("Focus Gold");
    });

    it("should return empty when no matches", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 1 });
      expect(result.ok).toBe(true);
      expect(result.data.items).toEqual([]);
      expect(result.data.count).toBe(0);
    });
  });

  describe("item structure", () => {
    it("should return correct item properties", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(true);

      const item = result.data.items[0];
      expect(item.row).toBe(2); // First data row
      expect(item.raw_code).toBe("gM001");
      expect(item.year).toBe(25);
      expect(item.month).toBe(8);
      expect(item.book_id).toBe("gM001");
      expect(item.subject).toBe("数学");
      expect(item.title).toBe("青チャートIA");
      expect(item.guideline_note).toBe("20問/週");
      expect(item.unit_load).toBe(2);
      expect(item.monthly_minutes).toBe(120);
      expect(item.guideline_amount).toBe(80);
    });

    it("should return week data", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(true);

      const item = result.data.items[0];
      expect(item.weeks).toHaveLength(5);
      expect(item.weeks[0]).toEqual({ index: 1, actual: "1-20" });
      expect(item.weeks[1]).toEqual({ index: 2, actual: "21-40" });
      expect(item.weeks[2]).toEqual({ index: 3, actual: "41-60" });
      expect(item.weeks[3]).toEqual({ index: 4, actual: "" });
      expect(item.weeks[4]).toEqual({ index: 5, actual: "" });
    });

    it("should calculate month_code correctly", () => {
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      const item = result.data.items[0];
      expect(item.month_code).toBe(258); // 25 * 10 + 8
    });
  });

  describe("sheet resolution", () => {
    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);

      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when no spreadsheet_id provided and no student_id", () => {
      const result = plannerMonthlyFilter({ year: 25, month: 8 });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should handle empty sheet", () => {
      createMonthlyMock([MONTHLY_HEADERS]);
      const result = plannerMonthlyFilter({ spreadsheet_id: "test-id", year: 25, month: 8 });
      expect(result.ok).toBe(true);
      expect(result.data.items).toEqual([]);
      expect(result.data.count).toBe(0);
    });
  });
});

/**
 * Tests for handlers/books.ts
 * Book master CRUD operations (find, get, filter, create, update, delete)
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  booksFind,
  booksGet,
  booksFilter,
  booksCreate,
  booksUpdate,
  booksDelete,
} from "../books";
import {
  resetAllMocks,
  mockSpreadsheetApp,
  mockCache,
} from "../../__mocks__/gas-stubs";

// Sample book master data for testing
const SAMPLE_HEADERS = [
  "参考書ID", "参考書名", "教科", "月間目標", "単位当たり処理量",
  "章立て", "章の名前", "章のはじめ", "章の終わり", "番号の数え方",
  "参考書のタイプ", "確認テストのタイプ", "確認テストID", "別名"
];

const SAMPLE_DATA = [
  SAMPLE_HEADERS,
  // Book 1: 青チャートIA (3 chapters)
  ["gM001", "青チャート数学IA", "数学", "2時間/日", "2", "1", "第1章 数と式", "1", "50", "問", "基礎", "選択", "qM001", "青チャ,1A"],
  ["", "", "", "", "", "2", "第2章 2次関数", "51", "100", "問", "", "", "", ""],
  ["", "", "", "", "", "3", "第3章 図形と計量", "101", "150", "問", "", "", "", ""],
  // Book 2: 英文法・語法 (2 chapters)
  ["gE001", "英文法・語法1000", "英語", "1.5時間/日", "1", "1", "文法編", "1", "500", "問", "演習", "全問", "qE001", "英文法"],
  ["", "", "", "", "", "2", "語法編", "501", "1000", "問", "", "", "", ""],
  // Book 3: 物理のエッセンス (no chapters)
  ["gP001", "物理のエッセンス", "物理", "1時間/日", "3", "", "", "", "", "", "基礎", "", "", "エッセンス"],
];

// Helper to create mock with custom data
function createBooksMock(data: any[][] = SAMPLE_DATA) {
  const mockSheet = {
    getName: vi.fn(() => "参考書マスター"),
    getLastRow: vi.fn(() => data.length),
    getLastColumn: vi.fn(() => data[0]?.length || 0),
    getDataRange: vi.fn(() => ({
      getValues: vi.fn(() => [...data]),
      getDisplayValues: vi.fn(() => data.map(row => row.map(String))),
    })),
    getRange: vi.fn((row: number, col: number, numRows?: number, numCols?: number) => ({
      getValues: vi.fn(() => {
        const r = row - 1;
        const c = col - 1;
        const h = numRows || 1;
        const w = numCols || 1;
        return data.slice(r, r + h).map(row => row.slice(c, c + w));
      }),
      getValue: vi.fn(() => data[row - 1]?.[col - 1] || ""),
      getDisplayValue: vi.fn(() => String(data[row - 1]?.[col - 1] || "")),
      setValue: vi.fn(),
      setValues: vi.fn(),
    })),
    insertRowsAfter: vi.fn(),
    deleteRow: vi.fn(),
    deleteRows: vi.fn(),
  };

  mockSpreadsheetApp.openById.mockReturnValue({
    getSheetByName: vi.fn((name: string) => {
      if (name === "参考書マスター") return mockSheet;
      return null;
    }),
    getSheets: vi.fn(() => [mockSheet]),
  } as any);

  return mockSheet;
}

describe("books handlers", () => {
  beforeEach(() => {
    resetAllMocks();
    createBooksMock();
  });

  describe("booksFind", () => {
    it("should find book by exact title match", () => {
      const result = booksFind({ query: "青チャート数学IA" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeGreaterThan(0);
      expect(result.data.top.book_id).toBe("gM001");
      expect(result.data.confidence).toBeGreaterThan(0);
    });

    it("should find book by partial title match", () => {
      const result = booksFind({ query: "青チャート" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeGreaterThan(0);
      expect(result.data.top.book_id).toBe("gM001");
    });

    it("should find book by alias", () => {
      const result = booksFind({ query: "エッセンス" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeGreaterThan(0);
      expect(result.data.top.book_id).toBe("gP001");
    });

    it("should find book by subject", () => {
      const result = booksFind({ query: "物理" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.some((c: any) => c.subject === "物理")).toBe(true);
    });

    it("should return error when query is missing", () => {
      const result = booksFind({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should limit results", () => {
      const result = booksFind({ query: "g", limit: 2 });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeLessThanOrEqual(2);
    });

    it("should handle no matches gracefully", () => {
      const result = booksFind({ query: "存在しない本" });
      expect(result.ok).toBe(true);
      expect(result.data.top).toBeNull();
      expect(result.data.confidence).toBe(0);
    });

    it("should return error when sheet not found", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = booksFind({ query: "test" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("booksGet", () => {
    it("should get single book by ID with chapters", () => {
      const result = booksGet({ book_id: "gM001" });
      expect(result.ok).toBe(true);
      expect(result.data.book.id).toBe("gM001");
      expect(result.data.book.title).toBe("青チャート数学IA");
      expect(result.data.book.subject).toBe("数学");
      expect(result.data.book.structure.chapters.length).toBe(3);
    });

    it("should parse chapter information correctly", () => {
      const result = booksGet({ book_id: "gM001" });
      const chapters = result.data.book.structure.chapters;
      expect(chapters[0].title).toBe("第1章 数と式");
      expect(chapters[0].range?.start).toBe(1);
      expect(chapters[0].range?.end).toBe(50);
      expect(chapters[0].numbering).toBe("問");
    });

    it("should get book with no chapters", () => {
      const result = booksGet({ book_id: "gP001" });
      expect(result.ok).toBe(true);
      expect(result.data.book.structure.chapters.length).toBe(0);
    });

    it("should get multiple books by IDs", () => {
      const result = booksGet({ book_ids: ["gM001", "gE001"] });
      expect(result.ok).toBe(true);
      expect(result.data.books.length).toBe(2);
      expect(result.data.books.map((b: any) => b.id)).toContain("gM001");
      expect(result.data.books.map((b: any) => b.id)).toContain("gE001");
    });

    it("should return error when book not found", () => {
      const result = booksGet({ book_id: "gX999" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when no ID provided", () => {
      const result = booksGet({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should include assessment info", () => {
      const result = booksGet({ book_id: "gM001" });
      expect(result.data.book.assessment.book_type).toBe("基礎");
      expect(result.data.book.assessment.quiz_type).toBe("選択");
      expect(result.data.book.assessment.quiz_id).toBe("qM001");
    });

    it("should parse monthly goal", () => {
      const result = booksGet({ book_id: "gM001" });
      expect(result.data.book.monthly_goal.text).toBe("2時間/日");
      expect(result.data.book.monthly_goal.per_day_minutes).toBe(120);
    });
  });

  describe("booksFilter", () => {
    it("should filter by exact match (where)", () => {
      const result = booksFilter({ where: { "教科": "数学" } });
      expect(result.ok).toBe(true);
      expect(result.data.books.length).toBe(1);
      expect(result.data.books[0].id).toBe("gM001");
    });

    it("should filter by partial match (contains)", () => {
      const result = booksFilter({ contains: { "参考書名": "エッセンス" } });
      expect(result.ok).toBe(true);
      expect(result.data.books.length).toBe(1);
      expect(result.data.books[0].id).toBe("gP001");
    });

    it("should return all books when no filter", () => {
      const result = booksFilter({});
      expect(result.ok).toBe(true);
      expect(result.data.books.length).toBe(3);
    });

    it("should respect limit", () => {
      const result = booksFilter({ limit: 2 });
      expect(result.ok).toBe(true);
      expect(result.data.books.length).toBe(2);
    });

    it("should return empty when no matches", () => {
      const result = booksFilter({ where: { "教科": "地学" } });
      expect(result.ok).toBe(true);
      expect(result.data.books).toEqual([]);
      expect(result.data.count).toBe(0);
    });

    it("should include chapters in filtered results", () => {
      const result = booksFilter({ where: { "教科": "数学" } });
      expect(result.data.books[0].structure.chapters.length).toBe(3);
    });
  });

  describe("booksCreate", () => {
    it("should create book with auto-generated ID", () => {
      const result = booksCreate({
        title: "新規参考書",
        subject: "数学",
      });
      expect(result.ok).toBe(true);
      expect(result.data.id).toMatch(/^gMB\d+$/); // MB = 数学 prefix
      expect(result.data.created_rows).toBeGreaterThanOrEqual(1);
    });

    it("should create book with custom prefix", () => {
      const result = booksCreate({
        title: "カスタム本",
        subject: "英語",
        id_prefix: "custom",
      });
      expect(result.ok).toBe(true);
      expect(result.data.id).toMatch(/^custom\d+$/);
    });

    it("should create book with optional parameters", () => {
      const result = booksCreate({
        title: "オプション付き本",
        subject: "物理",
        unit_load: 2,
        monthly_goal: "1時間/日",
      });
      expect(result.ok).toBe(true);
      expect(result.data.id).toBeDefined();
    });

    it("should return error when title missing", () => {
      const result = booksCreate({ subject: "数学" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when subject missing", () => {
      const result = booksCreate({ title: "テスト本" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });
  });

  describe("booksUpdate", () => {
    it("should return preview when no confirm_token", () => {
      const result = booksUpdate({
        book_id: "gM001",
        updates: { "参考書名": "青チャート数学1A 改訂版" },
      });
      expect(result.ok).toBe(true);
      expect(result.data.requires_confirmation).toBe(true);
      expect(result.data.confirm_token).toBeDefined();
    });

    it("should return error when confirm_token is invalid", () => {
      const result = booksUpdate({
        book_id: "gM001",
        confirm_token: "invalid-token",
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("CONFIRM_EXPIRED");
    });

    it("should return error when book not found", () => {
      const result = booksUpdate({
        book_id: "gX999",
        updates: { "参考書名": "test" },
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when book_id missing", () => {
      const result = booksUpdate({ updates: { "参考書名": "test" } });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });
  });

  describe("booksDelete", () => {
    it("should return preview when no confirm_token", () => {
      const result = booksDelete({ book_id: "gM001" });
      expect(result.ok).toBe(true);
      expect(result.data.requires_confirmation).toBe(true);
      expect(result.data.confirm_token).toBeDefined();
      expect(result.data.preview).toBeDefined();
    });

    it("should return error when confirm_token is invalid", () => {
      const result = booksDelete({
        book_id: "gM001",
        confirm_token: "invalid-token",
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("CONFIRM_EXPIRED");
    });

    it("should return error when book not found", () => {
      const result = booksDelete({ book_id: "gX999" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when book_id missing", () => {
      const result = booksDelete({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });
  });
});

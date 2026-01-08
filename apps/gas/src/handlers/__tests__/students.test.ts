/**
 * Tests for handlers/students.ts
 * Student master CRUD operations
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  studentsList,
  studentsFind,
  studentsGet,
  studentsFilter,
  studentsCreate,
  studentsUpdate,
  studentsDelete,
} from "../students";
import {
  mockSpreadsheetData,
  resetAllMocks,
  mockSpreadsheetApp,
  mockCache,
} from "../../__mocks__/gas-stubs";

// Sample student data for testing
const SAMPLE_HEADERS = ["生徒ID", "氏名", "学年", "スピードプランナーID", "面談メモID", "タグ", "Status"];
const SAMPLE_DATA = [
  SAMPLE_HEADERS,
  ["s001", "山田太郎", "高3", "planner-001", "meeting-001", "受験生", "在塾"],
  ["s002", "鈴木花子", "高2", "planner-002", "meeting-002", "推薦", "在塾"],
  ["s003", "田中一郎", "高1", "planner-003", "", "一般", "在塾"],
  ["s004", "佐藤美咲", "中3", "", "", "", "退塾"],
];

describe("students handlers", () => {
  beforeEach(() => {
    resetAllMocks();
    // Default mock setup
    mockSpreadsheetData({ "生徒マスター": SAMPLE_DATA });
  });

  describe("studentsList", () => {
    it("should return all students", () => {
      const result = studentsList({});
      expect(result.ok).toBe(true);
      expect(result.op).toBe("students.list");
      expect(result.data.students.length).toBe(4);
      expect(result.data.count).toBe(4);
    });

    it("should return students with limit", () => {
      const result = studentsList({ limit: 2 });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(2);
      expect(result.data.count).toBe(2);
    });

    it("should return student with correct properties", () => {
      const result = studentsList({ limit: 1 });
      const student = result.data.students[0];
      expect(student.id).toBe("s001");
      expect(student.name).toBe("山田太郎");
      expect(student.grade).toBe("高3");
      expect(student.planner_sheet_id).toBe("planner-001");
      expect(student.meeting_doc_id).toBe("meeting-001");
      expect(student.tags).toBe("受験生");
    });

    it("should return empty array when no data", () => {
      mockSpreadsheetData({ "生徒マスター": [SAMPLE_HEADERS] });
      const result = studentsList({});
      expect(result.ok).toBe(true);
      expect(result.data.students).toEqual([]);
      expect(result.data.count).toBe(0);
    });

    it("should handle missing sheet", () => {
      mockSpreadsheetApp.openById.mockReturnValue({
        getSheetByName: vi.fn(() => null),
        getSheets: vi.fn(() => []),
      } as any);
      const result = studentsList({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });
  });

  describe("studentsFind", () => {
    it("should find student by exact name match", () => {
      const result = studentsFind({ query: "山田太郎" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeGreaterThan(0);
      expect(result.data.top.student_id).toBe("s001");
      expect(result.data.top.reason).toBe("exact");
      expect(result.data.confidence).toBe(1.0);
    });

    it("should find student by partial name match", () => {
      const result = studentsFind({ query: "山田" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeGreaterThan(0);
      expect(result.data.top.student_id).toBe("s001");
      expect(result.data.top.reason).toBe("partial");
    });

    it("should find student by ID", () => {
      const result = studentsFind({ query: "s002" });
      expect(result.ok).toBe(true);
      expect(result.data.top.student_id).toBe("s002");
    });

    it("should return error when query is missing", () => {
      const result = studentsFind({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should limit results", () => {
      const result = studentsFind({ query: "s", limit: 2 });
      expect(result.ok).toBe(true);
      expect(result.data.candidates.length).toBeLessThanOrEqual(2);
    });

    it("should handle no matches", () => {
      const result = studentsFind({ query: "存在しない名前" });
      expect(result.ok).toBe(true);
      expect(result.data.candidates).toEqual([]);
      expect(result.data.top).toBeNull();
      expect(result.data.confidence).toBe(0);
    });
  });

  describe("studentsGet", () => {
    it("should get single student by ID", () => {
      const result = studentsGet({ student_id: "s001" });
      expect(result.ok).toBe(true);
      expect(result.data.student.id).toBe("s001");
      expect(result.data.student.name).toBe("山田太郎");
    });

    it("should get multiple students by IDs array", () => {
      const result = studentsGet({ student_ids: ["s001", "s003"] });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(2);
      expect(result.data.students.map((s: any) => s.id)).toContain("s001");
      expect(result.data.students.map((s: any) => s.id)).toContain("s003");
    });

    it("should return error when student not found", () => {
      const result = studentsGet({ student_id: "s999" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when no ID provided", () => {
      const result = studentsGet({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });
  });

  describe("studentsFilter", () => {
    it("should filter by exact match (where)", () => {
      const result = studentsFilter({ where: { "学年": "高3" } });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(1);
      expect(result.data.students[0].name).toBe("山田太郎");
    });

    it("should filter by partial match (contains)", () => {
      const result = studentsFilter({ contains: { "氏名": "田" } });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(2); // 山田太郎, 田中一郎
    });

    it("should combine where and contains", () => {
      const result = studentsFilter({
        where: { "Status": "在塾" },
        contains: { "タグ": "受験" },
      });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(1);
      expect(result.data.students[0].id).toBe("s001");
    });

    it("should respect limit", () => {
      const result = studentsFilter({ where: { "Status": "在塾" }, limit: 2 });
      expect(result.ok).toBe(true);
      expect(result.data.students.length).toBe(2);
    });

    it("should return empty when no matches", () => {
      const result = studentsFilter({ where: { "学年": "大学" } });
      expect(result.ok).toBe(true);
      expect(result.data.students).toEqual([]);
      expect(result.data.count).toBe(0);
    });
  });

  describe("studentsCreate", () => {
    it("should create new student with auto-generated ID", () => {
      const result = studentsCreate({
        record: { "氏名": "新規生徒", "学年": "高1" },
      });
      expect(result.ok).toBe(true);
      expect(result.data.created).toBe(true);
      expect(result.data.id).toMatch(/^s\d+$/);
    });

    it("should create student with custom prefix", () => {
      const result = studentsCreate({
        record: { "氏名": "テスト" },
        id_prefix: "test",
      });
      expect(result.ok).toBe(true);
      expect(result.data.id).toMatch(/^test\d+$/);
    });

    it("should use name and grade from request", () => {
      const result = studentsCreate({
        name: "直接指定",
        grade: "中2",
      });
      expect(result.ok).toBe(true);
      expect(result.data.created).toBe(true);
    });
  });

  describe("studentsUpdate", () => {
    it("should return preview with diff when no confirm_token", () => {
      const result = studentsUpdate({
        student_id: "s001",
        updates: { "学年": "大学1" },
      });
      expect(result.ok).toBe(true);
      expect(result.data.requires_confirmation).toBe(true);
      expect(result.data.confirm_token).toBeDefined();
      expect(result.data.preview.diffs).toBeDefined();
    });

    it("should apply update with valid confirm_token", () => {
      // First, get preview and token
      const preview = studentsUpdate({
        student_id: "s001",
        updates: { "学年": "大学1" },
      });
      const token = preview.data.confirm_token;

      // Then confirm
      const result = studentsUpdate({
        student_id: "s001",
        confirm_token: token,
      });
      expect(result.ok).toBe(true);
      expect(result.data.updated).toBe(true);
    });

    it("should return error when student not found", () => {
      const result = studentsUpdate({
        student_id: "s999",
        updates: { "学年": "高2" },
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when student_id is missing", () => {
      const result = studentsUpdate({ updates: { "学年": "高2" } });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when token expired", () => {
      const result = studentsUpdate({
        student_id: "s001",
        confirm_token: "invalid-token",
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("CONFIRM_EXPIRED");
    });

    it("should return error when student_id mismatch", () => {
      // Get token for s001
      const preview = studentsUpdate({
        student_id: "s001",
        updates: { "学年": "高2" },
      });
      const token = preview.data.confirm_token;

      // Try to use for s002
      const result = studentsUpdate({
        student_id: "s002",
        confirm_token: token,
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("CONFIRM_MISMATCH");
    });
  });

  describe("studentsDelete", () => {
    it("should return preview when no confirm_token", () => {
      const result = studentsDelete({ student_id: "s001" });
      expect(result.ok).toBe(true);
      expect(result.data.requires_confirmation).toBe(true);
      expect(result.data.confirm_token).toBeDefined();
      expect(result.data.preview.row).toBeDefined();
    });

    it("should delete with valid confirm_token", () => {
      // First, get preview and token
      const preview = studentsDelete({ student_id: "s001" });
      const token = preview.data.confirm_token;

      // Then confirm
      const result = studentsDelete({
        student_id: "s001",
        confirm_token: token,
      });
      expect(result.ok).toBe(true);
      expect(result.data.deleted).toBe(true);
    });

    it("should return error when student not found", () => {
      const result = studentsDelete({ student_id: "s999" });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("NOT_FOUND");
    });

    it("should return error when student_id is missing", () => {
      const result = studentsDelete({});
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("BAD_REQUEST");
    });

    it("should return error when token expired", () => {
      const result = studentsDelete({
        student_id: "s001",
        confirm_token: "invalid-token",
      });
      expect(result.ok).toBe(false);
      expect(result.error?.code).toBe("CONFIRM_EXPIRED");
    });
  });
});

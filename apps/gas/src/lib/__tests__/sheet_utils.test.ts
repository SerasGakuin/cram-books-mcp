/**
 * Tests for lib/sheet_utils.ts
 * Sheet utility functions for header normalization and column lookup
 */
import { describe, it, expect } from "vitest";
import { headerKey, pickCol, parseMonthlyGoal } from "../sheet_utils";

describe("headerKey", () => {
  it("should return empty string for null/undefined", () => {
    expect(headerKey(null as any)).toBe("");
    expect(headerKey(undefined as any)).toBe("");
  });

  it("should trim whitespace", () => {
    expect(headerKey("  参考書ID  ")).toBe("参考書id");
    expect(headerKey("\t教科\n")).toBe("教科");
  });

  it("should convert to lowercase", () => {
    expect(headerKey("ID")).toBe("id");
    expect(headerKey("Title")).toBe("title");
  });

  it("should normalize full-width characters (NFKC)", () => {
    expect(headerKey("ＩＤ")).toBe("id");
    expect(headerKey("参考書ＩＤ")).toBe("参考書id");
  });

  it("should remove all whitespace", () => {
    expect(headerKey("参考書 ID")).toBe("参考書id");
    expect(headerKey("book id")).toBe("bookid");
  });

  it("should handle full-width spaces", () => {
    expect(headerKey("参考書\u3000ID")).toBe("参考書id");
  });

  it("should handle mixed input", () => {
    expect(headerKey("  参考書　ＩＤ  ")).toBe("参考書id");
  });

  it("should convert numbers to string", () => {
    expect(headerKey(123 as any)).toBe("123");
  });
});

describe("pickCol", () => {
  const headers = ["参考書ID", "参考書名", "教科", "単元負荷"];

  it("should find column by exact match", () => {
    expect(pickCol(headers, ["教科"])).toBe(2);
  });

  it("should find column by first matching candidate", () => {
    expect(pickCol(headers, ["タイトル", "参考書名", "書名"])).toBe(1);
  });

  it("should return -1 when no match found", () => {
    expect(pickCol(headers, ["存在しない", "列名"])).toBe(-1);
  });

  it("should match case-insensitively", () => {
    const mixedHeaders = ["ID", "Title", "Subject"];
    expect(pickCol(mixedHeaders, ["id"])).toBe(0);
    expect(pickCol(mixedHeaders, ["TITLE"])).toBe(1);
  });

  it("should handle empty candidates", () => {
    expect(pickCol(headers, [])).toBe(-1);
  });

  it("should handle empty headers", () => {
    expect(pickCol([], ["教科"])).toBe(-1);
  });

  it("should normalize full-width characters in headers", () => {
    const fullWidthHeaders = ["参考書ＩＤ", "教科"];
    expect(pickCol(fullWidthHeaders, ["参考書ID"])).toBe(0);
  });

  it("should normalize full-width characters in candidates", () => {
    expect(pickCol(headers, ["参考書ＩＤ"])).toBe(0);
  });

  it("should find first match when multiple candidates exist", () => {
    expect(pickCol(headers, ["単元負荷", "参考書ID"])).toBe(3);
  });

  it("should handle headers with spaces", () => {
    const spacedHeaders = ["参考書 ID", "教 科"];
    expect(pickCol(spacedHeaders, ["参考書ID"])).toBe(0);
    expect(pickCol(spacedHeaders, ["教科"])).toBe(1);
  });
});

describe("parseMonthlyGoal", () => {
  it("should return null for null/undefined/empty", () => {
    expect(parseMonthlyGoal(null)).toBe(null);
    expect(parseMonthlyGoal(undefined)).toBe(null);
    expect(parseMonthlyGoal("")).toBe(null);
  });

  it("should parse hours and convert to minutes", () => {
    const result = parseMonthlyGoal("1日2時間");
    expect(result?.per_day_minutes).toBe(120);
    expect(result?.text).toBe("1日2時間");
  });

  it("should parse decimal hours", () => {
    const result = parseMonthlyGoal("1日1.5時間");
    expect(result?.per_day_minutes).toBe(90);
  });

  it("should handle different formats", () => {
    expect(parseMonthlyGoal("毎日1時間")?.per_day_minutes).toBe(60);
    expect(parseMonthlyGoal("3時間/日")?.per_day_minutes).toBe(180);
    expect(parseMonthlyGoal("週5時間")?.per_day_minutes).toBe(300);
  });

  it("should return null for per_day_minutes when no hours found", () => {
    const result = parseMonthlyGoal("毎日30分");
    expect(result?.per_day_minutes).toBe(null);
    expect(result?.text).toBe("毎日30分");
  });

  it("should always return null for days and total_minutes_est", () => {
    const result = parseMonthlyGoal("1日2時間");
    expect(result?.days).toBe(null);
    expect(result?.total_minutes_est).toBe(null);
  });

  it("should preserve original text", () => {
    const text = "1日3時間を目標に";
    const result = parseMonthlyGoal(text);
    expect(result?.text).toBe(text);
  });

  it("should handle numbers", () => {
    const result = parseMonthlyGoal(123);
    expect(result?.text).toBe("123");
    expect(result?.per_day_minutes).toBe(null);
  });

  it("should round minutes to integer", () => {
    // 1.33 hours = 79.8 minutes, should round to 80
    const result = parseMonthlyGoal("1.33時間");
    expect(result?.per_day_minutes).toBe(80);
  });

  it("should handle zero hours", () => {
    const result = parseMonthlyGoal("0時間");
    expect(result?.per_day_minutes).toBe(0);
  });
});

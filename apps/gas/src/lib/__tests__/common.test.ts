/**
 * Tests for lib/common.ts
 * Pure utility functions for response building and string normalization
 */
import { describe, it, expect } from "vitest";
import { ok, ng, normalize, toNumberOrNull, createJsonResponse, ApiResponse } from "../common";

describe("ok", () => {
  it("should create a success response with operation name", () => {
    const result = ok("books.find", { count: 5 });
    expect(result.ok).toBe(true);
    expect(result.op).toBe("books.find");
    expect(result.data).toEqual({ count: 5 });
    expect(result.meta?.ts).toBeDefined();
  });

  it("should create a success response with empty data by default", () => {
    const result = ok("ping");
    expect(result.ok).toBe(true);
    expect(result.op).toBe("ping");
    expect(result.data).toEqual({});
  });

  it("should include ISO timestamp in meta", () => {
    const result = ok("test");
    expect(result.meta?.ts).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });
});

describe("ng", () => {
  it("should create an error response with code and message", () => {
    const result = ng("books.find", "NOT_FOUND", "Book not found");
    expect(result.ok).toBe(false);
    expect(result.op).toBe("books.find");
    expect(result.error?.code).toBe("NOT_FOUND");
    expect(result.error?.message).toBe("Book not found");
  });

  it("should include details when provided", () => {
    const result = ng("books.create", "VALIDATION_ERROR", "Invalid input", { field: "title" });
    expect(result.error?.details).toEqual({ field: "title" });
  });

  it("should have empty details by default", () => {
    const result = ng("test", "ERROR", "Something went wrong");
    expect(result.error?.details).toEqual({});
  });
});

describe("normalize", () => {
  it("should return empty string for null/undefined", () => {
    expect(normalize(null)).toBe("");
    expect(normalize(undefined)).toBe("");
  });

  it("should trim whitespace", () => {
    expect(normalize("  hello  ")).toBe("hello");
    expect(normalize("\t\ntest\n\t")).toBe("test");
  });

  it("should convert to lowercase", () => {
    expect(normalize("HELLO")).toBe("hello");
    expect(normalize("HeLLo WoRLD")).toBe("helloworld");
  });

  it("should normalize full-width characters to half-width (NFKC)", () => {
    expect(normalize("ＡＢＣ")).toBe("abc");
    expect(normalize("１２３")).toBe("123");
  });

  it("should remove all whitespace", () => {
    expect(normalize("hello world")).toBe("helloworld");
    expect(normalize("a  b  c")).toBe("abc");
  });

  it("should handle full-width spaces", () => {
    expect(normalize("hello\u3000world")).toBe("helloworld");
  });

  it("should handle mixed input", () => {
    expect(normalize("  ＨｅＬＬＯ　ＷｏＲＬＤ  ")).toBe("helloworld");
  });

  it("should convert numbers to string", () => {
    expect(normalize(123)).toBe("123");
    expect(normalize(45.67)).toBe("45.67");
  });

  it("should handle Roman numerals (NFKC normalization)", () => {
    // Roman numeral characters like Ⅰ, Ⅱ, Ⅲ get normalized
    expect(normalize("Ⅰ")).toBe("i");
    expect(normalize("Ⅱ")).toBe("ii");
    expect(normalize("Ⅲ")).toBe("iii");
  });

  it("should handle circled numbers", () => {
    // Circled digits like ①, ②, ③ normalize to numbers
    expect(normalize("①")).toBe("1");
    expect(normalize("②")).toBe("2");
    expect(normalize("⑩")).toBe("10");
  });
});

describe("toNumberOrNull", () => {
  it("should return null for null/undefined", () => {
    expect(toNumberOrNull(null)).toBe(null);
    expect(toNumberOrNull(undefined)).toBe(null);
  });

  it("should return null for empty string", () => {
    expect(toNumberOrNull("")).toBe(null);
    expect(toNumberOrNull("   ")).toBe(null);
  });

  it("should parse integer strings", () => {
    expect(toNumberOrNull("42")).toBe(42);
    expect(toNumberOrNull("0")).toBe(0);
    expect(toNumberOrNull("-5")).toBe(-5);
  });

  it("should parse float strings", () => {
    expect(toNumberOrNull("3.14")).toBe(3.14);
    expect(toNumberOrNull("-2.5")).toBe(-2.5);
    expect(toNumberOrNull("0.001")).toBe(0.001);
  });

  it("should handle numbers directly", () => {
    expect(toNumberOrNull(42)).toBe(42);
    expect(toNumberOrNull(3.14)).toBe(3.14);
    expect(toNumberOrNull(0)).toBe(0);
  });

  it("should return null for non-numeric strings", () => {
    expect(toNumberOrNull("abc")).toBe(null);
    expect(toNumberOrNull("hello")).toBe(null);
    expect(toNumberOrNull("12abc")).toBe(null);
  });

  it("should return null for NaN", () => {
    expect(toNumberOrNull(NaN)).toBe(null);
  });

  it("should return null for Infinity", () => {
    expect(toNumberOrNull(Infinity)).toBe(null);
    expect(toNumberOrNull(-Infinity)).toBe(null);
  });

  it("should trim whitespace before parsing", () => {
    expect(toNumberOrNull("  42  ")).toBe(42);
    expect(toNumberOrNull("\t3.14\n")).toBe(3.14);
  });

  it("should handle scientific notation", () => {
    expect(toNumberOrNull("1e5")).toBe(100000);
    expect(toNumberOrNull("2.5e-3")).toBe(0.0025);
  });
});

describe("createJsonResponse", () => {
  it("should create a JSON text output from ApiResponse", () => {
    const response = ok("test", { key: "value" });
    const result = createJsonResponse(response);

    // Verify ContentService was called correctly
    expect(result.getContent()).toBe(JSON.stringify(response));
    expect(result.getMimeType()).toBe("application/json");
  });

  it("should handle error responses", () => {
    const response = ng("test", "ERROR", "Something went wrong");
    const result = createJsonResponse(response);

    expect(result.getContent()).toBe(JSON.stringify(response));
    expect(result.getMimeType()).toBe("application/json");
  });
});

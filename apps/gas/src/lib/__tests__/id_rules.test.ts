/**
 * Tests for lib/id_rules.ts
 * ID prefix determination and sequence generation
 */
import { describe, it, expect } from "vitest";
import { decidePrefix, nextIdForPrefix } from "../id_rules";

describe("decidePrefix", () => {
  describe("English subject variations", () => {
    it("should return EW for English writing", () => {
      expect(decidePrefix("英語", "英作文の基礎")).toBe("EW");
      expect(decidePrefix("英語", "自由英作文問題集")).toBe("EW");
      expect(decidePrefix("英語", "作文練習帳")).toBe("EW");
    });

    it("should return EL for English listening", () => {
      expect(decidePrefix("英語", "リスニング対策")).toBe("EL");
      expect(decidePrefix("英語", "聴解力向上")).toBe("EL");
    });

    it("should return EK for English interpretation/kaiseki", () => {
      expect(decidePrefix("英語", "英文解釈の技術")).toBe("EK");
      expect(decidePrefix("英語", "構文把握")).toBe("EK");
      expect(decidePrefix("英語", "パラグラフリーディング")).toBe("EK");
    });

    it("should return EC for English comprehension/reading", () => {
      expect(decidePrefix("英語", "長文読解")).toBe("EC");
      expect(decidePrefix("英語", "リーディング対策")).toBe("EC");
      expect(decidePrefix("英語", "読解力養成")).toBe("EC");
    });

    it("should return ET for English vocabulary", () => {
      expect(decidePrefix("英語", "単語帳")).toBe("ET");
      expect(decidePrefix("英語", "語彙力強化")).toBe("ET");
      expect(decidePrefix("英語", "熟語集")).toBe("ET");
      expect(decidePrefix("英語", "ターゲット1900")).toBe("ET");
      expect(decidePrefix("英語", "LEAP")).toBe("ET");
    });

    it("should return EB for English grammar", () => {
      expect(decidePrefix("英語", "文法問題集")).toBe("EB");
      expect(decidePrefix("英語", "スクランブル英文法")).toBe("EB");
      expect(decidePrefix("英語", "英文法基礎")).toBe("EB");
    });

    it("should default to EC for generic English", () => {
      expect(decidePrefix("英語", "総合問題集")).toBe("EC");
      expect(decidePrefix("英語", "入試対策")).toBe("EC");
    });
  });

  describe("Math subject", () => {
    it("should return MB for math subjects", () => {
      expect(decidePrefix("数学", "青チャート")).toBe("MB");
      expect(decidePrefix("数学I", "基礎問題集")).toBe("MB");
      expect(decidePrefix("数学II", "標準問題集")).toBe("MB");
      expect(decidePrefix("数学III", "発展問題")).toBe("MB");
      expect(decidePrefix("数学A", "確率統計")).toBe("MB");
      expect(decidePrefix("数学B", "ベクトル")).toBe("MB");
      expect(decidePrefix("数学C", "複素数平面")).toBe("MB");
    });
  });

  describe("Japanese subject variations", () => {
    it("should return JG for modern Japanese", () => {
      expect(decidePrefix("現代文", "読解演習")).toBe("JG");
      expect(decidePrefix("現代文", "入試対策")).toBe("JG");
    });

    it("should return JO for classical Japanese", () => {
      expect(decidePrefix("古文", "文法基礎")).toBe("JO");
      expect(decidePrefix("漢文", "句法演習")).toBe("JO");
      expect(decidePrefix("古典", "総合問題")).toBe("JO");
    });
  });

  describe("Social studies subjects", () => {
    it("should return JH for Japanese history", () => {
      expect(decidePrefix("日本史", "通史")).toBe("JH");
      expect(decidePrefix("日本史B", "問題集")).toBe("JH");
    });

    it("should return WH for world history", () => {
      expect(decidePrefix("世界史", "通史")).toBe("WH");
      expect(decidePrefix("世界史B", "問題集")).toBe("WH");
    });

    it("should return GG for geography", () => {
      expect(decidePrefix("地理", "系統地理")).toBe("GG");
      expect(decidePrefix("地理B", "問題集")).toBe("GG");
    });

    it("should return GE for politics/economics", () => {
      expect(decidePrefix("政治経済", "問題集")).toBe("GE");
      expect(decidePrefix("政治", "基礎知識")).toBe("GE");
      expect(decidePrefix("経済", "入門")).toBe("GE");
    });
  });

  describe("Science subjects", () => {
    it("should return PH for physics", () => {
      expect(decidePrefix("物理", "力学")).toBe("PH");
    });

    it("should return PHB for basic physics", () => {
      expect(decidePrefix("物理基礎", "入門")).toBe("PHB");
    });

    it("should return CH for chemistry", () => {
      expect(decidePrefix("化学", "有機化学")).toBe("CH");
    });

    it("should return CHB for basic chemistry", () => {
      expect(decidePrefix("化学基礎", "入門")).toBe("CHB");
    });

    it("should return BI for biology", () => {
      expect(decidePrefix("生物", "分子生物学")).toBe("BI");
    });

    it("should return BIB for basic biology", () => {
      expect(decidePrefix("生物基礎", "入門")).toBe("BIB");
    });

    it("should return ESB for basic earth science", () => {
      expect(decidePrefix("地学基礎", "入門")).toBe("ESB");
    });
  });

  describe("Fallback behavior", () => {
    it("should return MB for unknown subjects", () => {
      expect(decidePrefix("情報", "プログラミング")).toBe("MB");
      expect(decidePrefix("", "問題集")).toBe("MB");
      expect(decidePrefix("その他", "テスト")).toBe("MB");
    });
  });

  describe("Case insensitivity", () => {
    it("should handle case variations", () => {
      expect(decidePrefix("英語", "LEAP")).toBe("ET");
      expect(decidePrefix("英語", "leap")).toBe("ET");
    });
  });
});

describe("nextIdForPrefix", () => {
  it("should return prefix + 001 for empty data", () => {
    const allValues: any[][] = [["参考書ID", "タイトル"]];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB001");
  });

  it("should return prefix + 001 when no matching IDs exist", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gEC001", "英語長文"],
      ["gEC002", "英語リスニング"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB001");
  });

  it("should increment from existing max ID", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gMB001", "数学I"],
      ["gMB002", "数学II"],
      ["gMB005", "数学III"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB006");
  });

  it("should handle gaps in sequence", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gEC001", "英語1"],
      ["gEC010", "英語10"],
      ["gEC003", "英語3"],
    ];
    expect(nextIdForPrefix("gEC", allValues, 0)).toBe("gEC011");
  });

  it("should handle IDs with different column index", () => {
    const allValues: any[][] = [
      ["タイトル", "参考書ID", "教科"],
      ["数学I", "gMB001", "数学"],
      ["数学II", "gMB002", "数学"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 1)).toBe("gMB003");
  });

  it("should handle invalid column index", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gMB001", "数学I"],
    ];
    expect(nextIdForPrefix("gMB", allValues, -1)).toBe("gMB001");
  });

  it("should ignore non-matching prefixes", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gMB001", "数学"],
      ["gEC001", "英語"],
      ["gMB002", "数学II"],
      ["gJH001", "日本史"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB003");
    expect(nextIdForPrefix("gEC", allValues, 0)).toBe("gEC002");
    expect(nextIdForPrefix("gJH", allValues, 0)).toBe("gJH002");
  });

  it("should handle null/undefined values in cells", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      [null, "数学"],
      [undefined, "英語"],
      ["gMB001", "数学I"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB002");
  });

  it("should handle large numbers", () => {
    const allValues: any[][] = [
      ["参考書ID", "タイトル"],
      ["gMB999", "数学999"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB1000");
  });

  it("should pad numbers to 3 digits", () => {
    const allValues: any[][] = [["参考書ID", "タイトル"]];
    expect(nextIdForPrefix("gEC", allValues, 0)).toBe("gEC001");
  });

  it("should handle header row correctly (skip row 0)", () => {
    const allValues: any[][] = [
      ["gMB999", "Header looks like ID but should be skipped"],
      ["gMB001", "Actual data"],
    ];
    expect(nextIdForPrefix("gMB", allValues, 0)).toBe("gMB002");
  });
});

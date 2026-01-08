/**
 * Student resolution utilities
 * Extracts planner spreadsheet ID from student master sheet
 * (DRY: consolidated from planner.ts and planner_monthly.ts)
 */
import { CONFIG } from "../config";
import { pickCol, headerKey } from "./sheet_utils";

type RowMap = Record<string, any>;

/**
 * Column name candidates for student ID lookup
 */
export const STUDENT_ID_COLUMNS = ["生徒ID", "ID", "id"];

/**
 * Column name candidates for planner sheet ID
 */
export const PLANNER_ID_COLUMNS = [
  "スピードプランナーID",
  "PlannerSheetId",
  "planner_sheet_id",
  "プランナーID",
];

/**
 * Column name candidates for planner link (URL)
 */
export const PLANNER_LINK_COLUMNS = [
  "スプレッドシート",
  "スピードプランナー",
  "PlannerLink",
  "プランナーリンク",
  "スプレッドシートURL",
];

/**
 * Keywords for partial match fallback in header search
 */
const PLANNER_LINK_KEYWORDS = ["スプレッドシート", "planner", "プランナー"];

/**
 * Extract spreadsheet ID from URL string
 * Google Sheets URLs contain IDs that are 25+ characters of [-\w]
 */
export function extractSpreadsheetIdFromUrl(url: string): string | null {
  const match = String(url).match(/[-\w]{25,}/);
  return match ? match[0] : null;
}

/**
 * Resolve planner spreadsheet ID from student ID
 *
 * Resolution order:
 * 1. If req.spreadsheet_id is provided, return it directly
 * 2. Look up student in Students Master sheet by student_id
 * 3. Try to get planner ID from dedicated column (スピードプランナーID)
 * 4. Try to extract from link/URL column (with RichText support)
 *
 * @param req - Request object with student_id and/or spreadsheet_id
 * @returns Spreadsheet ID or null if not found
 */
export function resolveSpreadsheetIdByStudent(req: RowMap): string | null {
  // Direct spreadsheet_id takes precedence
  if (req.spreadsheet_id) {
    return String(req.spreadsheet_id);
  }

  const studentId = String(req.student_id || "").trim();
  if (!studentId) {
    return null;
  }

  try {
    const studentsFileId = req.students_file_id || CONFIG.STUDENTS_FILE_ID;
    const studentsSheetName = req.students_sheet || CONFIG.STUDENTS_SHEET;

    const ss = SpreadsheetApp.openById(studentsFileId);
    const sh = ss.getSheetByName(studentsSheetName) || ss.getSheets()[0];
    if (!sh) {
      return null;
    }

    const values = sh.getDataRange().getValues();
    if (values.length < 2) {
      return null;
    }

    const headers = values[0].map(String);
    const idxId = pickCol(headers, STUDENT_ID_COLUMNS);
    const idxPlannerId = pickCol(headers, PLANNER_ID_COLUMNS);
    let idxLink = pickCol(headers, PLANNER_LINK_COLUMNS);

    // Partial match fallback for link column
    if (idxLink < 0) {
      const normalizedHeaders = headers.map((h) => headerKey(h));
      const pos = normalizedHeaders.findIndex((hk) =>
        PLANNER_LINK_KEYWORDS.some(
          (keyword) => hk.includes(headerKey(keyword))
        )
      );
      if (pos >= 0) {
        idxLink = pos;
      }
    }

    // Search for student row
    for (let r = 1; r < values.length; r++) {
      const id = String(idxId >= 0 ? values[r][idxId] : "").trim();
      if (!id || id !== studentId) {
        continue;
      }

      // Found matching student
      // Try planner ID column first
      if (idxPlannerId >= 0) {
        const plannerId = String(values[r][idxPlannerId]).trim();
        if (plannerId) {
          return plannerId;
        }
      }

      // Try link column
      if (idxLink >= 0) {
        const spreadsheetId = extractSpreadsheetIdFromLink(sh, r, idxLink, values);
        if (spreadsheetId) {
          return spreadsheetId;
        }
      }

      // Student found but no planner ID
      return null;
    }

    // Student not found
    return null;
  } catch (_) {
    return null;
  }
}

/**
 * Extract spreadsheet ID from link column (handles RichText and plain URL)
 */
function extractSpreadsheetIdFromLink(
  sh: GoogleAppsScript.Spreadsheet.Sheet,
  rowIndex: number,
  colIndex: number,
  values: any[][]
): string | null {
  try {
    // Try RichText first (for hyperlinks)
    const rich = sh.getRange(rowIndex + 1, colIndex + 1).getRichTextValue();
    const url = (rich && rich.getLinkUrl()) || String(values[rowIndex][colIndex]).trim();
    return extractSpreadsheetIdFromUrl(url);
  } catch (_) {
    // Fallback to plain text
    const raw = String(values[rowIndex][colIndex]).trim();
    return extractSpreadsheetIdFromUrl(raw);
  }
}

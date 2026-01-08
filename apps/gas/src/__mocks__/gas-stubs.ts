/**
 * Google Apps Script API stubs for testing
 * These mocks allow unit tests to run without the actual GAS environment
 */
import { vi } from "vitest";

// Mock Range
export function createMockRange(values: any[][] = [[]]): GoogleAppsScript.Spreadsheet.Range {
  return {
    getValues: vi.fn(() => values),
    getDisplayValues: vi.fn(() => values.map((row) => row.map(String))),
    getValue: vi.fn(() => values[0]?.[0] ?? ""),
    getDisplayValue: vi.fn(() => String(values[0]?.[0] ?? "")),
    setValue: vi.fn(),
    setValues: vi.fn(),
    getRichTextValue: vi.fn(() => null),
    getNumRows: vi.fn(() => values.length),
    getNumColumns: vi.fn(() => values[0]?.length ?? 0),
  } as unknown as GoogleAppsScript.Spreadsheet.Range;
}

// Mock Sheet
export function createMockSheet(
  data: any[][] = [[]],
  name: string = "Sheet1"
): GoogleAppsScript.Spreadsheet.Sheet {
  return {
    getName: vi.fn(() => name),
    getDataRange: vi.fn(() => createMockRange(data)),
    getRange: vi.fn((a1OrRow: string | number, col?: number, numRows?: number, numCols?: number) => {
      if (typeof a1OrRow === "string") {
        // A1 notation - return full data for simplicity
        return createMockRange(data);
      }
      // Row/col notation
      const startRow = a1OrRow - 1;
      const startCol = (col ?? 1) - 1;
      const rows = numRows ?? 1;
      const cols = numCols ?? 1;
      const sliced = data.slice(startRow, startRow + rows).map((row) => row.slice(startCol, startCol + cols));
      return createMockRange(sliced);
    }),
    getLastRow: vi.fn(() => data.length),
    getLastColumn: vi.fn(() => data[0]?.length ?? 0),
    insertRowsAfter: vi.fn(),
    deleteRow: vi.fn(),
    deleteRows: vi.fn(),
  } as unknown as GoogleAppsScript.Spreadsheet.Sheet;
}

// Mock Spreadsheet
export function createMockSpreadsheet(
  sheets: Record<string, any[][]> = {}
): GoogleAppsScript.Spreadsheet.Spreadsheet {
  return {
    getSheetByName: vi.fn((name: string) => {
      if (sheets[name]) {
        return createMockSheet(sheets[name], name);
      }
      return null;
    }),
    getSheets: vi.fn(() => Object.entries(sheets).map(([name, data]) => createMockSheet(data, name))),
  } as unknown as GoogleAppsScript.Spreadsheet.Spreadsheet;
}

// Global SpreadsheetApp stub
const mockSpreadsheetApp = {
  openById: vi.fn((id: string) => createMockSpreadsheet({})),
};

// Global CacheService stub
const mockCache = new Map<string, string>();
const mockCacheService = {
  getScriptCache: vi.fn(() => ({
    put: vi.fn((key: string, value: string, _expirationInSeconds: number) => {
      mockCache.set(key, value);
    }),
    get: vi.fn((key: string) => mockCache.get(key) ?? null),
    remove: vi.fn((key: string) => {
      mockCache.delete(key);
    }),
  })),
};

// Global ContentService stub
const mockContentService = {
  createTextOutput: vi.fn((text: string) => {
    let mimeType = "text/plain";
    const output = {
      setMimeType: vi.fn((type: GoogleAppsScript.Content.MimeType) => {
        mimeType = type as unknown as string;
        return output;
      }),
      getContent: vi.fn(() => text),
      getMimeType: vi.fn(() => mimeType),
    };
    return output;
  }),
  MimeType: {
    JSON: "application/json" as GoogleAppsScript.Content.MimeType,
  },
};

// Global Utilities stub
const mockUtilities = {
  getUuid: vi.fn(() => "test-uuid-" + Math.random().toString(36).substring(2, 9)),
};

// Global PropertiesService stub
const mockPropertiesService = {
  getScriptProperties: vi.fn(() => ({
    getProperty: vi.fn((key: string) => null),
    setProperty: vi.fn(),
    deleteProperty: vi.fn(),
    getProperties: vi.fn(() => ({})),
  })),
};

// Global Browser stub (for interactive tests)
const mockBrowser = {
  inputBox: vi.fn(() => "cancel"),
  msgBox: vi.fn(),
  Buttons: {
    OK: "ok",
    OK_CANCEL: "ok_cancel",
    YES_NO: "yes_no",
    YES_NO_CANCEL: "yes_no_cancel",
  },
};

// Attach to global
declare global {
  var SpreadsheetApp: typeof mockSpreadsheetApp;
  var CacheService: typeof mockCacheService;
  var ContentService: typeof mockContentService;
  var Utilities: typeof mockUtilities;
  var PropertiesService: typeof mockPropertiesService;
  var Browser: typeof mockBrowser;
}

globalThis.SpreadsheetApp = mockSpreadsheetApp;
globalThis.CacheService = mockCacheService;
globalThis.ContentService = mockContentService;
globalThis.Utilities = mockUtilities;
globalThis.PropertiesService = mockPropertiesService;
globalThis.Browser = mockBrowser;

// Helper to reset all mocks between tests
export function resetAllMocks(): void {
  vi.clearAllMocks();
  mockCache.clear();
}

// Helper to configure SpreadsheetApp mock for specific test
export function mockSpreadsheetData(sheets: Record<string, any[][]>): void {
  mockSpreadsheetApp.openById.mockReturnValue(createMockSpreadsheet(sheets));
}

// Export for use in tests
export {
  mockSpreadsheetApp,
  mockCacheService,
  mockContentService,
  mockUtilities,
  mockPropertiesService,
  mockBrowser,
  mockCache,
};

/**
 * Spreadsheet service interfaces for dependency injection
 * These interfaces allow mocking Google Apps Script services in tests
 */

/**
 * Interface for RichTextValue (for extracting hyperlinks)
 */
export interface IRichTextValue {
  getLinkUrl(): string | null;
}

/**
 * Interface for Range operations
 */
export interface IRange {
  getValues(): any[][];
  getDisplayValues(): string[][];
  getValue(): any;
  getDisplayValue(): string;
  setValue(value: any): void;
  setValues(values: any[][]): void;
  getRichTextValue(): IRichTextValue | null;
  getNumRows(): number;
  getNumColumns(): number;
}

/**
 * Interface for Sheet operations
 */
export interface ISheet {
  getName(): string;
  getRange(a1Notation: string): IRange;
  getRange(row: number, column: number): IRange;
  getRange(row: number, column: number, numRows: number): IRange;
  getRange(row: number, column: number, numRows: number, numColumns: number): IRange;
  getDataRange(): IRange;
  getLastRow(): number;
  getLastColumn(): number;
  insertRowsAfter(afterPosition: number, howMany: number): void;
  deleteRow(rowPosition: number): void;
  deleteRows(rowPosition: number, howMany: number): void;
}

/**
 * Interface for Spreadsheet
 */
export interface ISpreadsheet {
  getSheetByName(name: string): ISheet | null;
  getSheets(): ISheet[];
  getId(): string;
}

/**
 * Interface for SpreadsheetApp service
 */
export interface ISpreadsheetService {
  openById(id: string): ISpreadsheet;
}

/**
 * Interface for CacheService
 */
export interface ICacheService {
  put(key: string, value: string, expirationInSeconds: number): void;
  get(key: string): string | null;
  remove(key: string): void;
}

/**
 * Interface for PropertiesService
 */
export interface IPropertiesService {
  getProperty(key: string): string | null;
  setProperty(key: string, value: string): void;
  deleteProperty(key: string): void;
  getProperties(): Record<string, string>;
}

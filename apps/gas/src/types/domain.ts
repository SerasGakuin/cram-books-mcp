/**
 * Domain type definitions
 * Strongly typed interfaces to replace Record<string, any>
 */

/**
 * Book metadata (parent row data)
 */
export interface BookMeta {
  id: string;
  title: string;
  subject: string;
  monthlyGoal: string;
  unitLoad: number | null;
  bookType: string;
  quizType: string;
  quizId: string;
}

/**
 * Chapter information (child rows)
 */
export interface Chapter {
  idx: number | null;
  title: string | null;
  range: ChapterRange | null;
  numbering: string | null;
}

/**
 * Chapter range (start/end page/problem numbers)
 */
export interface ChapterRange {
  start: number | null;
  end: number | null;
}

/**
 * Book with full details including chapters
 */
export interface BookWithChapters extends BookMeta {
  chapters: Chapter[];
}

/**
 * Book search result
 */
export interface BookSearchResult {
  id: string;
  subject: string;
  title: string;
  score: number;
}

/**
 * Student record
 */
export interface Student {
  id: string;
  name: string;
  grade: string;
  plannerSheetId: string;
  meetingDocId: string;
  status: string;
  tags: string;
}

/**
 * Planner item (row in weekly planner A-D columns)
 */
export interface PlannerItem {
  row: number;
  rawCode: string;
  monthCode: number | null;
  bookId: string;
  subject: string;
  title: string;
  guidelineNote: string;
}

/**
 * Week metrics (E/F/G columns per week)
 */
export interface WeekMetrics {
  weekIndex: number;
  items: WeekMetricsItem[];
}

export interface WeekMetricsItem {
  row: number;
  weeklyMinutes: number | null;
  unitLoad: number | null;
  guidelineAmount: number | null;
}

/**
 * Week plan (H column etc. per week)
 */
export interface WeekPlan {
  weekIndex: number;
  items: WeekPlanItem[];
}

export interface WeekPlanItem {
  row: number;
  planText: string;
  weeklyMinutes?: number | null;
  unitLoad?: number | null;
  guidelineAmount?: number | null;
}

/**
 * Plan create request item
 */
export interface PlanCreateItem {
  weekIndex: number;
  row: number;
  planText: string;
  overwrite?: boolean;
}

/**
 * Monthly planner record
 */
export interface MonthlyRecord {
  row: number;
  year: number;
  month: number;
  [key: string]: any;
}

/**
 * API request types
 */
export interface BooksGetRequest {
  book_id?: string;
  book_ids?: string[];
}

export interface BooksFindRequest {
  query: string;
  limit?: number;
}

export interface BooksFilterRequest {
  where?: Record<string, string>;
  contains?: Record<string, string>;
  limit?: number;
}

export interface BooksCreateRequest {
  title: string;
  subject: string;
  unit_load?: number;
  monthly_goal?: string;
  chapters?: ChapterInput[];
  id_prefix?: string;
}

export interface ChapterInput {
  title: string;
  range?: { start: number; end: number };
  numbering?: string;
}

export interface BooksUpdateRequest {
  book_id: string;
  updates?: Record<string, any>;
  confirm_token?: string;
}

export interface BooksDeleteRequest {
  book_id: string;
  confirm_token?: string;
}

export interface StudentsListRequest {
  limit?: number;
  include_all?: boolean;
}

export interface StudentsGetRequest {
  student_id?: string;
  student_ids?: string[];
}

export interface StudentsFindRequest {
  query: string;
  limit?: number;
  include_all?: boolean;
}

export interface StudentsFilterRequest {
  where?: Record<string, string>;
  contains?: Record<string, string>;
  limit?: number;
  include_all?: boolean;
}

export interface PlannerRequest {
  student_id?: string;
  spreadsheet_id?: string;
}

export interface PlannerPlanSetRequest extends PlannerRequest {
  week_index?: number;
  row?: number;
  plan_text?: string;
  overwrite?: boolean;
  items?: PlanCreateItem[];
}

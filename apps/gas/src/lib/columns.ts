/**
 * Centralized column name definitions
 * (DRY: candidate arrays used across handlers)
 */

/**
 * Books Master sheet column candidates
 */
export const BOOK_COLUMNS = {
  id: ["参考書ID", "ID", "id"],
  title: ["参考書名", "タイトル", "書名", "title"],
  subject: ["教科", "科目", "subject"],
  unitLoad: ["単元負荷", "単位負荷", "負荷", "unit_load"],
  monthlyGoal: ["月間目標", "目標", "monthly_goal"],
  bookType: ["参考書のタイプ", "タイプ", "book_type"],
  quizType: ["確認テストのタイプ", "テストタイプ", "quiz_type"],
  quizId: ["確認テストID", "テストID", "quiz_id"],
  chapterTitle: ["章タイトル", "章名", "chapter_title"],
  chapterStart: ["開始", "start", "章開始"],
  chapterEnd: ["終了", "end", "章終了"],
  chapterNumbering: ["番号形式", "numbering", "ナンバリング"],
};

/**
 * Students Master sheet column candidates
 */
export const STUDENT_COLUMNS = {
  id: ["生徒ID", "ID", "id"],
  name: ["氏名", "名前", "生徒名", "name"],
  grade: ["学年", "grade"],
  plannerSheetId: [
    "スピードプランナーID",
    "PlannerSheetId",
    "planner_sheet_id",
    "プランナーID",
  ],
  plannerLink: [
    "スプレッドシート",
    "スピードプランナー",
    "PlannerLink",
    "プランナーリンク",
    "スプレッドシートURL",
  ],
  meetingDocId: ["面談ドキュメント", "meeting_doc_id", "MeetingDocId"],
  status: ["ステータス", "Status", "status", "在籍状況"],
  tags: ["タグ", "tags", "Tags"],
};

/**
 * Weekly planner column mapping (week 1-5)
 * Each week has: time (weekly_minutes), unit (unit_load), guide (guideline_amount), plan (plan_text)
 */
export const WEEK_COLUMNS = [
  { index: 1, time: "E", unit: "F", guide: "G", plan: "H" },
  { index: 2, time: "M", unit: "N", guide: "O", plan: "P" },
  { index: 3, time: "U", unit: "V", guide: "W", plan: "X" },
  { index: 4, time: "AC", unit: "AD", guide: "AE", plan: "AF" },
  { index: 5, time: "AK", unit: "AL", guide: "AM", plan: "AN" },
] as const;

/**
 * Week start date cell addresses (D1, L1, T1, AB1, AJ1)
 */
export const WEEK_START_ADDRESSES = ["D1", "L1", "T1", "AB1", "AJ1"] as const;

/**
 * Planner sheet name variants (for flexible lookup)
 */
export const WEEKLY_SHEET_NAMES = ["週間管理", "週間計画", "週刊計画", "週刊管理"];
export const MONTHLY_SHEET_NAME = "月間管理";

/**
 * Status values for filtering active students
 */
export const ACTIVE_STATUS_VALUES = ["在塾", "在籍", "active", "Active"];

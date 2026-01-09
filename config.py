"""
Configuration constants for the MCP server.
Centralizes spreadsheet IDs, sheet names, and column mappings.
Ported from apps/gas/src/lib/columns.ts
"""
from typing import Final

# Master spreadsheet IDs
BOOKS_MASTER_ID: Final[str] = "1Z0mMUUchd9BT6r5dB6krHjPWETxOJo7pJuf2VrQ_Pvs"
STUDENTS_MASTER_ID: Final[str] = "1hLQe1TO6bfmdk3kvyV3RNkWmBuHhMfr9y01lIs7FVVI"

# Sheet names
BOOKS_SHEET: Final[str] = "参考書マスター"
STUDENTS_SHEET: Final[str] = "生徒一覧"
WEEKLY_SHEET: Final[str] = "週間管理"
MONTHLY_SHEET: Final[str] = "月間管理"

# Planner week column mappings (1-indexed week -> column letter for plan cell)
WEEK_PLAN_COLUMNS = {
    1: "H",
    2: "P",
    3: "X",
    4: "AF",
    5: "AN",
}

# Planner week metrics columns (time/unit/guide for each week)
WEEK_METRICS_COLUMNS = {
    1: {"time": "E", "unit": "F", "guide": "G", "plan": "H"},
    2: {"time": "M", "unit": "N", "guide": "O", "plan": "P"},
    3: {"time": "U", "unit": "V", "guide": "W", "plan": "X"},
    4: {"time": "AC", "unit": "AD", "guide": "AE", "plan": "AF"},
    5: {"time": "AK", "unit": "AL", "guide": "AM", "plan": "AN"},
}

# Week start date cells
WEEK_START_CELLS = ["D1", "L1", "T1", "AB1", "AJ1"]

# Planner row range
PLANNER_START_ROW = 4
PLANNER_END_ROW = 30

# ID generation prefix mappings (subject -> prefix)
PREFIX_MAP = {
    "英語ライティング": "EW",
    "英語コミュニケーション": "EC",
    "英語": "EN",
    "数学B": "MB",
    "数学C": "MC",
    "数学I": "M1",
    "数学II": "M2",
    "数学III": "M3",
    "数学A": "MA",
    "数学": "MA",
    "古文": "JG",
    "漢文": "JK",
    "現代文": "JM",
    "国語": "JA",
    "物理": "PP",
    "化学": "PC",
    "生物": "PB",
    "地学": "PE",
    "日本史": "HJ",
    "世界史": "HW",
    "地理": "HG",
    "政治経済": "HP",
    "倫理": "HE",
    "現代社会": "HS",
}

# Books Master sheet column candidates
BOOK_COLUMNS: Final[dict[str, list[str]]] = {
    "id": ["参考書ID", "ID", "id"],
    "title": ["参考書名", "タイトル", "書名", "title"],
    "subject": ["教科", "科目", "subject"],
    "unit_load": ["単位当たり処理量", "単位処理量", "unit_load"],
    "monthly_goal": ["月間目標", "goal"],
    "chap_idx": ["章立て"],
    "chap_name": ["章の名前", "章名"],
    "chap_begin": ["章のはじめ", "開始", "begin", "start"],
    "chap_end": ["章の終わり", "終了", "end"],
    "numbering": ["番号の数え方", "番号", "numbering"],
    "book_type": ["参考書のタイプ", "book_type"],
    "quiz_type": ["確認テストのタイプ", "quiz_type"],
    "quiz_id": ["確認テストID", "quiz_id"],
}

# Students Master sheet column candidates
# Note: The actual sheet has an empty header for the ID column (column 0)
STUDENT_COLUMNS: Final[dict[str, list[str]]] = {
    "id": ["", "生徒ID", "ID", "id"],  # Empty string for column with no header
    "comiru_id": ["Comiru生徒番号", "comiru_id"],
    "name": ["名前", "氏名", "生徒名", "name"],
    "family_name": ["姓"],
    "given_name": ["名"],
    "grade": ["学年", "grade"],
    "status": ["Status", "ステータス", "status", "在籍状況"],
    "planner_link": [
        "スプレッドシート",
        "スピードプランナー",
        "PlannerLink",
        "プランナーリンク",
        "スプレッドシートURL",
    ],
    "planner_sheet_id": [
        "スピードプランナーID",
        "PlannerSheetId",
        "planner_sheet_id",
        "プランナーID",
    ],
    "meeting_doc": ["ドキュメント", "面談メモID", "MeetingDocId", "meeting_doc_id"],
    "tags": ["タグ", "tags"],
}

# Planner sheet name variants (for flexible lookup)
WEEKLY_SHEET_NAMES = ["週間管理", "週間計画", "週刊計画", "週刊管理"]
MONTHLY_SHEET_NAME = "月間管理"
MONTHPLAN_SHEET_NAME = "今月プラン"

# Monthplan week columns (1-indexed week -> column letter for hours)
MONTHPLAN_WEEK_COLUMNS = {1: "D", 2: "E", 3: "F", 4: "G", 5: "H"}

# Status values for filtering active students
ACTIVE_STATUS_VALUES = ["在塾", "在籍", "active", "Active"]

# Plan text maximum length
PLAN_TEXT_MAX_LENGTH = 52

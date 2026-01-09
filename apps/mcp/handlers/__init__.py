"""
Domain handlers for the MCP server.
Each module provides functions that operate on Google Sheets directly.
"""
from .books import (
    books_find,
    books_get,
    books_filter,
    books_create,
    books_update,
    books_delete,
    books_list,
)
from .students import (
    students_list,
    students_find,
    students_get,
    students_filter,
    students_create,
    students_update,
    students_delete,
)
from .planner import (
    planner_ids_list,
    planner_dates_get,
    planner_dates_set,
    planner_metrics_get,
    planner_plan_get,
    planner_plan_set,
    resolve_planner_sheet_id,
)
from .planner_monthly import planner_monthly_filter

__all__ = [
    # Books
    "books_find",
    "books_get",
    "books_filter",
    "books_create",
    "books_update",
    "books_delete",
    "books_list",
    # Students
    "students_list",
    "students_find",
    "students_get",
    "students_filter",
    "students_create",
    "students_update",
    "students_delete",
    # Planner (weekly)
    "planner_ids_list",
    "planner_dates_get",
    "planner_dates_set",
    "planner_metrics_get",
    "planner_plan_get",
    "planner_plan_set",
    "resolve_planner_sheet_id",
    # Planner (monthly)
    "planner_monthly_filter",
]

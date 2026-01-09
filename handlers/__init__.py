"""
Domain handlers for the MCP server.

Each module provides OOP-based handler classes that operate on Google Sheets directly.
"""
from handlers.books import BooksHandler
from handlers.students import StudentsHandler
from handlers.planner import PlannerHandler

__all__ = [
    "BooksHandler",
    "StudentsHandler",
    "PlannerHandler",
]

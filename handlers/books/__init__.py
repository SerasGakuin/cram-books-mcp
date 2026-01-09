"""
Books handler package.

Exports BooksHandler class for book-related operations.
"""
from handlers.books.handler import BooksHandler, BookMeta
from handlers.books.search import _calculate_idf

__all__ = ["BooksHandler", "BookMeta", "_calculate_idf"]

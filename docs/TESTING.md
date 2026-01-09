# Testing Guide

This document describes the testing infrastructure for the cram-books-mcp project.

## Overview

| Component | Framework | Tests | Coverage |
|-----------|-----------|-------|----------|
| MCP helpers (lib/) | pytest | 66 | 100% |
| MCP tools | pytest | 75 | ~70% |
| **Total** | | **141** | ~70% |

## Running Tests

```bash
cd apps/mcp

# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_helpers.py -v

# Run specific test class
uv run pytest tests/test_books_tools.py::TestBooksFind -v
```

## Test Structure

```
apps/mcp/tests/
├── conftest.py              # Fixtures and mock setup
├── test_helpers.py          # Helper function tests (66 tests)
├── test_books_tools.py      # Books tool tests (26 tests)
├── test_students_tools.py   # Students tool tests (25 tests)
└── test_planner_tools.py    # Planner tool tests (24 tests)
```

## Handler Mocking

Tests mock handlers directly instead of HTTP requests:

```python
# apps/mcp/conftest.py

@pytest.fixture
def mock_sheets_client():
    """Mock Google Sheets client"""
    mock = MagicMock()
    mock.get_all_values.return_value = []
    return mock

@pytest.fixture
def mock_handler_responses():
    """Standard handler response templates"""
    return {
        "books.find": {"ok": True, "op": "books.find", "data": {...}},
        "books.get": {"ok": True, "op": "books.get", "data": {...}},
        # ... other responses
    }
```

## Example Tests

### Helper Function Test

```python
from lib.common import normalize, ok, ng

class TestNormalize:
    def test_basic_normalization(self):
        assert normalize("  Hello World  ") == "hello world"

    def test_fullwidth_conversion(self):
        assert normalize("ＡＢＣ") == "abc"
```

### Tool Test

```python
import pytest
from unittest.mock import patch, MagicMock
from server import books_find

class TestBooksFind:
    @pytest.mark.asyncio
    async def test_find_book_success(self, mock_handler_responses):
        with patch("server.get_sheets_client") as mock_client, \
             patch("handlers.books.books_find") as mock_find:
            mock_find.return_value = mock_handler_responses["books.find"]
            result = await books_find(query="Test Book")
            assert result.get("ok") is True
```

## Test Categories

### Helper Tests (test_helpers.py)

| Category | Functions Tested |
|----------|-----------------|
| Common | normalize, ok, ng, to_number_or_none |
| Sheet Utils | norm_header, pick_col, tokenize, parse_monthly_goal |
| ID Rules | decide_prefix, next_id_for_prefix, extract_ids_from_values |

### Tool Tests

| File | Tools Tested |
|------|-------------|
| test_books_tools.py | books_find, books_get, books_filter, books_list, books_create, books_update, books_delete |
| test_students_tools.py | students_list, students_find, students_get, students_filter, students_create, students_update, students_delete |
| test_planner_tools.py | planner_ids_list, planner_dates_get/set, planner_plan_get/create, planner_monthly_filter, planner_guidance |

## CI/CD

Tests run automatically on GitHub Actions:

- **Trigger**: Push to any branch, PR to main
- **Workflow**: `.github/workflows/test.yml`
- **Steps**:
  1. Setup Python 3.12
  2. Install dependencies with uv
  3. Run pytest with coverage
  4. Report results

## Troubleshooting

### Common Issues

1. **Import errors**
   - Ensure you're in the `apps/mcp` directory
   - Run `uv sync` to install dependencies

2. **Mock not returning expected data**
   - Check that the correct handler is being mocked
   - Verify mock return value matches expected response format

3. **Async test issues**
   - Ensure `@pytest.mark.asyncio` decorator is present
   - Check that `pytest-asyncio` is installed

### Running Individual Tests

```bash
# Run a single test
uv run pytest tests/test_helpers.py::TestNormalize::test_basic_normalization -v

# Run with print output
uv run pytest tests/test_helpers.py -v -s
```

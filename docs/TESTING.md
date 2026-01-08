# Testing Guide

This document describes the testing infrastructure and how to run tests for the cram-books-mcp project.

## Overview

The project has comprehensive test coverage across both GAS (Google Apps Script) and MCP (Model Context Protocol) components:

| Component | Framework | Tests | Coverage |
|-----------|-----------|-------|----------|
| GAS lib/ | Vitest | 90 | ~100% |
| GAS handlers/ | Vitest | 111 | ~88% |
| MCP helpers | pytest | 66 | 100% |
| MCP tools | pytest | 71 | ~72% |
| **Total** | | **338** | ~80% |

## GAS Tests

### Running Tests

```bash
cd apps/gas

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Test Structure

```
apps/gas/src/
├── lib/__tests__/           # Library function tests
│   ├── common.test.ts       # API response helpers, normalization
│   ├── id_rules.test.ts     # ID generation, prefix rules
│   └── sheet_utils.test.ts  # Column picking, sheet utilities
├── handlers/__tests__/      # Handler tests
│   ├── books.test.ts        # Books CRUD (35 tests)
│   ├── students.test.ts     # Students CRUD (34 tests)
│   ├── planner.test.ts      # Planner operations (24 tests)
│   └── planner_monthly.test.ts  # Monthly filter (18 tests)
└── __mocks__/
    └── gas-stubs.ts         # Google Apps Script mocks
```

### GAS Mocking

Tests use Vitest with custom mocks for Google Apps Script globals:

```typescript
// apps/gas/src/__mocks__/gas-stubs.ts
export const mockSpreadsheetApp = {
  openById: vi.fn(),
};

export const mockCacheService = {
  getScriptCache: vi.fn(() => ({
    get: vi.fn(),
    put: vi.fn(),
    remove: vi.fn(),
  })),
};

// Helper for common test setup
export function mockSpreadsheetData(sheetData: Record<string, any[][]>) {
  // Sets up mock spreadsheet with given data
}
```

### Coverage Thresholds

```typescript
// apps/gas/vitest.config.ts
thresholds: {
  lines: 80,
  branches: 60,
  functions: 90,
  statements: 80,
}
```

## MCP Tests

### Running Tests

```bash
cd apps/mcp

# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_helpers.py -v
```

### Test Structure

```
apps/mcp/tests/
├── test_helpers.py          # Helper function tests (66 tests)
├── test_books_tools.py      # Books tool tests (26 tests)
├── test_students_tools.py   # Students tool tests (25 tests)
└── test_planner_tools.py    # Planner tool tests (20 tests)
```

### HTTP Mocking

Tests use pytest-httpx for mocking HTTP requests to GAS:

```python
# apps/mcp/conftest.py

@pytest.fixture
def mock_gas_api(httpx_mock, gas_responses):
    """Mock single GAS API response"""
    def _mock_api(response_key: str, method: str = "GET"):
        response = gas_responses.get(response_key)
        httpx_mock.add_response(json=response)
    return _mock_api

@pytest.fixture
def mock_gas_sequence(httpx_mock, gas_responses):
    """Mock sequence of GAS API responses"""
    def _mock_sequence(response_keys: list[str]):
        for key in response_keys:
            httpx_mock.add_response(json=gas_responses[key])
    return _mock_sequence
```

### Example Test

```python
class TestBooksFind:
    @pytest.mark.asyncio
    async def test_find_book_success(self, mock_gas_api):
        mock_gas_api("books.find")
        result = await books_find(query="Test Book")
        assert result.get("ok") is True
```

## CI/CD

Tests run automatically on GitHub Actions:

- **Trigger**: Push to any branch, PR to main
- **Workflow**: `.github/workflows/test.yml`
- **Stages**:
  1. GAS tests (Vitest + coverage)
  2. MCP tests (pytest + coverage)
  3. Coverage threshold validation

### Viewing CI Results

```bash
# Check recent workflow runs
gh run list --limit 5

# View details of a specific run
gh run view <run-id>
```

## Writing New Tests

### GAS Handler Test

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { myHandler } from "../myHandler";
import { resetAllMocks, mockSpreadsheetData } from "../../__mocks__/gas-stubs";

describe("myHandler", () => {
  beforeEach(() => {
    resetAllMocks();
    mockSpreadsheetData({ "SheetName": [...testData] });
  });

  it("should do something", () => {
    const result = myHandler({ param: "value" });
    expect(result.ok).toBe(true);
  });
});
```

### MCP Tool Test

```python
import pytest
from server import my_tool

class TestMyTool:
    @pytest.mark.asyncio
    async def test_basic_usage(self, mock_gas_api):
        mock_gas_api("expected.response")
        result = await my_tool(param="value")
        assert result.get("ok") is True
```

## Troubleshooting

### Common Issues

1. **GAS mock not returning expected data**
   - Check `mockSpreadsheetData` call matches expected sheet structure
   - Verify column headers match handler expectations

2. **MCP test timeout**
   - Ensure all HTTP requests are mocked
   - Use `mock_gas_sequence` for multi-request handlers

3. **Coverage below threshold**
   - Check uncovered lines in coverage report
   - Add tests for error paths and edge cases

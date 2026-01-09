"""
CRAM Books MCP Server

Connects Claude to Google Sheets via direct Google Sheets API access.
No longer depends on GAS WebApp intermediary.
"""
import os
import sys
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings
except ImportError:
    from fastmcp import FastMCP
    TransportSecuritySettings = None

# Import handlers (OOP-based handler classes)
from sheets_client import get_sheets_client
from handlers.books import BooksHandler
from handlers.students import StudentsHandler
from handlers.planner import PlannerHandler
from lib.input_parser import (
    coerce_str as _coerce_str,
    as_list as _as_list,
    resolve_entity_ids,
    resolve_planner_context,
)
from lib.errors import bad_request

# Configure transport security to allow Railway domain
transport_security = None
if TransportSecuritySettings:
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost:8080",
            "127.0.0.1:8080",
            "cram-books-mcp-production.up.railway.app",
        ],
    )

mcp = FastMCP("cram-books", transport_security=transport_security)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ===== Books Tools =====

@mcp.tool()
async def books_find(query: Any) -> dict:
    """参考書を曖昧検索します。

    引数:
    - query: 検索語（必須）。例: "青チャート"、"現代文" など。

    使い方（例）:
    - books_find({"query": "青チャート"})
    - books_find("青チャート")

    返り値（例）:
    {
      "ok": true,
      "op": "books.find",
      "data": {
        "query": "青チャート",
        "candidates": [{"book_id":"gMB017","title":"…","subject":"数学","score":0.95}],
        "top": { … },
        "confidence": 0.68
      }
    }
    """
    q = _coerce_str(query, ("query", "q", "text"))
    if not q:
        return bad_request("books.find", "query is required")

    sheets = get_sheets_client()
    handler = BooksHandler(sheets)
    return handler.find(q)


@mcp.tool()
async def books_get(book_id: Any = None, book_ids: Any = None) -> dict:
    """参考書の詳細を取得します。

    引数:
    - book_id: 単一ID（文字列）
    - book_ids: 複数ID（配列）。どちらか必須。

    使い方（例）:
    - 単一: books_get({"book_id":"gMB017"})
    - 複数: books_get({"book_ids":["gMB017","gMB018"]})

    返り値（例）:
    - 単一: { ok:true, data: { book: { id, title, subject, structure:{chapters…} } } }
    - 複数: { ok:true, data: { books: [ {id,…}, {id,…} ] } }
    """
    single, many = resolve_entity_ids(book_id, book_ids, ("book_id", "id"), "book_id")

    sheets = get_sheets_client()
    handler = BooksHandler(sheets)

    if many:
        return handler.get_multiple(many)
    if single:
        return handler.get(single)

    return bad_request("books.get", "book_id or book_ids is required")


@mcp.tool()
async def books_filter(where: Any = None, contains: Any = None, limit: int | None = 50) -> dict:
    """条件で参考書をフィルタします。

    引数:
    - where: 完全一致の条件（辞書）。例: {"教科":"数学"}
    - contains: 部分一致の条件（辞書）。例: {"参考書名":"青チャート"}
    - limit: 上限件数（既定 50）

    返り値（例）:
    { ok:true, data:{ books:[ {id,title,subject,…} ], count, limit } }
    """
    sheets = get_sheets_client()
    handler = BooksHandler(sheets)
    return handler.filter(
        where=where if isinstance(where, dict) else None,
        contains=contains if isinstance(contains, dict) else None,
        limit=limit,
    )


@mcp.tool()
async def books_list(limit: int | None = None) -> dict:
    """参考書を簡易一覧（id/subject/title のみ）。"""
    sheets = get_sheets_client()
    handler = BooksHandler(sheets)
    return handler.list(limit=limit)


@mcp.tool()
async def books_create(
    title: str,
    subject: str,
    unit_load: Any = None,
    monthly_goal: str | None = None,
    chapters: Any = None,
    id_prefix: str | None = None,
) -> dict:
    """参考書を新規作成（自動ID付与）。

    引数:
    - title: 参考書名（必須）
    - subject: 教科（必須）
    - unit_load: 単位処理量（任意）
    - monthly_goal: 月間目標（任意）
    - chapters: 章の配列（任意）
    - id_prefix: IDの接頭辞（任意）

    章の形式:
    [{"title":"第1章", "range":{"start":1, "end":20}, "numbering":"問"}, ...]
    """
    sheets = get_sheets_client()
    handler = BooksHandler(sheets)
    return handler.create(
        title=title,
        subject=subject,
        unit_load=int(unit_load) if unit_load is not None else None,
        monthly_goal=monthly_goal or "",
        chapters=chapters if isinstance(chapters, list) else None,
        id_prefix=id_prefix,
    )


@mcp.tool()
async def books_update(book_id: Any, updates: Any = None, confirm_token: str | None = None) -> dict:
    """参考書の更新（二段階: preview → confirm）。

    1) プレビュー: {book_id, updates} → 差分と confirm_token
    2) 確定: {book_id, confirm_token} → { updated }
    """
    bid = _coerce_str(book_id, ("book_id", "id"))
    if not bid:
        return bad_request("books.update", "book_id is required")

    sheets = get_sheets_client()
    handler = BooksHandler(sheets)

    if confirm_token:
        return handler.update(bid, confirm_token=confirm_token)
    elif isinstance(updates, dict):
        return handler.update(bid, updates=updates)
    else:
        return bad_request("books.update", "updates is required for preview")


@mcp.tool()
async def books_delete(book_id: Any, confirm_token: str | None = None) -> dict:
    """参考書の削除（二段階: preview → confirm）。"""
    bid = _coerce_str(book_id, ("book_id", "id"))
    if not bid:
        return bad_request("books.delete", "book_id is required")

    sheets = get_sheets_client()
    handler = BooksHandler(sheets)
    return handler.delete(bid, confirm_token=confirm_token)


# ===== Students Tools =====

@mcp.tool()
async def students_list(limit: int | None = None, include_all: bool | None = None) -> dict:
    """生徒一覧を取得。既定は「在塾のみ」。include_all=true で全員。"""
    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)

    if include_all:
        result = handler.list(limit=limit)
    else:
        # Filter by status=在塾
        result = handler.filter(where={"Status": "在塾"}, limit=limit)

    if not result.get("ok"):
        return result

    students = result.get("data", {}).get("students", [])
    return {
        "ok": True,
        "op": "students.list",
        "data": {
            "students": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "grade": s.get("grade"),
                    "planner_sheet_id": s.get("planner_sheet_id"),
                    "status": s.get("status"),
                }
                for s in students
            ],
            "count": len(students),
        },
    }


@mcp.tool()
async def students_find(query: Any, limit: int | None = 10, include_all: bool | None = None) -> dict:
    """生徒を名前で検索。既定は「在塾のみ」。"""
    q = _coerce_str(query, ("query", "q", "text"))
    if not q:
        return bad_request("students.find", "query is required")

    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)

    if include_all:
        return handler.find(query=q, limit=limit)
    else:
        # Filter by status=在塾 and name contains query
        return handler.filter(
            where={"Status": "在塾"},
            contains={"名前": q},
            limit=limit,
        )


@mcp.tool()
async def students_get(student_id: Any = None, student_ids: Any = None) -> dict:
    """生徒の詳細を取得（単一/複数対応）。"""
    single, many = resolve_entity_ids(student_id, student_ids, ("student_id", "id"), "student_id")

    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)

    if many:
        return handler.get_multiple(many)
    elif single:
        return handler.get(single)
    else:
        return bad_request("students.get", "student_id or student_ids is required")


@mcp.tool()
async def students_filter(
    where: Any = None,
    contains: Any = None,
    limit: int | None = None,
    include_all: bool | None = None,
) -> dict:
    """条件で生徒をフィルタ。既定は「在塾のみ」。"""
    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)

    w = where if isinstance(where, dict) else {}
    if not include_all and "Status" not in w and "status" not in w:
        w = {**w, "Status": "在塾"}

    return handler.filter(
        where=w if w else None,
        contains=contains if isinstance(contains, dict) else None,
        limit=limit,
    )


@mcp.tool()
async def students_create(record: dict[str, Any] | None = None, id_prefix: str | None = None) -> dict:
    """生徒の新規作成。record にシート見出し→値で渡す。"""
    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)
    return handler.create(record=record, id_prefix=id_prefix)


@mcp.tool()
async def students_update(student_id: Any, updates: dict[str, Any] | None = None, confirm_token: str | None = None) -> dict:
    """生徒の更新（二段階）。"""
    sid = _coerce_str(student_id, ("student_id", "id"))
    if not sid:
        return bad_request("students.update", "student_id is required")

    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)

    if confirm_token:
        return handler.update(sid, confirm_token=confirm_token)
    elif isinstance(updates, dict):
        return handler.update(sid, updates=updates)
    else:
        return bad_request("students.update", "updates is required for preview")


@mcp.tool()
async def students_delete(student_id: Any, confirm_token: str | None = None) -> dict:
    """生徒の削除（二段階）。"""
    sid = _coerce_str(student_id, ("student_id", "id"))
    if not sid:
        return bad_request("students.delete", "student_id is required")

    sheets = get_sheets_client()
    handler = StudentsHandler(sheets)
    return handler.delete(sid, confirm_token=confirm_token)


# ===== Planner (Weekly) Tools =====

@mcp.tool()
async def planner_ids_list(student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """A4:D30 を読み取り、raw_code/月コード/book_id/教科/タイトル/進め方メモを返します。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    if not (sid or spid):
        return bad_request("planner.ids_list", "student_id or spreadsheet_id is required")

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.ids_list(student_id=sid, spreadsheet_id=spid)


@mcp.tool()
async def planner_dates_get(student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """週開始日 D1/L1/T1/AB1/AJ1 を取得。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.dates_get(student_id=sid, spreadsheet_id=spid)


@mcp.tool()
async def planner_dates_set(start_date: str, student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """D1 の週開始日を設定。"""
    if not start_date:
        return bad_request("planner.dates.set", "start_date is required")

    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.dates_set(start_date=start_date, student_id=sid, spreadsheet_id=spid)


@mcp.tool()
async def planner_metrics_get(student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """週ごとの週間時間/単位処理量/目安処理量を取得。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.metrics_get(student_id=sid, spreadsheet_id=spid)


@mcp.tool()
async def planner_plan_get(student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """計画セル（H/P/X/AF/AN, 行4〜30）を取得。メトリクスも統合。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)

    # Get plans
    plans = handler.plan_get(student_id=sid, spreadsheet_id=spid)
    if not plans.get("ok"):
        return plans

    # Get metrics and merge
    metrics = handler.metrics_get(student_id=sid, spreadsheet_id=spid)
    if not metrics.get("ok"):
        return plans  # Return plans without metrics

    # Index metrics by week and row
    metrics_by_week = {}
    for wk in metrics.get("data", {}).get("weeks", []):
        wi = wk.get("week_index")
        metrics_by_week[wi] = {it.get("row"): it for it in wk.get("items", [])}

    # Merge metrics into plans
    for wk in plans.get("data", {}).get("weeks", []):
        wi = wk.get("week_index")
        row_map = metrics_by_week.get(wi, {})
        for item in wk.get("items", []):
            r = item.get("row")
            m = row_map.get(r, {})
            if m:
                item["weekly_minutes"] = m.get("weekly_minutes")
                item["unit_load"] = m.get("unit_load")
                item["guideline_amount"] = m.get("guideline_amount")

    return plans


@mcp.tool()
async def planner_plan_set(
    week_index: int | None = None,
    plan_text: str | None = None,
    row: int | None = None,
    book_id: str | None = None,
    overwrite: bool = False,
    items: list[dict] | None = None,
    student_id: Any = None,
    spreadsheet_id: Any = None,
) -> dict:
    """計画セルへの書込み。単体モードまたは一括(items)モード。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.plan_set(
        week_index=week_index,
        plan_text=plan_text,
        row=row,
        book_id=book_id,
        overwrite=overwrite,
        items=items,
        student_id=sid,
        spreadsheet_id=spid,
    )


@mcp.tool()
async def planner_plan_create(
    items: Any,
    student_id: Any = None,
    spreadsheet_id: Any = None,
    overwrite: bool | None = None,
) -> dict:
    """計画セルを一括作成（高速・単発）。

    MUST: 実行前に planner_guidance を読むこと。

    引数:
    - items: [{week_index, row|book_id, plan_text, overwrite?}, …]
    - student_id | spreadsheet_id: いずれか
    - overwrite: 省略時は false（空欄のみ）
    """
    if not isinstance(items, list) or not items:
        return bad_request("planner.plan.create", "items[] is required")

    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)

    # Get week count for validation
    dates = handler.dates_get(student_id=sid, spreadsheet_id=spid)
    week_count = 5
    if dates.get("ok"):
        ws = dates.get("data", {}).get("week_starts", [])
        week_count = sum(1 for x in ws if str(x or "").strip()) or 5

    # Validate and prepare items
    warnings = []
    prepared_items = []
    for it in items:
        try:
            wi = int(it.get("week_index"))
            txt = str(it.get("plan_text") or "")
        except (TypeError, ValueError):
            warnings.append(f"bad item: {it}")
            continue

        if wi < 1 or wi > week_count:
            warnings.append(f"week_index out of range: {wi} (1..{week_count})")
        if len(txt) > 52:
            warnings.append(f"plan_text too long ({len(txt)} > 52)")

        out_it = {"week_index": wi, "plan_text": txt}
        if overwrite is not None and it.get("overwrite") is None:
            out_it["overwrite"] = bool(overwrite)
        if it.get("overwrite") is not None:
            out_it["overwrite"] = bool(it.get("overwrite"))
        if it.get("row") is not None:
            out_it["row"] = it.get("row")
        if it.get("book_id") is not None:
            out_it["book_id"] = it.get("book_id")
        prepared_items.append(out_it)

    # Execute
    result = handler.plan_set(
        items=prepared_items,
        student_id=sid,
        spreadsheet_id=spid,
    )

    # Add guidance digest
    guidance = await planner_guidance()

    out = {
        "ok": result.get("ok"),
        "op": "planner.plan.create",
        "data": {
            **(result.get("data") or {}),
            "warnings": warnings,
            "guidance_digest": guidance.get("data", {}),
        },
    }
    if not result.get("ok"):
        out["error"] = result.get("error")

    return out


# ===== Planner (Monthly) Tools =====

@mcp.tool()
async def planner_monthly_filter(
    year: int | str,
    month: int | str,
    student_id: Any = None,
    spreadsheet_id: Any = None,
) -> dict:
    """月間管理から指定年月の実績を取得。"""
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.monthly_filter(
        year=int(year),
        month=int(month),
        student_id=sid,
        spreadsheet_id=spid,
    )


@mcp.tool()
async def monthplan_get(student_id: Any = None, spreadsheet_id: Any = None) -> dict:
    """「今月プラン」シートの内容を取得（週ごとの時間と集計情報付き）。

    Returns:
        items: 各参考書の週ごとの時間 (weeks: {1: 3, 2: 2, ...}) と行合計 (row_total)
        week_totals: 各週の全参考書合計時間 {1: 15, 2: 12, ...}
        grand_total: 全体の合計時間
        count: 参考書数
    """
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    if not (sid or spid):
        return bad_request("planner.monthplan.get", "student_id or spreadsheet_id is required")

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.monthplan_get(student_id=sid, spreadsheet_id=spid)


@mcp.tool()
async def monthplan_set(
    items: list[dict],
    student_id: Any = None,
    spreadsheet_id: Any = None,
) -> dict:
    """「今月プラン」シートに週ごとの時間をバッチ書き込み。

    引数:
        items: [{row: int, week: int (1-5), hours: int}, ...]
            - row: 行番号 (4-30)
            - week: 週番号 (1-5)
            - hours: 時間（整数）

    Returns:
        updated: True
        results: 各アイテムの処理結果 [{row, week, ok, cell?, error?}, ...]
    """
    sid, spid = resolve_planner_context(student_id, spreadsheet_id)

    if not (sid or spid):
        return bad_request("planner.monthplan.set", "student_id or spreadsheet_id is required")

    if not isinstance(items, list):
        return bad_request("planner.monthplan.set", "items must be a list")

    sheets = get_sheets_client()
    handler = PlannerHandler(sheets)
    return handler.monthplan_set(items=items, student_id=sid, spreadsheet_id=spid)


# ===== Utility Tools =====

@mcp.tool()
async def planner_guidance() -> dict:
    """LLM向け：週間管理シートの計画作成ガイドを返します。"""
    return {
        "ok": True,
        "op": "planner.guidance",
        "data": {
            "sheet": {
                "name": "週間管理",
                "rows": "4-30",
                "id_column": "A: <month_code><book_id>",
                "weeks": {
                    "1": {"time": "E", "unit": "F", "guide": "G", "plan": "H"},
                    "2": {"time": "M", "unit": "N", "guide": "O", "plan": "P"},
                    "3": {"time": "U", "unit": "V", "guide": "W", "plan": "X"},
                    "4": {"time": "AC", "unit": "AD", "guide": "AE", "plan": "AF"},
                    "5": {"time": "AK", "unit": "AL", "guide": "AM", "plan": "AN"},
                },
                "week_starts": ["D1", "L1", "T1", "AB1", "AJ1"],
            },
            "policy": {
                "preconditions": ["A[row]非空", "週間時間セル非空"],
                "overwrite_default": False,
                "max_chars": 52,
                "conservative_planning": True,
                "ask_when_uncertain": True,
            },
            "format": {
                "range": "~ を用いる",
                "multi": "カンマ/改行で複数範囲",
                "freeform": "短く具体的に",
            },
            "workflow": {
                "collect": [
                    "planner_ids_list で対象行を取得",
                    "planner_dates_get で週数を把握",
                    "planner_plan_get で計画＋metricsを取得",
                ],
                "write": [
                    "planner_plan_create(items) で一括作成",
                ],
            },
        },
    }


@mcp.tool()
async def tools_help() -> dict:
    """このMCPで公開中のツール一覧と使い方を返します。"""
    tools = [
        {"name": "books_find", "desc": "参考書の曖昧検索", "args": {"query": "string"}},
        {"name": "books_get", "desc": "参考書の詳細取得", "args": {"book_id": "string", "book_ids": "string[]"}},
        {"name": "books_filter", "desc": "条件で参考書を絞り込み", "args": {"where": "dict", "contains": "dict", "limit": "int"}},
        {"name": "books_list", "desc": "全参考書の一覧", "args": {"limit": "int"}},
        {"name": "books_create", "desc": "参考書の新規作成", "args": {"title": "string", "subject": "string", "chapters": "list"}},
        {"name": "books_update", "desc": "参考書の更新（二段階）", "args": {"book_id": "string", "updates": "dict", "confirm_token": "string"}},
        {"name": "books_delete", "desc": "参考書の削除（二段階）", "args": {"book_id": "string", "confirm_token": "string"}},
        {"name": "students_list", "desc": "生徒一覧（既定は在塾のみ）", "args": {"limit": "int", "include_all": "bool"}},
        {"name": "students_find", "desc": "生徒の検索", "args": {"query": "string", "limit": "int"}},
        {"name": "students_get", "desc": "生徒の詳細取得", "args": {"student_id": "string", "student_ids": "string[]"}},
        {"name": "students_filter", "desc": "条件で生徒を絞り込み", "args": {"where": "dict", "contains": "dict"}},
        {"name": "students_create", "desc": "生徒の新規作成", "args": {"record": "dict"}},
        {"name": "students_update", "desc": "生徒の更新（二段階）", "args": {"student_id": "string", "updates": "dict"}},
        {"name": "students_delete", "desc": "生徒の削除（二段階）", "args": {"student_id": "string"}},
        {"name": "planner_ids_list", "desc": "プランナーのID一覧取得", "args": {"student_id": "string"}},
        {"name": "planner_dates_get", "desc": "週開始日の取得", "args": {"student_id": "string"}},
        {"name": "planner_dates_set", "desc": "週開始日の設定", "args": {"start_date": "string"}},
        {"name": "planner_metrics_get", "desc": "週間メトリクスの取得", "args": {"student_id": "string"}},
        {"name": "planner_plan_get", "desc": "計画セルの取得", "args": {"student_id": "string"}},
        {"name": "planner_plan_create", "desc": "計画セルの一括作成", "args": {"items": "list"}},
        {"name": "planner_monthly_filter", "desc": "月間実績の取得", "args": {"year": "int", "month": "int"}},
        {"name": "planner_guidance", "desc": "計画作成ガイド", "args": {}},
    ]
    return {"ok": True, "op": "tools.help", "data": {"tools": tools}}


# ===== Server Entry Point =====

if __name__ == "__main__":
    import uvicorn
    from contextlib import asynccontextmanager
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse

    async def healthz(request):
        return JSONResponse({"status": "ok"})

    async def root(request):
        return JSONResponse(
            {"error": "Use /mcp for MCP SSE endpoint or /healthz for health check"},
            status_code=406,
        )

    # Get MCP ASGI app
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    # Create Starlette app for non-MCP routes
    starlette_app = Starlette(
        routes=[
            Route("/", root),
            Route("/healthz", healthz),
        ],
        lifespan=lifespan,
    )

    # Combined ASGI app - MCP app handles /mcp path internally
    async def combined_app(scope, receive, send):
        path = scope.get("path", "/")
        if path.startswith("/mcp"):
            await mcp_app(scope, receive, send)
        else:
            await starlette_app(scope, receive, send)

    port = int(os.getenv("PORT", "8080"))
    log(f"Starting server on port {port}")
    uvicorn.run(combined_app, host="0.0.0.0", port=port, lifespan="on")

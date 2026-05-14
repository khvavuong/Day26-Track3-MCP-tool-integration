from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    class FastMCP:  # pragma: no cover - fallback for local offline test environments
        def __init__(self, _name: str):
            self._name = _name

        def tool(self, name: str | None = None):
            def decorator(fn):
                return fn

            return decorator

        def resource(self, _uri: str):
            def decorator(fn):
                return fn

            return decorator

        def run(self):
            raise RuntimeError(
                "fastmcp is not installed. Install dependencies from requirements.txt to run MCP server."
            )

from db import SQLiteAdapter, ValidationError
from init_db import DEFAULT_DB_PATH, create_database

mcp = FastMCP("SQLite Lab MCP Server")

DB_PATH = Path(DEFAULT_DB_PATH)
if not DB_PATH.exists():
    create_database(DB_PATH)

adapter = SQLiteAdapter(DB_PATH)


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        raise ValueError(f"ValidationError: {exc}") from exc
    raise RuntimeError(f"ServerError: {exc}") from exc


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    try:
        return adapter.search(
            table=table,
            filters=filters,
            columns=columns,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except Exception as exc:
        _handle_error(exc)


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    try:
        return adapter.insert(table=table, values=values)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except Exception as exc:
        _handle_error(exc)


@mcp.resource("schema://database")
def database_schema() -> str:
    try:
        return json.dumps(adapter.database_schema(), indent=2)
    except Exception as exc:
        _handle_error(exc)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    try:
        payload = {table_name: adapter.get_table_schema(table_name)}
        return json.dumps(payload, indent=2)
    except Exception as exc:
        _handle_error(exc)


if __name__ == "__main__":
    mcp.run()

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from init_db import DEFAULT_DB_PATH

ALLOWED_OPERATORS = {"=", "!=", ">", ">=", "<", "<=", "like", "in"}
ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetchall_dict(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def list_tables(self) -> list[str]:
        rows = self._fetchall_dict(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name ASC
            """
        )
        return [row["name"] for row in rows]

    def _assert_table(self, table: str) -> None:
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table: {table}")

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._assert_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [dict(row) for row in rows]

    def _table_columns(self, table: str) -> set[str]:
        return {c["name"] for c in self.get_table_schema(table)}

    def _assert_columns(self, table: str, columns: list[str]) -> None:
        valid_columns = self._table_columns(table)
        unknown = [c for c in columns if c not in valid_columns]
        if unknown:
            raise ValidationError(f"Unknown column(s) for {table}: {', '.join(unknown)}")

    def _build_filters(self, table: str, filters: list[dict[str, Any]] | None) -> tuple[str, list[Any]]:
        if not filters:
            return "", []

        where_parts: list[str] = []
        params: list[Any] = []

        for idx, f in enumerate(filters):
            if not isinstance(f, dict):
                raise ValidationError(f"Filter at index {idx} must be an object")

            column = f.get("column")
            operator = str(f.get("operator", "=")).lower()
            value = f.get("value")

            if not column:
                raise ValidationError(f"Filter at index {idx} missing 'column'")
            self._assert_columns(table, [column])

            if operator not in ALLOWED_OPERATORS:
                raise ValidationError(f"Unsupported operator: {operator}")

            if operator == "in":
                if not isinstance(value, list) or len(value) == 0:
                    raise ValidationError("Operator 'in' requires a non-empty list value")
                placeholders = ", ".join(["?"] * len(value))
                where_parts.append(f"{column} IN ({placeholders})")
                params.extend(value)
            elif operator == "like":
                where_parts.append(f"{column} LIKE ?")
                params.append(value)
            else:
                where_parts.append(f"{column} {operator} ?")
                params.append(value)

        return " WHERE " + " AND ".join(where_parts), params

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._assert_table(table)

        if limit <= 0 or limit > 200:
            raise ValidationError("limit must be in range 1..200")
        if offset < 0:
            raise ValidationError("offset must be >= 0")

        if columns is None:
            select_clause = "*"
        else:
            if len(columns) == 0:
                raise ValidationError("columns must not be empty when provided")
            self._assert_columns(table, columns)
            select_clause = ", ".join(columns)

        if order_by is not None:
            self._assert_columns(table, [order_by])
            order_clause = f" ORDER BY {order_by} {'DESC' if descending else 'ASC'}"
        else:
            order_clause = ""

        where_clause, params = self._build_filters(table, filters)

        sql = (
            f"SELECT {select_clause} FROM {table}"
            f"{where_clause}{order_clause} LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        rows = self._fetchall_dict(sql, params)

        return {
            "table": table,
            "rows": rows,
            "count_returned": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._assert_table(table)

        if not isinstance(values, dict) or not values:
            raise ValidationError("values must be a non-empty object")

        columns = list(values.keys())
        self._assert_columns(table, columns)

        placeholders = ", ".join(["?"] * len(columns))
        col_sql = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"

        with self.connect() as conn:
            cur = conn.execute(sql, [values[c] for c in columns])
            conn.commit()
            inserted_id = cur.lastrowid

        payload = dict(values)
        if inserted_id is not None:
            payload["id"] = inserted_id

        return {"table": table, "inserted": payload}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._assert_table(table)

        metric_lc = metric.lower()
        if metric_lc not in ALLOWED_METRICS:
            raise ValidationError(f"Unsupported metric: {metric}")

        if metric_lc == "count":
            metric_expr = "COUNT(*) AS value"
        else:
            if not column:
                raise ValidationError(f"metric '{metric_lc}' requires a column")
            self._assert_columns(table, [column])
            metric_expr = f"{metric_lc.upper()}({column}) AS value"

        group_clause = ""
        select_group = ""
        if group_by:
            self._assert_columns(table, [group_by])
            select_group = f"{group_by}, "
            group_clause = f" GROUP BY {group_by}"

        where_clause, params = self._build_filters(table, filters)

        sql = f"SELECT {select_group}{metric_expr} FROM {table}{where_clause}{group_clause}"
        rows = self._fetchall_dict(sql, params)

        return {
            "table": table,
            "metric": metric_lc,
            "column": column,
            "group_by": group_by,
            "rows": rows,
        }

    def database_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {}
        for table in self.list_tables():
            schema[table] = self.get_table_schema(table)
        return schema

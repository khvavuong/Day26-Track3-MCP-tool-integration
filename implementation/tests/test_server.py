from __future__ import annotations

import pytest

from db import SQLiteAdapter, ValidationError
from init_db import create_database
from mcp_server import aggregate as tool_aggregate
from mcp_server import database_schema as resource_database_schema
from mcp_server import insert as tool_insert
from mcp_server import search as tool_search
from mcp_server import table_schema as resource_table_schema


@pytest.fixture(scope="module")
def adapter() -> SQLiteAdapter:
    db_path = create_database()
    return SQLiteAdapter(db_path)


def test_search_with_filter_order_pagination(adapter: SQLiteAdapter):
    out = adapter.search(
        table="students",
        columns=["id", "full_name", "cohort"],
        filters=[{"column": "cohort", "operator": "=", "value": "A1"}],
        order_by="id",
        descending=False,
        limit=2,
        offset=1,
    )
    assert out["count_returned"] == 2
    assert out["rows"][0]["id"] < out["rows"][1]["id"]


def test_insert_returns_payload(adapter: SQLiteAdapter):
    out = adapter.insert(
        table="students",
        values={"full_name": "Nina Vu", "cohort": "A2", "age": 24},
    )
    assert out["inserted"]["full_name"] == "Nina Vu"
    assert out["inserted"]["id"] > 0


def test_aggregate_metrics(adapter: SQLiteAdapter):
    for metric in ["count", "avg", "sum", "min", "max"]:
        kwargs = {"table": "enrollments", "metric": metric}
        if metric != "count":
            kwargs["column"] = "score"
        out = adapter.aggregate(**kwargs)
        assert len(out["rows"]) >= 1


def test_aggregate_group_by(adapter: SQLiteAdapter):
    out = adapter.aggregate(
        table="students", metric="avg", column="age", group_by="cohort"
    )
    assert len(out["rows"]) >= 2


def test_schema_resources(adapter: SQLiteAdapter):
    db_schema = adapter.database_schema()
    table_schema = adapter.get_table_schema("students")
    assert "students" in db_schema
    assert any(c["name"] == "full_name" for c in table_schema)


def test_invalid_table_rejected(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(table="x_not_found")


def test_invalid_column_rejected(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(table="students", columns=["bad_column"])


def test_invalid_operator_rejected(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.search(
            table="students",
            filters=[{"column": "cohort", "operator": "contains", "value": "A"}],
        )


def test_invalid_aggregate_rejected(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.aggregate(table="students", metric="median", column="age")


def test_empty_insert_rejected(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError):
        adapter.insert(table="students", values={})


def test_mcp_tool_search():
    out = tool_search(table="students", limit=1)
    assert out["count_returned"] == 1


def test_mcp_tool_insert():
    out = tool_insert(table="students", values={"full_name": "Lan Pham", "cohort": "A9", "age": 21})
    assert out["inserted"]["id"] > 0


def test_mcp_tool_aggregate():
    out = tool_aggregate(table="students", metric="count")
    assert out["rows"][0]["value"] >= 1


def test_mcp_resources_callable():
    db_payload = resource_database_schema()
    student_payload = resource_table_schema("students")
    assert "students" in db_payload
    assert "full_name" in student_payload

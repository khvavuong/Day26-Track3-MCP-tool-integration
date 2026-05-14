from __future__ import annotations

from db import SQLiteAdapter, ValidationError
from init_db import create_database


def check(name: str, fn):
    try:
        fn()
        print(f"[PASS] {name}")
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")


def main() -> None:
    db_path = create_database()
    adapter = SQLiteAdapter(db_path)

    check("server foundation: tables exist", lambda: assert_tables(adapter))
    check("tool/search: filters + ordering + pagination", lambda: assert_search(adapter))
    check("tool/insert: success", lambda: assert_insert(adapter))
    check("tool/aggregate: count", lambda: assert_aggregate_count(adapter))
    check("tool/aggregate: avg + group_by", lambda: assert_aggregate_group(adapter))
    check("resource/schema://database", lambda: assert_schema_database(adapter))
    check("resource/schema://table/{table_name}", lambda: assert_schema_table(adapter))
    check("error: unknown table rejected", lambda: assert_unknown_table(adapter))
    check("error: unknown column rejected", lambda: assert_unknown_column(adapter))
    check("error: unsupported operator rejected", lambda: assert_bad_operator(adapter))
    check("error: invalid aggregate rejected", lambda: assert_bad_metric(adapter))
    check("error: empty insert rejected", lambda: assert_empty_insert(adapter))


def assert_tables(adapter: SQLiteAdapter) -> None:
    tables = adapter.list_tables()
    assert set(tables) == {"students", "courses", "enrollments"}


def assert_search(adapter: SQLiteAdapter) -> None:
    out = adapter.search(
        table="students",
        columns=["id", "full_name", "cohort"],
        filters=[{"column": "cohort", "operator": "=", "value": "A1"}],
        order_by="id",
        descending=True,
        limit=2,
        offset=0,
    )
    assert out["count_returned"] == 2
    assert out["rows"][0]["id"] > out["rows"][1]["id"]


def assert_insert(adapter: SQLiteAdapter) -> None:
    out = adapter.insert(
        table="students",
        values={"full_name": "Foo Bar", "cohort": "C3", "age": 23},
    )
    assert out["inserted"]["id"] > 0


def assert_aggregate_count(adapter: SQLiteAdapter) -> None:
    out = adapter.aggregate(table="enrollments", metric="count")
    assert out["rows"][0]["value"] >= 1


def assert_aggregate_group(adapter: SQLiteAdapter) -> None:
    out = adapter.aggregate(
        table="students",
        metric="avg",
        column="age",
        group_by="cohort",
    )
    assert len(out["rows"]) >= 2


def assert_schema_database(adapter: SQLiteAdapter) -> None:
    schema = adapter.database_schema()
    assert "students" in schema
    assert "courses" in schema


def assert_schema_table(adapter: SQLiteAdapter) -> None:
    schema = adapter.get_table_schema("students")
    assert any(c["name"] == "full_name" for c in schema)


def assert_unknown_table(adapter: SQLiteAdapter) -> None:
    _expect_validation_error(lambda: adapter.search(table="missing_table"))


def assert_unknown_column(adapter: SQLiteAdapter) -> None:
    _expect_validation_error(
        lambda: adapter.search(table="students", columns=["not_a_column"])
    )


def assert_bad_operator(adapter: SQLiteAdapter) -> None:
    _expect_validation_error(
        lambda: adapter.search(
            table="students",
            filters=[{"column": "cohort", "operator": "contains", "value": "A"}],
        )
    )


def assert_bad_metric(adapter: SQLiteAdapter) -> None:
    _expect_validation_error(
        lambda: adapter.aggregate(table="students", metric="median", column="age")
    )


def assert_empty_insert(adapter: SQLiteAdapter) -> None:
    _expect_validation_error(lambda: adapter.insert(table="students", values={}))


def _expect_validation_error(fn) -> None:
    try:
        fn()
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")


if __name__ == "__main__":
    main()

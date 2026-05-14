# Day26 - SQLite MCP Lab Implementation

This implementation satisfies the required rubric for:
- FastMCP server with `search`, `insert`, `aggregate`
- SQLite schema/resource exposure
- Safety validation and error handling
- Repeatable verification and tests

## 1) Setup

```bash
cd implementation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Initialize Database

```bash
python init_db.py
```

Expected output:
- `Database initialized at: .../implementation/data/lab.db`

## 3) Run MCP Server

```bash
python mcp_server.py
```

The server runs with stdio transport by default.

## 4) Rubric Verification Script

```bash
python verify_server.py
```

This script checks:
- Table/schema setup
- `search`, `insert`, `aggregate` happy paths
- Resource data availability
- Invalid table/column/operator/aggregate/insert errors

## 5) Run Automated Tests

```bash
pytest -q
```

## 6) MCP Tool Summary

### `search`
Inputs:
- `table` (str)
- `columns` (list[str] | None)
- `filters` (list[object] | None)
- `limit` (int, 1..200)
- `offset` (int, >=0)
- `order_by` (str | None)
- `descending` (bool)

### `insert`
Inputs:
- `table` (str)
- `values` (dict, must be non-empty)

### `aggregate`
Inputs:
- `table` (str)
- `metric` in `count|avg|sum|min|max`
- `column` (required except `count`)
- `filters` (optional)
- `group_by` (optional)

## 7) MCP Resources

- `schema://database`
- `schema://table/{table_name}`

## 8) Codex Client Integration Example

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.sqlite_lab]
command = "python"
args = ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

Verify:

```bash
codex mcp list
```

Then run a prompt that requires MCP usage, for example:

- "Use the `sqlite_lab` MCP server. Show top 2 students in cohort A1 by id descending."
- "Read `schema://database` from `sqlite_lab` and summarize tables."

Evidence to capture for grading:
- `codex mcp list` showing the server
- One successful tool call output
- One successful schema resource read output

## 9) Inspector (Optional but Recommended)

```bash
cd ..
mkdir -p .npm-cache
NPM_CONFIG_CACHE="$PWD/.npm-cache" npx -y @modelcontextprotocol/inspector /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py
```

Inspector checklist:
- Tools visible with schemas
- Resources visible
- Valid call succeeds
- Invalid call returns clear error

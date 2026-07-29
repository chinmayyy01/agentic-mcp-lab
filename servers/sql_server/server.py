import sqlite3
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sql-server")

DB_PATH = (Path(__file__).parent / "company.db").resolve()

def _get_connection() -> sqlite3.Connection:
    """Opens a fresh connection to the sandboxed database file."""
    return sqlite3.connect(DB_PATH)

@mcp.tool()
def list_tables() -> str:
    """
    Lists all tables in the database. Use this first to discover what
    data is available before querying or describing a specific table.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master where type='table';")
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return "No tables found in the database."

    table_names = [row[0] for row in rows]
    return "\n".join(table_names)

@mcp.tool()
def describe_table(table_name: str) -> str:
    """
    Describes the schema of a specific table: column names, types,
    and whether each column is nullable. Use list_tables first to see
    valid table names.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        )
        if cur.fetchone() is None:
            return f"Error: table '{table_name}' does not exist. Use list_tables to see valid options."

        cur.execute(f"PRAGMA table_info({table_name});")
        columns = cur.fetchall()
    finally:
        conn.close()

    lines = [f"Schema for table '{table_name}':"]
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, is_pk = col
        nullable = "NOT NULL" if not_null else "NULLABLE"
        pk_marker = " [PRIMARY KEY]" if is_pk else ""
        lines.append(f"  - {col_name}: {col_type} ({nullable}){pk_marker}")

    return "\n".join(lines)

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
}

MAX_ROWS = 100

def _validate_query_is_safe(query: str) -> str | None:
    """
    Checks a SQL query for obviously destructive or write operations.
    Returns an error message string if unsafe, or None if it looks safe.
    """
    stripped = query.strip().rstrip(";")

    if ";" in stripped:
        return "Only a single SQL statement is allowed per call (no chained statements)."
    if not stripped.upper().startswith("SELECT"):
        return "Only SELECT queries are allowed. This tool is strictly read only."

    tokens = re.findall(r"[A-Za-z_]+", stripped.upper())
    found_forbidden = FORBIDDEN_KEYWORDS.intersection(tokens)
    if found_forbidden:
        return f"Query contains forbidden keyword(s): {', '.join(found_forbidden)}. This tool is strictly read-only."

    return None

@mcp.tool()
def run_query(query: str) -> str:
    """
    Executes a read only SQL SELECT query against the database and
    returns the results. Only SELECT statements are permitted — any
    write, delete, or schema altering query will be rejected. Results
    are automatically limited to 100 rows. Use list_tables and
    describe_table first to understand the schema before writing a query.
    """
    error = _validate_query_is_safe(query)
    if error:
        return f"Error: {error}"

    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query)

        column_names = [description[0] for description in cur.description]
        rows = cur.fetchmany(MAX_ROWS)
    except sqlite3.Error as e:
        return f"SQL error: {e}"
    finally:
        conn.close()

    if not rows:
        return "Query executed successfully but returned no rows."

    lines = [" | ".join(column_names)]
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(value) for value in row))

    result = "\n".join(lines)
    if len(rows) == MAX_ROWS:
        result += f"\n\n(Results truncated to {MAX_ROWS} rows.)"

    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
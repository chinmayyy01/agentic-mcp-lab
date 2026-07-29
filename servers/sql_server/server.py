import sqlite3
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
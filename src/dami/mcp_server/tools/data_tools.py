"""Tools to discover and inspect the tables of DaMi's database."""

from datetime import datetime

import pandas as pd
from mcp.types import ToolAnnotations

from dami.core.data import catalog, load_table, numeric_columns, table_path

# Tool annotations: hints for MCP clients (for example, to auto-approve read-only tools).
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def register(mcp) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def list_tables() -> dict:
        """List all tables in the user's database, with a short description of each.

        Use this first when the user mentions data that you have not seen yet.
        """
        try:
            tables = []
            for name, info in catalog().items():
                path = table_path(name)
                rows = len(pd.read_csv(path)) if path.exists() else 0
                tables.append(
                    {
                        "table": name,
                        "description": info.get("description", ""),
                        "columns": list((info.get("columns") or {}).keys()),
                        "rows": rows,
                        "notes": info.get("notes", ""),
                    }
                )
            return {"database": "analytics_db", "tables": tables, "checked_at": datetime.now().isoformat()}
        except Exception as e:
            return {"error": f"Failed to list tables: {e}"}

    @mcp.tool(annotations=READ_ONLY)
    def describe_table(table: str) -> dict:
        """Describe one table: its columns, their meaning, basic statistics and a few sample rows.

        Args:
            table: Name of the table, as returned by list_tables (for example "customers").
        """
        try:
            df = load_table(table)
            info = catalog()[table]
            stats = df[numeric_columns(df)].describe().round(3).to_dict()
            return {
                "table": table,
                "rows": len(df),
                "columns": info.get("columns", {}),
                "statistics": stats,
                "sample_rows": df.head(5).to_dict(orient="records"),
                "notes": info.get("notes", ""),
            }
        except Exception as e:
            return {"error": f"Failed to describe table: {e}"}

    @mcp.tool(annotations=READ_ONLY)
    def get_table_info(table: str) -> dict:
        """Get information about a table.

        Args:
            table: the table
        """
        try:
            df = load_table(table)
            return {"table": table, "columns": list(df.columns), "rows": len(df), "connection_status": "Connected"}
        except Exception as e:
            return {"error": str(e)}

"""Older helper tools from the first version of DaMi."""

import os

from mcp.types import ToolAnnotations

from dami.config import get_settings

# Tool annotations: hints for MCP clients (for example, to auto-approve read-only tools).
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def register(mcp) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def get_workspace_paths() -> dict:
        """Get the absolute paths of the workspace folders. Call this before you save or read any file."""
        s = get_settings()
        for d in (s.workspace_dir, s.plots_dir, s.results_dir):
            d.mkdir(parents=True, exist_ok=True)
        return {
            "workspace": str(s.workspace_dir),
            "plots": str(s.plots_dir),
            "results": str(s.results_dir),
            "data": str(s.data_dir),
        }

    @mcp.tool(annotations=READ_ONLY)
    def list_csv_files_in(directory: str) -> dict:
        """List all CSV files in a directory.

        Args:
            directory: Directory to search for CSV files
        """
        if not os.path.isdir(directory):
            return {"error": f"Directory not found: {directory}"}
        return {"files": sorted(f for f in os.listdir(directory) if f.endswith(".csv"))}

    @mcp.tool(annotations=READ_ONLY)
    def add(a: int, b: int) -> int:
        """Add two numbers.

        Args:
            a: the first number
            b: the second number
        """
        return a + b

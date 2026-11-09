"""Plotting tools. Each tool saves a PNG file and returns its path."""

import os
from pathlib import Path

from dami.config import get_settings
from dami.core import plotting
from dami.core.data import load_result, load_table, numeric_columns


def register(mcp) -> None:
    @mcp.tool()
    def plot_table(table: str, title: str | None = None, save_path: str | None = None) -> dict:
        """Draw a scatter plot of a table and save it as a PNG image.

        Args:
            table: Name of the table to plot.
            title: Title of the plot.
            save_path: Where to save the image. If empty, a file in the plots folder is used.
        """
        try:
            df = load_table(table)
            x, y = numeric_columns(df)[:2]

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            if not save_path:
                save_path = str(get_settings().plots_dir / f"{table}_scatter.png")

            path = plotting.scatter(df, x, y, title or f"{table}", save_path=Path(save_path))
            return {"saved_to": str(path.resolve()), "points": len(df), "x": x, "y": y}
        except Exception as e:
            return {"error": f"Plot failed: {e}"}

    @mcp.tool()
    def plot_clusters(result_id: str, title: str | None = None) -> dict:
        """Draw the clusters of a clustering result (from kmeans or dbscan) and save the image.

        Args:
            result_id: The result_id returned by a clustering tool.
            title: Title of the plot.
        """
        try:
            df = load_result(result_id)
            x, y = [c for c in numeric_columns(df) if c != "cluster"][:2]
            path = plotting.clusters(
                df, x, y, df["cluster"].to_numpy(), title or result_id,
                save_path=get_settings().plots_dir / f"{result_id}.png",
            )
            return {"saved_to": str(path.resolve()), "result_id": result_id}
        except Exception as e:
            return {"error": f"Plot failed: {e}"}

    @mcp.tool()
    def plot_outliers(result_id: str, title: str | None = None) -> dict:
        """Draw the outliers of an outlier-detection result and save the image.

        Args:
            result_id: The result_id returned by an outlier-detection tool.
            title: Title of the plot.
        """
        try:
            df = load_result(result_id)
            x, y = [c for c in numeric_columns(df) if c not in ("cluster", "is_outlier")][:2]
            path = plotting.outliers(
                df, x, y, df["is_outlier"].astype(bool).to_numpy(), title or result_id,
                save_path=get_settings().plots_dir / f"{result_id}.png",
            )
            return {"saved_to": str(path.resolve()), "outliers": int(df["is_outlier"].sum())}
        except Exception as e:
            return {"error": f"Plot failed: {e}"}

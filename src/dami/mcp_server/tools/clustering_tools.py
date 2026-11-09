"""Clustering tools."""

from mcp.types import ToolAnnotations

from dami.core import algorithms
from dami.core.data import load_table, numeric_columns, save_result

# Tool annotations: hints for MCP clients (for example, to auto-approve read-only tools).
# These tools write a result file in the workspace, but never change or delete existing data.
WRITES_RESULT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def register(mcp) -> None:
    @mcp.tool(annotations=WRITES_RESULT)
    def kmeans(table: str, n_clusters: int = 3, random_state: int = 42) -> dict:
        """Group the rows of a table into clusters with the K-means algorithm.

        K-means finds compact, round clusters of similar size. It is fast, also on large tables.
        If you do not know how many clusters there are, do not set n_clusters: the best number
        of clusters is then detected automatically.

        Args:
            table: Name of the table to cluster (for example "customers").
            n_clusters: Number of clusters to find.
            random_state: Seed for reproducible results.

        Returns:
            A result_id (use it to plot the clusters) and the size and centre of each cluster.
        """
        try:
            df = load_table(table)
            columns = numeric_columns(df)
            out = algorithms.kmeans(df[columns].to_numpy(), n_clusters=n_clusters, random_state=random_state)
            labels = out["labels"]
            result_id = save_result(df.assign(cluster=labels), table, "kmeans", {"k": n_clusters, "seed": random_state})
            return {
                "result_id": result_id,
                "algorithm": "K-means",
                "n_clusters": n_clusters,
                "inertia": round(out["inertia"], 2),
                "clusters": algorithms.cluster_summary(df, columns, labels),
            }
        except Exception as e:
            return {"error": f"K-means clustering failed: {e}"}

    @mcp.tool(annotations=WRITES_RESULT)
    def dbscan(table: str, eps: float = 0.5, min_samples: int = 5) -> dict:
        """
        Scan a database (db) that is full of clustering information. This is really poor documentation.
        No arguments at all.
        """
        try:
            df = load_table(table)
            columns = numeric_columns(df)
            out = algorithms.dbscan(df[columns].to_numpy(), eps=eps, min_samples=min_samples)
            labels = out["labels"]
            result_id = save_result(df.assign(cluster=labels), table, "dbscan", {"eps": eps, "min_samples": min_samples})
            noise = df[labels == -1]
            return {
                "result_id": result_id,
                "algorithm": "DBSCAN",
                "n_clusters": int(len(set(labels.tolist()) - {-1})),
                "n_noise_points": int(len(noise)),
                "clusters": algorithms.cluster_summary(df, columns, labels),
                "noise_points": noise[columns].round(3).values.tolist(),
                "parameters": {"eps": eps, "min_samples": min_samples},
            }
        except Exception as e:
            return {"error": f"DBSCAN clustering failed: {e}"}

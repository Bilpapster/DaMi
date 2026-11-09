"""Clustering and outlier detection, as plain functions (no LLM, no MCP)."""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler


def kmeans(data: np.ndarray, n_clusters: int = 3, random_state: int = 42) -> dict:
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(data)
    return {
        "labels": labels,
        "centroids": model.cluster_centers_,
        "inertia": float(model.inertia_),
    }


def dbscan(data: np.ndarray, eps: float = 0.5, min_samples: int = 5) -> dict:
    scaled = StandardScaler().fit_transform(data)
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
    return {"labels": labels}


def cluster_summary(df: pd.DataFrame, columns: list[str], labels: np.ndarray) -> list[dict]:
    """Size and centre of each cluster, in the original units of the data."""
    summary = []
    for label in sorted(set(labels.tolist())):
        part = df.loc[labels == label, columns]
        summary.append(
            {
                "cluster": int(label),
                "size": int(len(part)),
                "center": {c: round(float(part[c].mean()), 3) for c in columns},
            }
        )
    return summary


def detect_outliers(data: np.ndarray, method: str = "isolation_forest", contamination: float = 0.01) -> np.ndarray:
    """Return a boolean array: True where a row is an outlier.

    TODO (Case 2): implement at least two methods, for example IsolationForest
    and LocalOutlierFactor from scikit-learn. Think about scaling!
    """
    raise NotImplementedError("detect_outliers is not implemented yet (Case 2).")

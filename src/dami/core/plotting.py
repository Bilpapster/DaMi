"""Matplotlib helpers that save plots as PNG files."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window: we only save files
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def _finish(ax, title: str | None, xlabel: str, ylabel: str, save_path: Path) -> Path:
    ax.set_title(title or "", fontsize=14, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()
    return save_path


def scatter(df: pd.DataFrame, x: str, y: str, title: str | None, save_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df[x], df[y], s=6, alpha=0.5, c="#3b6ea5", linewidths=0)
    return _finish(ax, title, x, y, save_path)


def clusters(df: pd.DataFrame, x: str, y: str, labels: np.ndarray, title: str | None, save_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 6))
    unique = sorted(set(labels.tolist()))
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(unique), 1)))
    for color, label in zip(colors, unique):
        part = df[labels == label]
        ax.scatter(part[x], part[y], s=6, alpha=0.6, color=color, label=f"Cluster {label}", linewidths=0)
        ax.scatter(part[x].mean(), part[y].mean(), marker="x", s=150, c="black", linewidths=3)
    ax.legend(markerscale=3, fontsize=8)
    return _finish(ax, title, x, y, save_path)


def outliers(df: pd.DataFrame, x: str, y: str, is_outlier: np.ndarray, title: str | None, save_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 6))
    normal, odd = df[~is_outlier], df[is_outlier]
    ax.scatter(normal[x], normal[y], s=6, alpha=0.4, c="#3b6ea5", label="normal", linewidths=0)
    ax.scatter(odd[x], odd[y], s=30, marker="X", c="#d62728", label=f"outlier ({len(odd)})")
    ax.legend(markerscale=2)
    return _finish(ax, title, x, y, save_path)

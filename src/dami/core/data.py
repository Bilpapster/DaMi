"""Plain Python functions to read DaMi's "database" and to store analysis results.

Nothing in `dami.core` knows about LLMs or MCP. You can call these functions from
a notebook or a test, which makes them easy to check.
"""

import hashlib
from pathlib import Path

import pandas as pd
import yaml

from dami.config import get_settings


def catalog() -> dict:
    """Return the table catalog (data/catalog.yaml) as a dict."""
    path = get_settings().data_dir / "catalog.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def table_path(table: str) -> Path:
    return get_settings().data_dir / f"{table}.csv"


def load_table(table: str) -> pd.DataFrame:
    """Load a table by name. Raises a clear error if it does not exist."""
    known = catalog()
    if table not in known:
        raise KeyError(f"Unknown table '{table}'. Known tables: {sorted(known)}")
    path = table_path(table)
    if not path.exists():
        raise FileNotFoundError(f"Table '{table}' is in the catalog, but {path} does not exist.")
    return pd.read_csv(path)


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def save_result(df: pd.DataFrame, table: str, method: str, params: dict) -> str:
    """Save a result table (the data plus label columns) and return its result_id."""
    key = f"{table}|{method}|{sorted(params.items())}"
    short = hashlib.sha1(key.encode()).hexdigest()[:6]
    result_id = f"{table}-{method}-{short}"
    results_dir = get_settings().results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_dir / f"{result_id}.csv", index=False)
    return result_id


def load_result(result_id: str) -> pd.DataFrame:
    path = get_settings().results_dir / f"{result_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No result with id '{result_id}'. Run a clustering tool first.")
    return pd.read_csv(path)

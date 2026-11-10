"""The deterministic evaluator of Step 6 (no LLM): clean -> fixed outlier detector -> F1 on hidden labels.

The detector never changes (IsolationForest on the standardized sensor columns), so the only way to a
better score is better data. Scores are reported relative to "no cleaning", like s = r - r0 in LLM-AutoDP.

Rules that make cheating useless:
- The score is computed on the ORIGINAL row ids. A row that a plan drops counts as "not flagged":
  dropping a real anomaly is a miss.
- Rows that still have missing values cannot go into the detector, so they also count as "not flagged".
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

from dami.config import get_settings
from dami.duo.cleaning import CleaningPlan, apply_plan

FEATURES = ["temperature_c", "pressure_kpa", "vibration_mm_s", "power_kw"]
CONTAMINATION = 0.01


def table_dir() -> Path:
    return get_settings().data_dir / "duo"


def load_table(name: str = "factory_line") -> pd.DataFrame:
    return pd.read_csv(table_dir() / f"{name}.csv")


def _load_labels(name: str) -> pd.Series:
    labels = pd.read_csv(table_dir() / f"{name}.labels.csv")
    return labels.set_index("row_id")["is_anomaly"].astype(bool)


@dataclass
class Score:
    f1: float
    precision: float
    recall: float
    rows_in: int
    rows_scored: int


def detect(df: pd.DataFrame) -> pd.Series:
    """The fixed detector: returns flagged row_ids (a row is flagged if any of its copies is flagged)."""
    usable = df.dropna(subset=FEATURES)
    if len(usable) < 50:
        return pd.Series(dtype=bool)
    x = StandardScaler().fit_transform(usable[FEATURES].to_numpy())
    flags = IsolationForest(contamination=CONTAMINATION, n_estimators=200, random_state=0).fit_predict(x) == -1
    return pd.Series(flags, index=usable["row_id"].to_numpy()).groupby(level=0).any()


def score_frame(df: pd.DataFrame, name: str = "factory_line") -> Score:
    truth = _load_labels(name)
    flagged = detect(df).reindex(truth.index, fill_value=False)
    y, p = truth.to_numpy(), flagged.to_numpy()
    return Score(f1=round(float(f1_score(y, p, zero_division=0)), 4),
                 precision=round(float(precision_score(y, p, zero_division=0)), 4),
                 recall=round(float(recall_score(y, p, zero_division=0)), 4),
                 rows_in=len(df), rows_scored=int(df.dropna(subset=FEATURES)["row_id"].nunique()))


def score_plan(plan: CleaningPlan, name: str = "factory_line") -> tuple[Score, Score]:
    """Return (score of the cleaned table, score of the raw table = the baseline)."""
    raw = load_table(name)
    return score_frame(apply_plan(raw, plan), name), score_frame(raw, name)


if __name__ == "__main__":  # quick check: python -m dami.duo.evaluate
    base = score_frame(load_table())
    print("baseline (no cleaning):", base)
    print("anomaly share:", np.round(_load_labels("factory_line").mean(), 4))

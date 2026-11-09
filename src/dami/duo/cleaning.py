"""The cleaning vocabulary: a small, closed set of operations that a cleaning plan can use.

A plan is an ordered list of steps, for example:

    [{"op": "drop_duplicates"},
     {"op": "linear_fix", "column": "temperature_c", "machine": "M3", "multiply": 0.5556, "add": -17.78}]

Order matters (as in the LLM-AutoDP paper): for example, mark stuck values as missing
BEFORE you fill missing values. Every operation is plain pandas: no LLM writes code here.
"""

from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

OpName = Literal["drop_duplicates", "linear_fix", "fill_missing", "mark_stuck_as_missing",
                 "swap_columns_where", "clip", "drop_rows_where"]


class Step(BaseModel):
    op: OpName
    column: str | None = Field(None, description="Column to change (not for drop_duplicates).")
    machine: str | None = Field(None, description="Only rows of this machine (e.g. 'M3'). Empty = all rows.")
    multiply: float | None = Field(None, description="linear_fix: new = old * multiply + add.")
    add: float | None = Field(None, description="linear_fix: new = old * multiply + add.")
    only_below: float | None = Field(None, description="linear_fix/drop_rows_where: only rows where column < this.")
    only_above: float | None = Field(None, description="linear_fix/drop_rows_where: only rows where column > this.")
    method: Literal["median", "mean", "zero"] | None = Field(None, description="fill_missing: how to fill.")
    min_run: int | None = Field(None, description="mark_stuck_as_missing: at least this many equal values in a row.")
    other_column: str | None = Field(None, description="swap_columns_where: swap with this column where column > other_column.")
    low: float | None = Field(None, description="clip: lower bound.")
    high: float | None = Field(None, description="clip: upper bound.")


class CleaningPlan(BaseModel):
    steps: list[Step] = Field(default_factory=list, description="Ordered steps; an empty list means 'no cleaning'.")
    rationale: str = Field("", description="Why these steps, in 1-3 sentences.")


def _rows(df: pd.DataFrame, step: Step) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    if step.machine:
        mask &= df["machine"] == step.machine
    if step.column and step.only_below is not None:
        mask &= df[step.column] < step.only_below
    if step.column and step.only_above is not None:
        mask &= df[step.column] > step.only_above
    return mask


def apply_step(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    df = df.copy()
    if step.op != "drop_duplicates" and step.column not in df.columns:
        raise ValueError(f"{step.op}: unknown column '{step.column}'. Columns: {list(df.columns)}")
    if step.op == "drop_duplicates":
        return df.drop_duplicates()
    if step.op == "linear_fix":
        rows = _rows(df, step)
        df.loc[rows, step.column] = df.loc[rows, step.column] * (step.multiply if step.multiply is not None else 1) + (step.add or 0)
        return df
    if step.op == "fill_missing":
        method = step.method or "median"
        value = {"median": df[step.column].median(), "mean": df[step.column].mean(), "zero": 0.0}[method]
        df[step.column] = df[step.column].fillna(value)
        return df
    if step.op == "mark_stuck_as_missing":
        min_run = step.min_run or 5
        for _, part in df.groupby("machine") if "machine" in df else [(None, df)]:
            part = part.sort_values("minute") if "minute" in part else part
            values = part[step.column]
            run_id = (values != values.shift()).cumsum()
            run_len = values.groupby(run_id).transform("size")
            df.loc[run_len[run_len >= min_run].index, step.column] = np.nan
        return df
    if step.op == "swap_columns_where":
        if step.other_column not in df.columns:
            raise ValueError(f"swap_columns_where: unknown other_column '{step.other_column}'.")
        rows = _rows(df, step) & (df[step.column] > df[step.other_column])
        df.loc[rows, [step.column, step.other_column]] = df.loc[rows, [step.other_column, step.column]].to_numpy()
        return df
    if step.op == "clip":
        df[step.column] = df[step.column].clip(step.low, step.high)
        return df
    if step.op == "drop_rows_where":
        if step.only_below is None and step.only_above is None and not step.machine:
            raise ValueError("drop_rows_where needs only_below, only_above or machine.")
        return df[~_rows(df, step)]
    raise ValueError(f"Unknown op {step.op}")


def apply_plan(df: pd.DataFrame, plan: CleaningPlan) -> pd.DataFrame:
    for i, step in enumerate(plan.steps, 1):
        try:
            df = apply_step(df, step)
        except Exception as e:  # noqa: BLE001 - tell the agent which step failed
            raise ValueError(f"step {i} ({step.op}) failed: {e}") from e
    return df

"""The exam panel of the web app: read the full answers of an exam run, grade them, and compare runs.

The grades go into the "correct" column of the exam's CSV file in runs/, so the files that
`dami exam` writes stay the single source of truth.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from dami.config import REPO_ROOT, Settings
from dami.ui import parts

GRADES = ["yes", "partly", "no"]


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _run_name(path: Path) -> str:
    return path.stem.removeprefix("exam-")


def _full_run(runs_dir: Path, run_id: str) -> dict:
    """The run as the recorder saved it: the CSV keeps only the start of the answer, the run file all of it."""
    path = runs_dir / f"{run_id}.jsonl"
    if not run_id or not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    end = next((r for r in records if r["type"] == "end"), {})
    return {"answer": end.get("answer", ""), "tools": [r for r in records if r["type"] == "tool"]}


def _grade(path: Path, row: int, key: str) -> None:
    df = _load(path)
    df.loc[row, "correct"] = st.session_state[key] or ""
    try:
        df.to_csv(path, index=False)
    except PermissionError:  # Windows locks a CSV that is open in Excel
        st.toast(f"Could not save the grade: close {path.name} in your spreadsheet program.", icon=":material/error:")


def _overview(files: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per exam run, and the grade of every question in every run."""
    rows, grades = [], []
    for path in files:
        df = _load(path)
        num = lambda column: pd.to_numeric(df[column], errors="coerce")  # noqa: E731
        rows.append({"run": _run_name(path), "answers": len(df),
                     **{grade: int((df["correct"] == grade).sum()) for grade in GRADES},
                     "not graded": int((df["correct"] == "").sum()),
                     "avg latency (s)": round(num("latency_s").mean(), 1),
                     "avg tool calls": round(num("tool_calls").mean(), 1),
                     "avg tokens": round((num("input_tokens") + num("output_tokens")).mean())})
        grades.append(df.assign(run=_run_name(path))[["run", "question", "correct"]])
    grid = pd.concat(grades).pivot_table(index="question", columns="run", values="correct", sort=False,
                                         aggfunc=lambda v: " / ".join(g or "·" for g in v))
    return pd.DataFrame(rows), grid[[_run_name(p) for p in files if _run_name(p) in grid.columns]]


def exam_panel(settings: Settings) -> None:
    # Oldest first: the file names end with the date and time of the run.
    files = sorted(settings.runs_dir.glob("exam-*.csv"), key=lambda p: p.stem[-15:])
    if not files:
        st.info("No exam runs yet. Run `dami exam --tag baseline` in a terminal first.")
        return
    questions = {q["id"]: q["question"]
                 for q in yaml.safe_load((REPO_ROOT / "exam" / "questions.yaml").read_text(encoding="utf-8"))}

    st.subheader("All exam runs")
    overview, grid = _overview(files)
    st.dataframe(overview, hide_index=True)
    st.caption("The grade of each question in every run (· = not graded yet):")
    st.dataframe(grid)

    st.subheader("Read and grade a run")
    path = st.selectbox("Exam run", files[::-1], format_func=_run_name)
    df = _load(path)
    st.caption(f"{int((df['correct'] != '').sum())} of {len(df)} answers graded. "
               f"Your grades are saved in `{path}`.")
    for i, row in df.iterrows():
        question = questions.get(row["question"], "(no longer in questions.yaml)")
        with st.expander(f"**{row['question']}** #{row['repeat']} · {row['correct'] or 'not graded'} · {question}"):
            st.markdown(f"**Question:** {question}")
            st.caption(f"{row['latency_s']} s · {row['model_calls']} model calls · {row['tool_calls']} tool calls · "
                       f"{row['input_tokens']} input / {row['output_tokens']} output tokens  \n"
                       f"Tools: {row['tools'] or '-'}")
            if row["error"]:
                st.error(row["error"])
            run = _full_run(settings.runs_dir, row["run_id"])
            with st.container(border=True):
                st.markdown(run.get("answer") or row["answer"] or "_(no answer)_")
            for image in parts.image_paths(run):
                st.image(image, width=620)
            key = f"grade-{path.name}-{i}"
            st.segmented_control("Is the answer correct?", GRADES, default=row["correct"] or None, key=key,
                                 on_change=_grade, args=(path, i, key))

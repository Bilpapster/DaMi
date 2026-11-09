"""Step 5: the driver (brain A) spawns sub-agents (brain B) that inspect the data and propose cleaning plans.

    dami duo run           # one session of the driver
    dami duo journal       # print the journal (the memory that survives sessions)

The driver never sees the data (black-box mode, as in LLM-AutoDP): it sees only the sub-agents'
proposals, the scores of the deterministic evaluator, and the journal.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

from dami.config import PACKAGE_DIR, get_settings
from dami.duo import evaluate
from dami.duo.cleaning import CleaningPlan, apply_plan
from dami.duo.journal import Journal, plan_summary
from dami.hooks.metrics import VictoriaMetricsHook
from dami.hooks.recorder import RunRecorder
from dami.model import make_model, make_model_b
from dami.telemetry import setup_tracing

TABLE = "factory_line"

SUB_AGENT_TOOLKIT = """

## Your toolkit (added by DaMi; you cannot change it)
You may inspect the table `factory_line` with your tools. Then answer with a cleaning plan: an ORDERED list
of steps. Allowed steps (all parameters are optional unless the step needs them):
- drop_duplicates
- linear_fix(column, multiply, add, machine, only_below, only_above): new = old * multiply + add, only on the chosen rows
- fill_missing(column, method = median | mean | zero)
- mark_stuck_as_missing(column, min_run): equal values repeated min_run times in a row become missing
- swap_columns_where(column, other_column, machine): swap the two values where column > other_column
- clip(column, low, high)
- drop_rows_where(column, only_below, only_above, machine)
Order matters. Explain your plan in 1-3 sentences in `rationale`.
"""


# ---------------------------------------------------------------- read-only tools of the sub-agent
@tool
def profile_table() -> str:
    """Overview of the table: row count, missing values per column, and min / median / max of each sensor per machine."""
    df = evaluate.load_table(TABLE)
    stats = df.groupby("machine")[evaluate.FEATURES].agg(["min", "median", "max"]).round(2)
    return json.dumps({"rows": len(df), "columns": list(df.columns),
                       "missing": df.isna().sum()[lambda s: s > 0].to_dict(),
                       "per_machine": {m: {c: stats.loc[m, c].to_dict() for c in evaluate.FEATURES} for m in stats.index}})


@tool
def count_duplicates() -> str:
    """Count rows that are exact copies of another row."""
    df = evaluate.load_table(TABLE)
    return json.dumps({"duplicate_rows": int(df.duplicated().sum()), "rows": len(df)})


@tool
def repeated_runs(column: str) -> str:
    """Find, per machine, the longest run of identical values in a row (by minute). Long runs can mean a stuck sensor.

    Args:
        column: A sensor column, for example "vibration_mm_s".
    """
    df = evaluate.load_table(TABLE).drop_duplicates()
    if column not in df.columns:
        return f"Unknown column '{column}'."
    out = {}
    for machine, part in df.sort_values("minute").groupby("machine"):
        values = part[column]
        run_id = (values != values.shift()).cumsum()
        sizes = values.groupby(run_id).size()
        longest = sizes.idxmax()
        rows = part[run_id == longest]
        out[machine] = {"longest_run": int(sizes.max()), "value": float(rows[column].iloc[0]),
                        "minutes": [int(rows["minute"].min()), int(rows["minute"].max())]}
    return json.dumps(out)


@tool
def rows_where(column: str, below: float | None = None, above: float | None = None, machine: str | None = None) -> str:
    """Count the rows where a column is below and/or above a value (optionally for one machine), with 5 examples.

    Args:
        column: The column to test.
        below: Keep rows where column < below.
        above: Keep rows where column > above.
        machine: Only this machine, e.g. "M2".
    """
    df = evaluate.load_table(TABLE)
    if column not in df.columns:
        return f"Unknown column '{column}'."
    mask = df[column].notna()
    if below is not None:
        mask &= df[column] < below
    if above is not None:
        mask &= df[column] > above
    if machine:
        mask &= df["machine"] == machine
    rows = df[mask]
    return json.dumps({"count": int(len(rows)), "by_machine": rows["machine"].value_counts().to_dict(),
                       "examples": rows.head(5).to_dict(orient="records")})


SUB_AGENT_TOOLS = [profile_table, count_duplicates, repeated_runs, rows_where]


# ---------------------------------------------------------------- the driver's session
@dataclass
class Session:
    name: str
    max_evaluations: int
    max_spawns: int
    journal: Journal = field(default_factory=Journal.default)
    spawns: dict = field(default_factory=dict)
    evaluations: int = 0

    def driver_tools(self) -> list:
        s = self

        @tool
        def spawn_agent(system_prompt: str, task: str) -> str:
            """Start a NEW sub-agent on the second brain. It can look at the data; you cannot.

            You write its system prompt (its role and guidance) and its task. It answers with a cleaning
            plan and a short rationale. Use the journal and earlier results to give it better guidance.

            Args:
                system_prompt: The role and guidance for the sub-agent.
                task: What it should do now.
            """
            if len(s.spawns) >= s.max_spawns:
                return f"No spawns left in this session ({s.max_spawns} used). Evaluate plans or finish."
            spawn_id = f"S{len(s.spawns) + 1}"
            settings = get_settings()
            recorder = RunRecorder(settings.runs_dir, session=f"{s.name}-{spawn_id}")
            sub = Agent(name=f"sub-agent-{spawn_id}", model=make_model_b(), tools=SUB_AGENT_TOOLS,
                        system_prompt=system_prompt + SUB_AGENT_TOOLKIT, callback_handler=None,
                        hooks=[recorder, VictoriaMetricsHook(settings, session=f"duo-sub-{s.name}")],
                        trace_attributes={"session.id": s.name, "dami.role": "sub-agent"})
            try:
                result = sub(task, structured_output_model=CleaningPlan)
                plan = result.structured_output
            except Exception as e:  # noqa: BLE001 - tell the driver what happened
                s.spawns[spawn_id] = {"system_prompt": system_prompt, "error": str(e)}
                return f"{spawn_id} failed to produce a valid plan: {type(e).__name__}: {e}"
            finally:
                sub.cleanup()
            s.spawns[spawn_id] = {"system_prompt": system_prompt, "plan": plan.model_dump(exclude_none=True)}
            steps = "\n".join(f"  {i}. {plan_summary({'steps': [st.model_dump(exclude_none=True)]})}"
                              for i, st in enumerate(plan.steps, 1)) or "  (no steps)"
            return f"{spawn_id} proposes:\n{steps}\nRationale: {plan.rationale}\nScore it with evaluate_plan('{spawn_id}')."

        @tool
        def evaluate_plan(spawn_id: str, drop_steps: list[int] | None = None) -> str:
            """Apply the plan of a sub-agent to the data and score it (outlier-detection F1, relative to no cleaning).

            Every scored plan is written into the journal automatically. A plan that was already tried is
            not scored again (and does not use your budget).

            Args:
                spawn_id: The sub-agent whose plan to score, e.g. "S1".
                drop_steps: Optional step numbers to leave out, e.g. [3] to try the plan without its step 3.
            """
            if spawn_id not in s.spawns or "plan" not in s.spawns[spawn_id]:
                return f"Unknown spawn id or no plan: {spawn_id}. Known: {list(s.spawns)}"
            plan = dict(s.spawns[spawn_id]["plan"])
            drop = set(drop_steps or [])
            plan["steps"] = [st for i, st in enumerate(plan.get("steps", []), 1) if i not in drop]
            seen = s.journal.find(plan)
            if seen:
                return f"Already tried as {seen['id']}: F1 = {seen['f1']} (Δ {seen['delta']}). Not scored again."
            if s.evaluations >= s.max_evaluations:
                return f"Evaluation budget used up ({s.max_evaluations}). Write your lessons and finish."
            s.evaluations += 1
            raw = evaluate.load_table(TABLE)
            baseline = evaluate.score_frame(raw, TABLE).f1
            try:
                score = evaluate.score_frame(apply_plan(raw, CleaningPlan(**plan)), TABLE)
            except Exception as e:  # noqa: BLE001
                trial = s.journal.add_trial(s.name, plan, None, baseline, error=str(e), sub_agent=spawn_id)
                return f"{trial['id']}: the plan failed: {e}"
            trial = s.journal.add_trial(s.name, plan, score.f1, baseline, sub_agent=spawn_id)
            best = max((t["f1"] for t in s.journal.trials() if t["f1"] is not None), default=score.f1)
            return (f"{trial['id']}: F1 = {score.f1:.3f} (precision {score.precision:.2f}, recall {score.recall:.2f}), "
                    f"Δ vs no cleaning = {trial['delta']:+.3f}. Best so far: {best:.3f}. "
                    f"Evaluations left: {s.max_evaluations - s.evaluations}.")

        @tool
        def read_journal() -> str:
            """Read the journal: the best trials of ALL sessions (best first), failures, lessons and next steps."""
            return s.journal.render()

        @tool
        def write_lesson(lesson: str) -> str:
            """Save a lesson for future sessions. It must cite trial ids, e.g. "T04 beat T02: ...".

            Args:
                lesson: One short sentence with trial ids.
            """
            return s.journal.add_lesson(s.name, lesson)

        @tool
        def remove_lesson(number: int) -> str:
            """Remove a lesson by its number in the journal (to merge lessons or drop a wrong one).

            Args:
                number: The lesson number shown in the journal.
            """
            return s.journal.remove_lesson(s.name, number)

        @tool
        def set_next_steps(steps: list[str]) -> str:
            """Save at most 3 next steps for the next session: one to explore, one to exploit, one new idea.

            Args:
                steps: The next steps.
            """
            return s.journal.set_next(s.name, steps)

        return [spawn_agent, evaluate_plan, read_journal, write_lesson, remove_lesson, set_next_steps]


MAX_NUDGES = 8  # harness: how often the driver is told to continue when it stops too early


def run_session(max_evaluations: int = 6, max_spawns: int = 4, name: str | None = None) -> Session:
    settings = get_settings()
    setup_tracing(settings)
    session = Session(name=name or f"duo-{datetime.now():%Y%m%d-%H%M%S}", max_evaluations=max_evaluations,
                      max_spawns=max_spawns)
    prompt = (PACKAGE_DIR / "prompts" / "duo_driver.md").read_text(encoding="utf-8").format(
        max_evaluations=max_evaluations, max_spawns=max_spawns)
    driver = Agent(name="driver", model=make_model(), tools=session.driver_tools(), system_prompt=prompt,
                   conversation_manager=SlidingWindowConversationManager(window_size=40), callback_handler=None,
                   hooks=[RunRecorder(settings.runs_dir, session=session.name),
                          VictoriaMetricsHook(settings, session=f"duo-driver-{session.name}")],
                   trace_attributes={"session.id": session.name, "dami.role": "driver"})
    try:
        answer = str(driver(f"Start session {session.name}. Begin by reading the journal."))
        for _ in range(MAX_NUDGES):
            # Small models often say what they will do and then stop. The harness keeps the loop going.
            left_eval = session.max_evaluations - session.evaluations
            left_spawn = session.max_spawns - len(session.spawns)
            if "FINISHED" in answer or (left_eval <= 0 and left_spawn <= 0):
                break
            print(f"   ↻ driver stopped early; nudging it ({left_eval} evaluations, {left_spawn} spawns left)")
            answer = str(driver(f"Continue now with a tool call. You have {left_eval} evaluations and {left_spawn} spawns "
                                "left. When you are done, write lessons and next steps, then answer with FINISHED."))
        print(f"\n🧭 Driver: {answer.strip()}\n")
    finally:
        driver.cleanup()
    return session

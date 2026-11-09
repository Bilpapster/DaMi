"""`dami exam`: run the fixed exam questions and write a summary table.

Each question runs in a NEW conversation, so the questions do not influence
each other. The exam does not grade the answers: you do (see the "correct" column).
"""

import csv
import time
from datetime import datetime

import yaml

from dami.agent import build_agent
from dami.config import REPO_ROOT, get_settings

QUESTIONS = REPO_ROOT / "exam" / "questions.yaml"


def run(tag: str, repeat: int = 1, only: list[str] | None = None) -> int:
    s = get_settings()
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    if only:
        questions = [q for q in questions if q["id"] in only]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = s.runs_dir / f"exam-{tag}-{stamp}.csv"
    s.runs_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"📝 DaMi exam '{tag}': {len(questions)} questions x {repeat} repeat(s), model {s.model_id}\n")

    for q in questions:
        for rep in range(1, repeat + 1):
            agent = build_agent(s, session=f"exam-{tag}")
            t = time.time()
            try:
                result = agent(q["question"])
                answer, error = str(result).strip(), ""
            except Exception as e:  # noqa: BLE001 - an exam must go on
                answer, error = "", f"{type(e).__name__}: {e}"
            took = time.time() - t
            usage = agent.event_loop_metrics.accumulated_usage
            run = agent.dami_recorder.last_run or {}
            tools = [f"{x['name']}" for x in run.get("tools", [])]
            row = {
                "tag": tag, "question": q["id"], "repeat": rep, "run_id": run.get("run_id", ""),
                "model": s.model_id, "latency_s": round(took, 1),
                "model_calls": run.get("model_calls", 0), "tool_calls": len(tools),
                "input_tokens": usage.get("inputTokens", 0), "output_tokens": usage.get("outputTokens", 0),
                "tools": " > ".join(tools), "error": error,
                "answer": answer.replace("\n", " ")[:400], "correct": "",
            }
            rows.append(row)
            print(f"{q['id']} #{rep}  {took:6.1f}s  tools: {row['tools'] or '-'}")
            print(f"     {(error or row['answer'])[:160]}\n")
            agent.cleanup()

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"📄 Summary: {out}\n   Open it, and fill the 'correct' column (yes / partly / no).")
    return 0

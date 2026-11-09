"""The experiment journal of Case 6: DaMi's long-term memory across sessions.

Two files in workspace/duo/:
- journal.jsonl: append-only facts, one line per event (trials, lessons, plans for the next steps).
- journal.md:    the view that the driver reads: best trials FIRST (sorted by score, not by time),
                 as recommended by "Self-Evolving Recommendation System" (Wang et al., 2026, Table 4).

Rules:
- Facts (scores, plans, errors) are written by the tools, never by the LLM: an LLM cannot invent a score.
- The LLM writes only lessons (each must cite trial ids, e.g. "T03") and next steps.
- The view is small on purpose (top 10 trials, last 5 failures, at most 8 lessons), so that it fits
  in the context of a small model, however many sessions you run.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dami.config import get_settings

MAX_BEST, MAX_FAILURES, MAX_LESSONS, MAX_NEXT = 10, 5, 8, 3


def fingerprint(plan: dict) -> str:
    """A short id of a plan: the same steps in the same order give the same fingerprint."""
    canonical = json.dumps(plan.get("steps", []), sort_keys=True)
    return hashlib.sha1(canonical.encode()).hexdigest()[:8]


def plan_summary(plan: dict) -> str:
    parts = []
    for step in plan.get("steps", []):
        args = ",".join(f"{k}={v}" for k, v in step.items() if k != "op" and v is not None)
        parts.append(f"{step['op']}({args})")
    return " → ".join(parts) or "(no cleaning)"


@dataclass
class Journal:
    folder: Path

    @classmethod
    def default(cls) -> "Journal":
        return cls(get_settings().workspace_dir / "duo")

    @property
    def store(self) -> Path:
        return self.folder / "journal.jsonl"

    @property
    def view(self) -> Path:
        return self.folder / "journal.md"

    # ------------------------------------------------------------------ facts
    def events(self) -> list[dict]:
        if not self.store.exists():
            return []
        return [json.loads(line) for line in self.store.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _append(self, event: dict) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        event = {"time": datetime.now().isoformat(timespec="seconds"), **event}
        with open(self.store, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        self.render()

    def trials(self) -> list[dict]:
        return [e for e in self.events() if e["type"] == "trial"]

    def find(self, plan: dict) -> dict | None:
        fp = fingerprint(plan)
        return next((t for t in self.trials() if t["fingerprint"] == fp), None)

    def add_trial(self, session: str, plan: dict, f1: float | None, baseline: float, error: str = "",
                  sub_agent: str = "") -> dict:
        trial = {"type": "trial", "id": f"T{len(self.trials()) + 1:02d}", "session": session,
                 "fingerprint": fingerprint(plan), "plan": plan, "f1": f1, "baseline": baseline,
                 "delta": None if f1 is None else round(f1 - baseline, 4), "error": error, "sub_agent": sub_agent}
        self._append(trial)
        return trial

    # ------------------------------------------------------------------ what the LLM may write
    def add_lesson(self, session: str, text: str) -> str:
        ids = re.findall(r"\bT\d{2,}\b", text)
        known = {t["id"] for t in self.trials()}
        if not ids or not set(ids) <= known:
            return "Rejected: a lesson must cite existing trial ids, for example 'T03 beat T01 because ...'."
        if len(self.lessons()) >= MAX_LESSONS:
            return (f"Rejected: the journal already has {MAX_LESSONS} lessons. First merge or remove one with "
                    "remove_lesson(number), then add the new one.")
        self._append({"type": "lesson", "session": session, "text": text.strip()})
        return "Lesson saved."

    def remove_lesson(self, session: str, number: int) -> str:
        lessons = self.lessons()
        if not 1 <= number <= len(lessons):
            return f"No lesson number {number}."
        self._append({"type": "remove_lesson", "session": session, "text": lessons[number - 1]})
        return f"Lesson {number} removed."

    def set_next(self, session: str, steps: list[str]) -> str:
        self._append({"type": "next", "session": session, "steps": [s.strip() for s in steps[:MAX_NEXT]]})
        return "Next steps saved."

    # ------------------------------------------------------------------ the view
    def lessons(self) -> list[str]:
        removed = {e["text"] for e in self.events() if e["type"] == "remove_lesson"}
        return [e["text"] for e in self.events() if e["type"] == "lesson" and e["text"] not in removed]

    def render(self) -> str:
        trials = self.trials()
        scored = sorted([t for t in trials if t["f1"] is not None], key=lambda t: (-t["f1"], t["id"]))
        failed = [t for t in trials if t["f1"] is None or (t["delta"] is not None and t["delta"] < 0)][-MAX_FAILURES:]
        baseline = trials[0]["baseline"] if trials else None
        next_steps = next((e["steps"] for e in reversed(self.events()) if e["type"] == "next"), [])
        lines = [f"# Journal: factory_line | metric: outlier F1 (higher is better) | baseline F1 = {baseline}",
                 f"{len(trials)} trials so far.", "",
                 f"## Best trials (sorted by F1, best first; top {MAX_BEST})",
                 "| rank | id | F1 | Δ vs baseline | plan |", "|---|---|---|---|---|"]
        lines += [f"| {i} | {t['id']} | {t['f1']:.3f} | {t['delta']:+.3f} | {plan_summary(t['plan'])} |"
                  for i, t in enumerate(scored[:MAX_BEST], 1)]
        lines += ["", f"## Failures and dead ends (newest last; last {MAX_FAILURES})", "| id | F1 | Δ | plan or error |",
                  "|---|---|---|---|"]
        lines += [f"| {t['id']} | {t['f1'] if t['f1'] is not None else '-'} | "
                  f"{t['delta'] if t['delta'] is not None else '-'} | {t['error'] or plan_summary(t['plan'])} |"
                  for t in failed]
        lines += ["", "## Already tried (fingerprints: do not try these plans again)",
                  ", ".join(f"{t['id']}:{t['fingerprint']}" for t in trials) or "-", "",
                  f"## Lessons (written by the driver; each cites trial ids; at most {MAX_LESSONS})"]
        lines += [f"{i}. {text}" for i, text in enumerate(self.lessons(), 1)] or ["(none yet)"]
        lines += ["", "## Next steps (written by the driver)"] + ([f"- {s}" for s in next_steps] or ["(none yet)"])
        text = "\n".join(lines) + "\n"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.view.write_text(text, encoding="utf-8")
        return text

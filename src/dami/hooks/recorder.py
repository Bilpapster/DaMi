"""The run recorder: a Strands hook that writes one JSONL file per agent run.

Every question you ask DaMi is one "run". The recorder writes what happened in
`runs/<run_id>.jsonl`: the prompt, each tool call, the token usage and the answer.
Use these files as evidence in your JOURNAL.md.
"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    HookProvider,
    HookRegistry,
)


def _text_of(content) -> str:
    parts = []
    for block in content or []:
        if isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
        elif isinstance(block, dict) and "json" in block:
            parts.append(json.dumps(block["json"]))
    return "\n".join(parts)


class RunRecorder(HookProvider):
    def __init__(self, runs_dir: Path, session: str = "chat"):
        self.runs_dir = Path(runs_dir)
        self.session = session
        self.run_id: str | None = None
        self.last_run: dict | None = None
        self._started = 0.0
        self._tools: list[dict] = []

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_start)
        registry.add_callback(AfterToolCallEvent, self.on_tool)
        registry.add_callback(AfterInvocationEvent, self.on_end)

    # --- callbacks -------------------------------------------------------
    def on_start(self, event: BeforeInvocationEvent) -> None:
        self.run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
        self._started = time.time()
        self._tools = []
        prompt = ""
        if event.messages:
            prompt = _text_of(event.messages[-1].get("content"))
        self._write({"type": "start", "session": self.session, "prompt": prompt})

    def on_tool(self, event: AfterToolCallEvent) -> None:
        output = _text_of(event.result.get("content"))
        record = {
            "type": "tool",
            "name": event.tool_use["name"],
            "input": event.tool_use.get("input"),
            "status": "error" if event.exception else "ok",
            "duration_s": round(event.duration or 0.0, 3),
            "output_chars": len(output),
            "output_preview": output[:500],
        }
        self._tools.append(record)
        self._write(record)

    def on_end(self, event: AfterInvocationEvent) -> None:
        metrics = event.agent.event_loop_metrics
        invocation = metrics.latest_agent_invocation
        calls = []
        input_tokens = output_tokens = 0
        for cycle in invocation.cycles if invocation else []:
            calls.append({"input_tokens": cycle.usage.get("inputTokens", 0), "output_tokens": cycle.usage.get("outputTokens", 0)})
            input_tokens = cycle.usage.get("inputTokens", 0)
            output_tokens = cycle.usage.get("outputTokens", 0)

        answer = ""
        if event.result is not None:
            answer = _text_of(event.result.message.get("content"))

        summary = {
            "type": "end",
            "model_calls": len(calls),
            "calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tool_calls": len(self._tools),
            "latency_s": round(time.time() - self._started, 2),
            "answer": answer,
        }
        self._write(summary)
        self.last_run = {"run_id": self.run_id, "tools": list(self._tools), **summary}

    # --- helpers ---------------------------------------------------------
    def _write(self, record: dict) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        record = {"run_id": self.run_id, "time": datetime.now().isoformat(timespec="seconds"), **record}
        with open(self.runs_dir / f"{self.run_id}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

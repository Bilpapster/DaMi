"""Building blocks of the DaMi web app: live progress, status checks and the "under the hood" panel.

The page flow is in app.py. You can change this file to show more (or other) things about DaMi.
"""

import asyncio
import copy
import json
import re
import time
from pathlib import Path

import requests
import streamlit as st
import yaml
from strands.hooks import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

from dami.config import REPO_ROOT, Settings
from dami.model import NGROK_HEADERS

LOGO = Path(__file__).parent / "logo" / "dami.png"
DAMI_AVATAR = "⛏️"
USER_AVATAR = "user"
STEPS_DIR = REPO_ROOT / "assignment_steps"


def example_prompts() -> dict[str, list[str]]:
    exam = yaml.safe_load((REPO_ROOT / "exam" / "questions.yaml").read_text(encoding="utf-8"))
    return {
        "Step 1": ["What is your name?", "What can you do for me?", "Which tables do we have?"],
        "Step 2": [q["question"] for q in exam],
        "Step 3": ["How many customer segments are there? Plot them.",
                   "Group the products into families and plot them.",
                   "Some presses act strange. Find unusual sensor readings.",
                   "Is there anything suspicious in the card transactions?"],
        "Step 4": ["Describe every table we have.", "Cluster the marketing campaigns, then plot those clusters."],
        "Step 5": ["Find outliers in the sensors table with micro-clusters.",
                   "Which clustering method fits the marketing table best, and why?",
                   "Write a short data mining report on the products table."],
    }


def assignment_steps() -> dict[str, str]:
    """The assignment steps, read from assignment_steps/ (the single source of truth): {title: markdown}.

    The files are read on every page run, so a change to a step shows at once.
    """
    def order(path: Path) -> list:
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.stem)]

    steps = {}
    for path in sorted(STEPS_DIR.glob("*.md"), key=order):
        text = path.read_text(encoding="utf-8")
        heading = text.lstrip().splitlines()[0] if text.strip() else ""
        title = re.search(r"Step\s*\d+.*", heading)
        other = re.sub(r"^#+\s*(\W+\s*)?(DaMi\s+)?", "", heading).strip()  # "# ⛏️ DaMi Exam: ..." -> "Exam: ..."
        steps[title.group(0).strip() if title else other or path.stem] = text
    return steps


# ----------------------------------------------------------------------------- live progress
class LiveProgress(HookProvider):
    """A Strands hook that shows each step of the agent loop while it happens.

    Streamlit can only draw from the thread that runs the page. `run_streaming()` runs the
    agent with `asyncio.run(agent.stream_async(...))` on that thread, so these callbacks can
    write into the status box directly. (With `agent(prompt)`, Strands runs the loop on another
    thread and Streamlit would silently ignore the writes.)
    """

    def __init__(self):
        self.box = None
        self.steps: list[dict] = []
        self.on_model_start = None
        self._lines: dict = {}  # one placeholder line per step, updated when the step ends

    def reset(self, box) -> None:
        self.box, self.steps, self._lines = box, [], {}

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeModelCallEvent, self.model_start)
        registry.add_callback(AfterModelCallEvent, self.model_end)
        registry.add_callback(BeforeToolCallEvent, self.tool_start)
        registry.add_callback(AfterToolCallEvent, self.tool_end)

    def _show(self, key, text: str) -> None:
        if self.box is None:
            return
        if key not in self._lines:
            self._lines[key] = self.box.empty()
        self._lines[key].markdown(text)

    def model_start(self, event: BeforeModelCallEvent) -> None:
        n = sum(1 for s in self.steps if s["kind"] == "model") + 1
        self.steps.append({"kind": "model", "n": n, "t0": time.time(), "estimate": event.projected_input_tokens})
        self._show(("model", n), f":material/hourglass_top: Thinking… (model call {n})")
        if self.on_model_start:
            self.on_model_start()

    def model_end(self, event: AfterModelCallEvent) -> None:
        step = next((s for s in reversed(self.steps) if s["kind"] == "model"), None)
        if step:
            step["seconds"] = round(time.time() - step["t0"], 1)
            step["stop"] = event.stop_response.stop_reason if event.stop_response else "error"
            icon = ":material/psychology:" if event.stop_response else ":material/cancel:"
            self._show(("model", step["n"]), f"{icon} Model call {step['n']} · {step['seconds']} s")

    def tool_start(self, event: BeforeToolCallEvent) -> None:
        name, args = event.tool_use["name"], event.tool_use.get("input") or {}
        tool_id = event.tool_use.get("toolUseId")
        self.steps.append({"kind": "tool", "id": tool_id, "name": name, "input": args, "t0": time.time()})
        self._show(("tool", tool_id), f":material/hourglass_top: `{name}` {json.dumps(args)[:80]}")

    def tool_end(self, event: AfterToolCallEvent) -> None:
        tool_id = event.tool_use.get("toolUseId")
        step = next((s for s in reversed(self.steps) if s["kind"] == "tool" and s.get("id") == tool_id), None)
        status = event.result.get("status", "?")
        if step:
            step["status"], step["seconds"] = status, round(event.duration or 0.0, 2)
            icon = ":material/check_circle:" if status == "success" else ":material/cancel:"
            self._show(("tool", tool_id), f"{icon} `{step['name']}` {json.dumps(step['input'])[:80]} · {step['seconds']} s")


def run_streaming(agent, live: LiveProgress, prompt: str) -> tuple[str, Exception | None]:
    """Run one question with live progress, a running clock and the answer streamed as it is written."""
    with st.status("DaMi is working…", expanded=True) as box:
        live.reset(box)
        clock, out = st.empty(), st.empty()
        text = {"now": ""}
        live.on_model_start = lambda: text.update(now="")  # each model call writes a new text

        async def run():
            t0, done, result = time.time(), asyncio.Event(), None

            async def tick():
                while not done.is_set():
                    clock.caption(f":material/timer: {time.time() - t0:.0f} s")
                    await asyncio.sleep(0.5)

            ticker = asyncio.create_task(tick())
            try:
                async for event in agent.stream_async(prompt):
                    if "data" in event:
                        text["now"] += event["data"]
                        out.markdown(text["now"] + " ▌")
                    elif "result" in event:
                        result = event["result"]
            finally:
                done.set()
                await ticker
            return result, time.time() - t0

        try:
            result, seconds = asyncio.run(run())
        except Exception as e:  # noqa: BLE001 - shown to the student with a hint
            box.update(label="DaMi could not finish this request", state="error", expanded=True)
            return "", e
        out.empty()
        steps = sum(1 for s in live.steps if s["kind"] == "model")
        box.update(label=f"Done · {seconds:.0f} s · {steps} model calls", state="complete", expanded=False)
    return str(result).strip(), None


def show_error(error: Exception) -> None:
    """Explain the most common problems, and show the full error (read all of it!)."""
    text = f"{type(error).__name__}: {error}"
    if "OLLAMA_HOST" in text:
        hint = "Set `OLLAMA_HOST` in your `.env` file (README, section 2.5)."
    elif "ngrok" in text.lower() or "ConnectError" in text or "ConnectionError" in text or "404" in text:
        hint = "The brain is not reachable. Is the Kaggle notebook running? Try `dami kaggle status`."
    elif "not found" in text.lower() and "model" in text.lower():
        hint = "The model is not on the server. Run `dami doctor`."
    elif "MCP" in text or "client initialization" in text:
        hint = "DaMi's hands (the MCP server) did not start. Run `python -m dami.mcp_server.server`."
    else:
        hint = "Run `dami doctor`, and read the full error below."
    st.error(hint, icon=":material/report:")
    with st.expander("Full error", icon=":material/bug_report:"):
        st.exception(error)


# ----------------------------------------------------------------------------- status checks
@st.cache_data(ttl=30, show_spinner=False)
def brain_status(host: str | None, model: str) -> dict:
    if not host:
        return {"ok": False, "why": "OLLAMA_HOST is not set"}
    base = host.rstrip("/")
    try:
        r = requests.get(f"{base}/api/version", headers=NGROK_HEADERS, timeout=3)
        if r.status_code != 200:
            return {"ok": False, "why": "tunnel offline (start the Kaggle notebook)" if "ERR_NGROK" in r.text else f"HTTP {r.status_code}"}
        loaded = requests.get(f"{base}/api/ps", headers=NGROK_HEADERS, timeout=3).json().get("models", [])
    except requests.RequestException as e:
        return {"ok": False, "why": f"not reachable ({type(e).__name__})"}
    ctx = next((m.get("context_length") for m in loaded if m.get("name", "").startswith(model)), None)
    return {"ok": True, "version": r.json().get("version"), "loaded": bool(ctx), "server_context": ctx}


@st.cache_data(ttl=30, show_spinner=False)
def observability_status(vm_url: str, langfuse_url: str) -> dict:
    def up(url: str) -> bool:
        try:
            return requests.get(url, timeout=0.5).status_code == 200
        except requests.RequestException:
            return False

    return {"grafana": up(f"{vm_url}/health") and up("http://127.0.0.1:3001/api/health"),
            "langfuse": up(f"{langfuse_url}/api/public/health")}


# ----------------------------------------------------------------------------- under the hood
def snapshot(agent, live: LiveProgress, run: dict, before: dict) -> dict:
    """Everything the panel needs about the run that just finished (a copy: the agent keeps changing)."""
    after = agent.event_loop_metrics.accumulated_usage
    invocation = agent.event_loop_metrics.latest_agent_invocation
    return {
        "run": run,
        "steps": copy.deepcopy(live.steps),
        "strands_usage": {k: after.get(k, 0) - before.get(k, 0) for k in ("inputTokens", "outputTokens")},
        "strands_calls": [dict(c.usage) for c in invocation.cycles] if invocation else [],
        "system_prompt": agent.system_prompt,
        "tool_specs": agent.tool_registry.get_all_tool_specs(),
        "messages": copy.deepcopy(agent.messages),
    }


def under_the_hood(snap: dict, settings: Settings) -> None:
    run = snap["run"]
    with st.expander(f"Under the hood · run `{run.get('run_id')}`", icon=":material/manage_search:", type="compact"):
        a, b, c, d = st.columns(4)
        a.metric("Model calls", len(snap["strands_calls"]), border=True)
        b.metric("Tool calls", sum(1 for s in snap["steps"] if s["kind"] == "tool"), border=True)
        usage = snap["strands_usage"]
        c.metric("Tokens in / out", f"{usage['inputTokens']:,} / {usage['outputTokens']:,}", border=True)
        d.metric("Latency", f"{run.get('latency_s', '?')} s", border=True)

        timeline, numbers, model_saw, evidence = st.tabs(
            ["Timeline", "Two instruments", "What the model saw", "Evidence"])
        with timeline:
            _timeline(snap)
        with numbers:
            _instruments(snap)
        with model_saw:
            st.caption("The model reads all of this on every call (1 token ≈ 4 characters).")
            st.markdown(f"**System prompt** (~{len(snap['system_prompt']) // 4:,} tokens)")
            st.code(snap["system_prompt"], language="markdown", wrap_lines=True, height=200)
            specs = json.dumps(snap["tool_specs"])
            st.markdown(f"**Tool schemas**: {len(snap['tool_specs'])} tools (~{len(specs) // 4:,} tokens)")
            st.json(snap["tool_specs"], expanded=False)
            history = json.dumps(snap["messages"], default=str)
            st.markdown(f"**Conversation history** that DaMi kept: {len(snap['messages'])} messages (~{len(history) // 4:,} tokens)")
            st.json(snap["messages"], expanded=False)
        with evidence:
            st.caption("Copy this into your JOURNAL.md (use the copy button on the right).")
            st.code(f"run `{run.get('run_id')}` — {len(snap['strands_calls'])} model calls, "
                    f"{run.get('tool_calls', 0)} tool calls, {run.get('latency_s', '?')} s", language=None)
            path = settings.runs_dir / f"{run.get('run_id')}.jsonl"
            if path.exists():
                st.download_button("Download the run file", path.read_bytes(), file_name=path.name,
                                   icon=":material/download:", on_click="ignore")


def _timeline(snap: dict) -> None:
    outputs = [t.get("output_preview", "") for t in snap["run"].get("tools", [])]
    calls, tool_i, model_i = snap["strands_calls"], 0, 0
    for step in snap["steps"]:
        if step["kind"] == "model":
            used = calls[model_i].get("inputTokens") if model_i < len(calls) else None
            model_i += 1
            tokens = f" · {used:,} tokens in" if isinstance(used, int) else ""
            st.markdown(f":material/psychology: **Model call {step['n']}** · {step.get('seconds', '?')} s"
                        f"{tokens} · stop: `{step.get('stop', '?')}`")
        else:
            ok = step.get("status") == "success"
            with st.expander(f"`{step['name']}` · {step.get('seconds', '?')} s",
                             icon=":material/check_circle:" if ok else ":material/error:", type="step"):
                st.caption("Input (what the brain asked for)")
                st.code(json.dumps(step["input"], indent=2), language="json", wrap_lines=True)
                st.caption("Output (the first 500 characters that the brain read)")
                st.code(outputs[tool_i] if tool_i < len(outputs) else "", language="json", wrap_lines=True, height=220)
            tool_i += 1
    st.markdown(":material/edit_note: **Answer written**")


def _instruments(snap: dict) -> None:
    st.caption("The same run, measured by DaMi's run recorder (src/dami/hooks/recorder.py) and by Strands itself.")
    run, calls, steps = snap["run"], snap["strands_calls"], snap["steps"]
    rows = [
        ("Model calls", run.get("model_calls"), len(calls)),
        ("Input tokens (whole run)", run.get("input_tokens"), sum(c.get("inputTokens", 0) for c in calls)),
        ("Output tokens (whole run)", run.get("output_tokens"), sum(c.get("outputTokens", 0) for c in calls)),
        ("Tool calls with an error", sum(1 for t in run.get("tools", []) if t.get("status") != "ok"),
         sum(1 for s in steps if s["kind"] == "tool" and s.get("status") == "error")),
    ]
    st.dataframe([{"Measure": m, "Run recorder": r, "Strands": s} for m, r, s in rows], hide_index=True)

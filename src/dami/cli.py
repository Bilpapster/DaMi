"""The `dami` command. Run `dami --help` to see all commands."""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime

from strands.hooks import (
    AfterToolCallEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

from dami.config import PACKAGE_DIR, get_settings


class _ConsoleToolPrinter(HookProvider):
    """Print each tool call in the terminal while DaMi works."""

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)
        registry.add_callback(AfterToolCallEvent, self.after)

    def before(self, event: BeforeToolCallEvent) -> None:
        args = ", ".join(f"{k}={v!r}" for k, v in (event.tool_use.get("input") or {}).items())
        print(f"   🔧 {event.tool_use['name']}({args})", flush=True)

    def after(self, event: AfterToolCallEvent) -> None:
        print(f"      -> {event.result.get('status')} in {event.duration or 0:.2f}s", flush=True)


def cmd_chat(args) -> int:
    from dami.agent import build_agent

    agent = build_agent(session="cli", extra_hooks=[_ConsoleToolPrinter()])
    print("🕵️  DaMi is listening. Type 'exit' to stop, 'reset' to forget the conversation.\n")
    try:
        while True:
            try:
                text = input("👤 You: ").strip()
            except EOFError:
                break
            if text.lower() in {"exit", "quit", "bye"}:
                break
            if text.lower() == "reset":
                agent.messages.clear()
                print("🧹 Conversation cleared.\n")
                continue
            if not text:
                continue
            result = agent(text)
            run = agent.dami_recorder.last_run or {}
            print(f"\n🕵️  DaMi: {str(result).strip()}\n   (run {run.get('run_id')}, {run.get('latency_s')}s)\n")
    finally:
        agent.cleanup()
    return 0


def cmd_ask(args) -> int:
    from dami.agent import build_agent

    agent = build_agent(session="cli", extra_hooks=[_ConsoleToolPrinter()])
    try:
        result = agent(" ".join(args.question))
        run = agent.dami_recorder.last_run or {}
        print(f"\n{str(result).strip()}\n\n(run {run.get('run_id')}, {run.get('latency_s')}s)")
    finally:
        agent.cleanup()
    return 0


def cmd_ui(args) -> int:
    app = PACKAGE_DIR / "ui" / "app.py"
    # Bind to 127.0.0.1: only your own computer can open the UI.
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.address", "127.0.0.1",
           "--server.port", str(args.port), "--browser.gatherUsageStats", "false"]
    return subprocess.call(cmd)


def cmd_tools(args) -> int:
    """Show what the model sees: the system prompt and every tool schema, with a size estimate."""
    from dami.agent import load_system_prompt, make_mcp_client

    s = get_settings()
    prompt = load_system_prompt(s)
    total = len(prompt) // 4
    print(f"System prompt: ~{len(prompt) // 4} tokens ({s.prompt_file})\n")
    client = make_mcp_client()
    with client:
        tools = client.list_tools_sync()
    for t in tools:
        spec = t.tool_spec
        size = len(json.dumps(spec)) // 4
        total += size
        first_line = (spec.get("description") or "").strip().splitlines()[0:1]
        print(f"  {spec['name']:22s} ~{size:4d} tokens  {first_line[0] if first_line else '(no description)'}")
        if args.verbose:
            print(json.dumps(spec, indent=2), "\n")
    print(f"\nTotal before the first question: ~{total} tokens (1 token ≈ 4 characters; a rough estimate).")
    return 0


def cmd_exam(args) -> int:
    from dami import exam

    only = args.only.split(",") if args.only else None
    return exam.run(args.tag, repeat=args.repeat, only=only)


def cmd_mini(args) -> int:
    from dami.harness import mini_loop

    print(mini_loop.run(" ".join(args.question)))
    return 0


def cmd_doctor(args) -> int:
    from dami import doctor

    return doctor.run(skip_chat=args.skip_chat)


def cmd_kaggle(args) -> int:
    from dami.kaggle import runner

    if args.action == "start":
        return runner.start(args.model, args.idle_minutes, args.max_hours, args.wait_minutes)
    if args.action == "status":
        return runner.show_status()
    if args.action == "partner":
        return runner.partner(args.url)
    print("The Kaggle CLI cannot stop a running notebook. It stops by itself after IDLE_MINUTES "
          "without requests, or open https://www.kaggle.com/code and stop it there.")
    return 0


def cmd_duo(args) -> int:
    from dami.duo import agents, evaluate
    from dami.duo.cleaning import CleaningPlan, apply_plan
    from dami.duo.journal import Journal

    journal = Journal.default()
    if args.action == "run":
        agents.run_session(args.evaluations, args.spawns, args.session)
        print(journal.render())
        return 0
    if args.action == "journal":
        print(journal.render())
        return 0
    if args.action == "score":
        if not args.plan:
            print("Give a plan file: dami duo score --plan my_plan.json")
            return 1
        with open(args.plan, encoding="utf-8") as f:
            plan = CleaningPlan(**json.load(f))
        raw = evaluate.load_table()
        base, cleaned = evaluate.score_frame(raw), evaluate.score_frame(apply_plan(raw, plan))
        print(f"no cleaning: F1 = {base.f1:.3f}\nyour plan:   F1 = {cleaned.f1:.3f} (Δ {cleaned.f1 - base.f1:+.3f}, "
              f"precision {cleaned.precision:.2f}, recall {cleaned.recall:.2f}) — not written to the journal")
        return 0
    if args.action == "reset":
        if journal.store.exists():
            backup = journal.store.with_name(f"journal-{datetime.now():%Y%m%d-%H%M%S}.jsonl")
            journal.store.rename(backup)
            print(f"Journal moved to {backup}. The next session starts without memory.")
        else:
            print("The journal is already empty.")
        return 0
    return 1


def cmd_obs(args) -> int:
    from dami import obs

    return {"init": obs.init, "down": obs.down, "delete": obs.delete, "status": obs.status}.get(args.action, lambda: obs.up(args.traces))()


def main(argv=None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="dami", description="DaMi, the data mining agent.")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("doctor", help="check the brain, the hands and the observability stack")
    d.add_argument("--skip-chat", action="store_true", help="do not send a test message to the model")
    d.set_defaults(func=cmd_doctor)

    sub.add_parser("chat", help="chat with DaMi in the terminal").set_defaults(func=cmd_chat)

    a = sub.add_parser("ask", help="ask DaMi one question")
    a.add_argument("question", nargs="+")
    a.set_defaults(func=cmd_ask)

    u = sub.add_parser("ui", help="open the chat web app (Streamlit) on http://127.0.0.1:8501")
    u.add_argument("--port", type=int, default=8501)
    u.set_defaults(func=cmd_ui)

    t = sub.add_parser("tools", help="show the system prompt and tool schemas that the model receives")
    t.add_argument("-v", "--verbose", action="store_true", help="print the full JSON schemas")
    t.set_defaults(func=cmd_tools)

    e = sub.add_parser("exam", help="run the DaMi exam questions and save a summary")
    e.add_argument("--tag", required=True, help="a name for this run, e.g. baseline, step2, step3")
    e.add_argument("--repeat", type=int, default=1, help="run each question N times")
    e.add_argument("--only", help="comma-separated question ids, e.g. Q2,Q5")
    e.set_defaults(func=cmd_exam)

    m = sub.add_parser("mini", help="ask a question with your own mini harness (Step 3)")
    m.add_argument("question", nargs="+")
    m.set_defaults(func=cmd_mini)

    k = sub.add_parser("kaggle", help="start DaMi's brain on Kaggle")
    k.add_argument("action", choices=["start", "status", "stop", "partner"],
                   help="partner: find your partner's tunnel URL (Step 5) and save it as OLLAMA_HOST_B")
    k.add_argument("--url", help="partner: set OLLAMA_HOST_B to this URL instead of reading the partner's log")
    k.add_argument("--model", help="Ollama model (default: OLLAMA_MODEL from .env)")
    k.add_argument("--idle-minutes", type=int, default=20)
    k.add_argument("--max-hours", type=float, default=4)
    k.add_argument("--wait-minutes", type=int, default=120, help="start: how long to wait for the brain (Kaggle can queue for a long time)")
    k.set_defaults(func=cmd_kaggle)

    du = sub.add_parser("duo", help="Step 5: a driver agent and its sub-agents on two brains")
    du.add_argument("action", choices=["run", "journal", "score", "reset"])
    du.add_argument("--evaluations", type=int, default=6, help="run: evaluation budget of the session")
    du.add_argument("--spawns", type=int, default=4, help="run: how many sub-agents the driver may start")
    du.add_argument("--session", help="run: a name for the session")
    du.add_argument("--plan", help="score: a JSON file with a cleaning plan")
    du.set_defaults(func=cmd_duo)

    o = sub.add_parser("obs", help="local observability stack: Grafana + VictoriaMetrics (+ Langfuse)")
    o.add_argument("action", choices=["init", "up", "down", "delete", "status"],
                   help="delete: stop the stack and delete its volumes (all metrics, traces and stored passwords)")
    o.add_argument("--traces", action="store_true", help="also start Langfuse (needs ~4 GB RAM)")
    o.set_defaults(func=cmd_obs)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

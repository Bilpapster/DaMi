"""`dami doctor`: check every part of DaMi and say what to fix."""

import time
import traceback

import requests

from dami.config import REPO_ROOT, get_settings
from dami.model import NGROK_HEADERS

OK, BAD, WARN, INFO = "✅", "❌", "⚠️ ", "ℹ️ "


def _get(url: str, timeout: float = 10):
    return requests.get(url, headers=NGROK_HEADERS, timeout=timeout)


def check_brain(s) -> bool:
    print("\n🧠 Brain (Ollama on Kaggle)")
    if not s.ollama_host:
        print(f"  {BAD} OLLAMA_HOST is not set in .env")
        return False
    print(f"  {INFO} OLLAMA_HOST = {s.ollama_host}")
    try:
        r = _get(f"{s.ollama_host.rstrip('/')}/api/version")
    except requests.RequestException as e:
        print(f"  {BAD} cannot reach the tunnel: {type(e).__name__}. Is the URL right?")
        return False
    if r.status_code != 200:
        hint = "the Kaggle notebook is not running (start it: `dami kaggle start`)" if "ERR_NGROK" in r.text else r.text[:200]
        print(f"  {BAD} HTTP {r.status_code}: {hint}")
        return False
    print(f"  {OK} Ollama {r.json().get('version')} answers through the tunnel")

    names = [m["name"] for m in _get(f"{s.ollama_host.rstrip('/')}/api/tags").json().get("models", [])]
    if s.model_id in names or f"{s.model_id}:latest" in names:
        print(f"  {OK} model {s.model_id} is downloaded")
    else:
        print(f"  {BAD} model {s.model_id} is not on the server. Server has: {names or 'nothing'}")
        return False

    print(f"  {INFO} DaMi asks for: temperature={s.temperature}, think={s.think}, "
          f"num_ctx={s.context_length or '(not set: server default)'}")
    return True


def check_chat(s) -> None:
    from dami.model import make_model
    from strands import Agent

    t = time.time()
    try:
        agent = Agent(model=make_model(s), callback_handler=None, system_prompt="Answer with one word.")
        result = agent("Say OK.")
        took = time.time() - t
        print(f"  {OK} test answer in {took:.1f}s: {str(result).strip()[:60]!r}")
        if took > 30:
            print(f"  {WARN} slow first answer: the model was probably loading into GPU memory")
    except Exception as e:  # noqa: BLE001
        print(f"  {BAD} test chat failed: {e}")
        return
    try:
        ps = _get(f"{s.ollama_host.rstrip('/')}/api/ps").json().get("models", [])
        for m in ps:
            vram = m.get("size_vram", 0) / 1e9
            print(f"  {INFO} loaded: {m.get('name')}  context_length={m.get('context_length', '?')}  "
                  f"in GPU memory: {vram:.1f} GB")
    except Exception:  # noqa: BLE001
        pass


def check_hands() -> None:
    print("\n🖐️  Hands (MCP tool server)")
    from dami.agent import make_mcp_client

    try:
        client = make_mcp_client()
        with client:
            tools = client.list_tools_sync()
        print(f"  {OK} MCP server started with {len(tools)} tools: {', '.join(t.tool_name for t in tools)}")
    except Exception as e:  # noqa: BLE001
        print(f"  {BAD} the MCP server did not start: {e}")
        print("     Run it alone to see the full error:  python -m dami.mcp_server.server")
        detail = "".join(traceback.format_exception(e)).strip().splitlines()[-3:]
        for line in detail:
            print(f"     | {line}")


def check_observability(s) -> None:
    print("\n🔭 Observability (optional, `dami obs up`)")
    for name, url in {
        "VictoriaMetrics": f"{s.victoriametrics_url}/health",
        "Grafana": "http://127.0.0.1:3001/api/health",
        "Langfuse": f"{s.langfuse_host}/api/public/health",
    }.items():
        try:
            up = requests.get(url, timeout=2).status_code == 200
        except requests.RequestException:
            up = False
        print(f"  {OK if up else '⚪'} {name} {'is running' if up else 'is not running'}")


def run(skip_chat: bool = False) -> int:
    s = get_settings()
    print("🩺 DaMi doctor")
    env = REPO_ROOT / ".env"
    print(f"  {OK if env.exists() else BAD} .env file {'found' if env.exists() else 'missing: copy .env.example to .env'}")
    brain_ok = check_brain(s)
    if s.ollama_host_b:
        print("\n🧠 Brain B (Case 6: your partner's notebook)")
        from dami.kaggle.runner import brain_ready

        ok_b, why_b = brain_ready(s.ollama_host_b, s.model_id_b or s.model_id)
        print(f"  {OK if ok_b else BAD} OLLAMA_HOST_B = {s.ollama_host_b}: {why_b}")
    if brain_ok and not skip_chat:
        check_chat(s)
    check_hands()
    check_observability(s)
    print()
    return 0 if brain_ok else 1

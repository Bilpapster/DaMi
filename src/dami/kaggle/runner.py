"""Start DaMi's brain on Kaggle from your terminal: `dami kaggle start`.

The push/status logic is adapted from the kaggle-automation utilities written by
George Atmatzidis. It uses the official `kaggle` package (its Python API and its CLI).

How it works:
1. You create the notebook once on kaggle.com (README: "Kaggle notebook"). Put its id
   ("<username>/<slug>") in .env as KAGGLE_NOTEBOOK, and your ngrok token as NGROK_AUTHTOKEN.
2. `dami kaggle start` uploads the notebook in this package as a new version of
   your notebook and runs it in the background, with a T4 GPU and internet on.
   Kaggle secrets are not available in versions pushed from the API, so the ngrok
   token is written into the uploaded copy. Keep the notebook PRIVATE.
3. The notebook starts Ollama, downloads the model and opens the ngrok tunnel.
4. This command reads the tunnel URL from the notebook's live log, writes it into .env as
   OLLAMA_HOST, and waits until the brain answers through the tunnel.
5. The notebook stops by itself when nobody uses it for IDLE_MINUTES, to save GPU quota.
   The Kaggle CLI cannot stop a running notebook; you can also stop it on kaggle.com.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import requests

from dami.config import REPO_ROOT, get_settings
from dami.model import NGROK_HEADERS

NOTEBOOK = Path(__file__).with_name("llm_DaMi.ipynb")
DEFAULT_ACCELERATOR = os.getenv("KAGGLE_ACCELERATOR", "NvidiaTeslaT4")


def _kaggle_cmd() -> list[str]:
    exe = shutil.which("kaggle")
    if exe:
        return [exe]
    return [sys.executable, "-m", "kaggle"]


def _run_kaggle(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([*_kaggle_cmd(), *args], capture_output=True, text=True)


def _fix_notebook_metadata(nb: dict) -> None:
    nb.setdefault("metadata", {})
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["metadata"]["language_info"] = {"name": "python"}


def _set_parameters(nb: dict, params: dict) -> None:
    """Change the values in the cell that starts with '# PARAMETERS'."""
    for cell in nb["cells"]:
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code" and source.lstrip().startswith("# PARAMETERS"):
            for name, value in params.items():
                source = re.sub(rf"^{name}\s*=.*$", f"{name} = {value!r}", source, flags=re.M)
            cell["source"] = source.splitlines(keepends=True)
            return
    raise RuntimeError("The notebook has no '# PARAMETERS' cell.")


def push(notebook_id: str, model: str, idle_minutes: int, max_hours: float, accelerator: str,
         ngrok_token: str | None = None) -> str:
    username, _, slug = notebook_id.partition("/")
    if not (username and slug):
        raise ValueError("KAGGLE_NOTEBOOK must look like '<kaggle-username>/<notebook-slug>'.")

    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    _fix_notebook_metadata(nb)
    params = {"MODEL": model, "IDLE_MINUTES": idle_minutes, "MAX_HOURS": max_hours}
    if ngrok_token:
        params["NGROK_AUTHTOKEN_FALLBACK"] = ngrok_token
    _set_parameters(nb, params)

    api = _kaggle_api()
    existing = _find_notebook(api, notebook_id)
    if existing is None:
        print(f"ℹ️  No notebook '{notebook_id}' found in your account: Kaggle will create it (private).")
        existing = {"id": notebook_id, "id_no": None, "title": slug}
    elif existing["id"] != notebook_id:
        print(f"ℹ️  Your notebook's real id is '{existing['id']}'. Put KAGGLE_NOTEBOOK={existing['id']} in .env.")

    metadata = {
        # Push as a new VERSION of the existing notebook: same id, id number and title.
        # (Another title makes Kaggle try to create a second notebook: "title already in use".)
        "id": existing["id"],
        "id_no": existing["id_no"],
        "title": existing["title"],
        "code_file": NOTEBOOK.name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    with tempfile.TemporaryDirectory(prefix="dami-kaggle-") as tmp:
        (Path(tmp) / NOTEBOOK.name).write_text(json.dumps(nb, indent=1), encoding="utf-8")
        (Path(tmp) / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        timeout_s = str(int(max_hours * 3600) + 900)
        # We call the Python API of the `kaggle` package (the CLI does the same), because the
        # CLI hides the reason that Kaggle gives when it refuses a push.
        try:
            response = api.kernels_push(tmp, timeout=timeout_s, acc=accelerator)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            body = e.response.text.strip() if e.response is not None else ""
            raise RuntimeError(_explain_push_error(code, body or str(e))) from e

    error = getattr(response, "error", "")
    if error:
        raise RuntimeError(_explain_push_error(None, error))
    version = getattr(response, "version_number", None)
    return f"Version {version} started: {getattr(response, 'url', '')}", version


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _find_notebook(api, notebook_id: str) -> dict | None:
    """Find the notebook in the user's account: by its id first, then by a title that matches the slug."""
    with tempfile.TemporaryDirectory(prefix="dami-kaggle-pull-") as tmp:
        try:
            api.kernels_pull(notebook_id, tmp, metadata=True, quiet=True)
            meta = json.loads((Path(tmp) / "kernel-metadata.json").read_text(encoding="utf-8"))
            return {"id": meta["id"], "id_no": meta.get("id_no"), "title": meta["title"]}
        except Exception:  # noqa: BLE001 - not found by id: search by title below
            pass
    slug = notebook_id.partition("/")[2].lower()
    for kernel in api.kernels_list(mine=True, search=slug.replace("-", " "), page_size=50) or []:
        if kernel and (_slugify(kernel.title) == slug or kernel.ref.lower().endswith("/" + slug)):
            return {"id": kernel.ref, "id_no": kernel.id, "title": kernel.title}
    return None


def _kaggle_api():
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    try:
        api.authenticate()
    except (Exception, SystemExit) as e:  # the kaggle package exits when it finds no credentials
        raise RuntimeError("No Kaggle credentials found. Run `kaggle auth login`, or see README "
                           "section 2.6.") from e
    return api


def _explain_push_error(code: int | None, reason: str) -> str:
    if "Maximum weekly GPU quota" in reason:
        return "Your weekly Kaggle GPU quota is used up. It resets every week."
    if code in (401, 403):
        return f"Kaggle rejected your credentials (HTTP {code}). Run `kaggle auth login`.\nKaggle says: {reason}"
    if code == 409:
        return ("Kaggle refused to save a new version of the notebook (HTTP 409 Conflict).\n"
                f"Kaggle says: {reason}\n"
                "Common causes: the notebook is running right now (an open session in your browser, or an earlier\n"
                "`dami kaggle start`), or KAGGLE_NOTEBOOK does not match your notebook's URL. Stop the session on\n"
                "kaggle.com (Run -> Stop session, and close the editor tab), then try again.")
    return f"kaggle kernels push failed (HTTP {code}).\nKaggle says: {reason}"


def status(notebook_id: str) -> str:
    result = _run_kaggle("kernels", "status", notebook_id)
    if result.returncode != 0:
        raise RuntimeError(f"kaggle kernels status failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def brain_ready(host: str, model: str) -> tuple[bool, str]:
    """Check through the ngrok tunnel if Ollama answers and has the model."""
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", headers=NGROK_HEADERS, timeout=10)
    except requests.RequestException as e:
        return False, f"tunnel not reachable ({type(e).__name__})"
    if r.status_code != 200:
        if "ERR_NGROK_3200" in r.text or r.status_code == 404:
            return False, "tunnel is offline (the notebook has not opened it yet)"
        return False, f"HTTP {r.status_code}"
    names = [m.get("name", "") for m in r.json().get("models", [])]
    if not any(n == model or n.startswith(model + ":") or n.split(":")[0] == model for n in names):
        return False, f"Ollama is up, model '{model}' is still downloading"
    return True, "ready"


HOST_LINE = re.compile(r"OLLAMA_HOST=(https://\S+)")


def _watch_log_for_host(kernel: str, found: list, stop: threading.Event) -> None:
    """Stream the notebook log and remember every OLLAMA_HOST=... line (the last one wins)."""
    api = _kaggle_api()
    while not stop.is_set():
        try:
            for event in api.kernels_logs_stream(kernel):
                for match in HOST_LINE.finditer(str(event.get("data", ""))):
                    found.append(match.group(1).rstrip("/"))
                if stop.is_set():
                    return
        except Exception:  # noqa: BLE001 - the log is not available yet: try again
            pass
        stop.wait(10)


def _write_env(key: str, value: str) -> None:
    """Set KEY=value in the .env file (replace the line, or add it)."""
    env = REPO_ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    lines = [line for line in lines if not re.match(rf"^\s*{key}\s*=", line)]
    lines.append(f"{key}={value}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def start(model: str | None, idle_minutes: int, max_hours: float, wait_minutes: int,
          accelerator: str = DEFAULT_ACCELERATOR) -> int:
    s = get_settings()
    model = model or s.model_id
    if not s.kaggle_notebook:
        print("❌ KAGGLE_NOTEBOOK is not set in .env (example: KAGGLE_NOTEBOOK=jane/llm-dami).")
        return 1

    # Kaggle secrets do not reach versions pushed from the API: the token goes into the (private) copy.
    token = os.getenv("NGROK_AUTHTOKEN")
    if not token:
        print("❌ NGROK_AUTHTOKEN is not set in .env. Copy it from https://dashboard.ngrok.com/get-started/your-authtoken")
        return 1

    ok, _ = brain_ready(s.ollama_host, model) if s.ollama_host else (False, "")
    if ok:
        print(f"✅ The brain is already running at {s.ollama_host} with {model}.")
        return 0

    print(f"🚀 Pushing the notebook to Kaggle as {s.kaggle_notebook} (GPU {accelerator}, model {model}) ...")
    try:
        message, version = push(s.kaggle_notebook, model, idle_minutes, max_hours, accelerator, token)
        print(message)
    except Exception as e:  # noqa: BLE001 - show the message to the student
        print(f"❌ {e}")
        return 1

    # The ngrok URL can change on every run: read it from the live log of THIS version.
    kernel = f"{s.kaggle_notebook}/{version}" if version else s.kaggle_notebook
    found: list[str] = []
    stop = threading.Event()
    threading.Thread(target=_watch_log_for_host, args=(kernel, found, stop), daemon=True).start()

    print(f"⏳ Waiting for the brain (up to {wait_minutes} min). Ctrl+C stops waiting, not the notebook.")
    deadline = time.time() + wait_minutes * 60
    last, host = "", None
    while time.time() < deadline:
        if found and found[-1] != host:
            host = found[-1]
            _write_env("OLLAMA_HOST", host)
            print(f"   🔗 tunnel URL from the notebook log: {host} (written to .env as OLLAMA_HOST)")
        ok, why = brain_ready(host, model) if host else (False, "waiting for the tunnel URL in the notebook log")
        if ok:
            stop.set()
            print(f"\n✅ DaMi's brain is ready at {host}. It stops by itself after {idle_minutes} idle minutes.")
            return 0
        try:
            kstate = status(s.kaggle_notebook)
        except Exception as e:  # noqa: BLE001
            kstate = str(e)
        line = f"   kaggle: {kstate} | brain: {why}"
        if line != last:
            print(line)
            last = line
        if "error" in kstate.lower() or "cancel" in kstate.lower():
            stop.set()
            print("❌ The notebook stopped with an error. Read its log: kaggle kernels logs " + s.kaggle_notebook)
            return 1
        time.sleep(15)
    stop.set()
    print("⌛ The brain is not ready yet. Check `dami kaggle status`, or the log: kaggle kernels logs " + s.kaggle_notebook)
    return 1


def partner(url: str | None = None) -> int:
    """Step 5: find the tunnel URL of your partner's running notebook and save it as OLLAMA_HOST_B.

    Your partner shares their notebook with you once on kaggle.com (Share -> add you as a collaborator),
    and you put its id in .env as PARTNER_NOTEBOOK. Then this command reads the URL from the live log.
    """
    s = get_settings()
    if not url:
        if not s.partner_notebook:
            print("❌ PARTNER_NOTEBOOK is not set in .env (example: PARTNER_NOTEBOOK=alex/llm-dami). "
                  "Or give the URL directly: dami kaggle partner --url https://....ngrok-free.app")
            return 1
        print(f"🔎 Reading the log of {s.partner_notebook} ...")
        found: list[str] = []
        stop = threading.Event()
        threading.Thread(target=_watch_log_for_host, args=(s.partner_notebook, found, stop), daemon=True).start()
        deadline = time.time() + 60
        while time.time() < deadline and not found:
            time.sleep(2)
        stop.set()
        if not found:
            print("❌ No tunnel URL in the partner's log. Is their notebook running (dami kaggle start on their side)? "
                  "Did they share the notebook with you on kaggle.com?")
            return 1
        url = found[-1]
    ok, why = brain_ready(url, s.model_id_b or s.model_id)
    _write_env("OLLAMA_HOST_B", url.rstrip("/"))
    print(f"{'✅' if ok else '⚠️ '} OLLAMA_HOST_B={url} saved in .env (brain B: {why}).")
    return 0 if ok else 1


def show_status() -> int:
    s = get_settings()
    if s.kaggle_notebook:
        try:
            print(f"Kaggle notebook {s.kaggle_notebook}: {status(s.kaggle_notebook)}")
        except Exception as e:  # noqa: BLE001
            print(f"Kaggle notebook {s.kaggle_notebook}: {e}")
    if s.ollama_host:
        ok, why = brain_ready(s.ollama_host, s.model_id)
        print(f"Brain at {s.ollama_host}: {'✅ ' if ok else '❌ '}{why}")
    return 0

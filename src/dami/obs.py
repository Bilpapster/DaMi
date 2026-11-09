"""`dami obs ...`: start and stop the local observability stack (docker compose)."""

import secrets
import shutil
import subprocess

import requests

from dami.config import REPO_ROOT, get_settings

ENV_FILE = REPO_ROOT / ".env"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yaml"


def _secret_values() -> dict[str, str]:
    return {
        "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(12),
        "LANGFUSE_NEXTAUTH_SECRET": secrets.token_urlsafe(32),
        "LANGFUSE_SALT": secrets.token_urlsafe(32),
        "LANGFUSE_ENCRYPTION_KEY": secrets.token_hex(32),
        "LANGFUSE_POSTGRES_PASSWORD": secrets.token_urlsafe(16),
        "LANGFUSE_CLICKHOUSE_PASSWORD": secrets.token_urlsafe(16),
        "LANGFUSE_REDIS_PASSWORD": secrets.token_urlsafe(16),
        "LANGFUSE_MINIO_PASSWORD": secrets.token_urlsafe(16),
        "LANGFUSE_INIT_PROJECT_PUBLIC_KEY": f"pk-lf-{secrets.token_hex(16)}",
        "LANGFUSE_INIT_PROJECT_SECRET_KEY": f"sk-lf-{secrets.token_hex(16)}",
        "LANGFUSE_INIT_USER_EMAIL": "detective@dami.local",
        "LANGFUSE_INIT_USER_PASSWORD": secrets.token_urlsafe(12),
    }


def _read_env() -> dict[str, str]:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    return values


def _existing_volumes() -> list[str]:
    """Docker volumes left by an earlier start of this stack (empty list if Docker is missing)."""
    if not shutil.which("docker"):
        return []
    try:
        out = subprocess.run(["docker", "volume", "ls", "-q", "--filter", "label=com.docker.compose.project=dami"],
                             check=False, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted(v for v in out.split() if v)


def init(show_logins: bool = True) -> int:
    existing = _read_env()
    new = {k: v for k, v in _secret_values().items() if not existing.get(k)}
    if not new:
        print("✅ .env already has all observability secrets.")
    else:
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write("\n# --- Observability stack (written by `dami obs init`; keep this file private) ---\n")
            for k, v in new.items():
                f.write(f"{k}={v}\n")
        ENV_FILE.chmod(0o600)
        print(f"✅ Wrote {len(new)} values to {ENV_FILE}.")
        old = _existing_volumes()
        if old:
            print("⚠️  Data of an earlier stack exists (Docker volumes: " + ", ".join(old) + ").\n"
                  "   Grafana and Langfuse keep the passwords of their FIRST start, so the new ones will not work.\n"
                  "   To start fresh (this deletes the stored metrics and traces):\n"
                  "     dami obs down && docker volume rm " + " ".join(old))
    if show_logins:
        print_logins()
    return 0


def print_logins() -> None:
    env = _read_env()
    print("\nLogins (local only):")
    print(f"  Grafana   http://127.0.0.1:3001   user: admin   password: {env.get('GRAFANA_ADMIN_PASSWORD', '?')}")
    print(f"  Langfuse  http://127.0.0.1:3000   user: {env.get('LANGFUSE_INIT_USER_EMAIL', '?')}"
          f"   password: {env.get('LANGFUSE_INIT_USER_PASSWORD', '?')}")


def _compose(*args: str) -> int:
    if not shutil.which("docker"):
        print("❌ Docker is not installed. See README: 'Observability'.")
        return 1
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def up(traces: bool) -> int:
    if not _read_env().get("GRAFANA_ADMIN_PASSWORD"):
        init(show_logins=False)
    profiles = ["--profile", "metrics"] + (["--profile", "traces"] if traces else [])
    code = _compose(*profiles, "up", "-d")
    if code == 0:
        print_logins()
        if traces:
            print("\nLangfuse needs about 1-2 minutes for its first start.")
    return code


def down() -> int:
    return _compose("--profile", "metrics", "--profile", "traces", "down")


def status() -> int:
    s = get_settings()
    checks = {
        "VictoriaMetrics": f"{s.victoriametrics_url}/health",
        "Grafana": "http://127.0.0.1:3001/api/health",
        "Langfuse": f"{s.langfuse_host}/api/public/health",
    }
    for name, url in checks.items():
        try:
            ok = requests.get(url, timeout=2).status_code == 200
        except requests.RequestException:
            ok = False
        print(f"  {'✅' if ok else '⚪'} {name:15s} {url}")
    return 0

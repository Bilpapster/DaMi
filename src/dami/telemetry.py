"""Send OpenTelemetry traces of every agent run to Langfuse (optional).

Strands creates a trace for each run, with one span per model call and per tool
call. If Langfuse keys are in your .env (`dami obs init` writes them) and Langfuse
is running (`dami obs up --traces`), the traces appear at http://127.0.0.1:3000.
"""

import base64
import logging
import os

import requests

from dami.config import Settings

log = logging.getLogger(__name__)
_DONE = False


def setup_tracing(settings: Settings) -> bool:
    """Turn on tracing once per process. Returns True if traces go to Langfuse."""
    global _DONE
    if _DONE:
        return True
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return False
    host = settings.langfuse_host.rstrip("/")
    try:
        requests.get(f"{host}/api/public/health", timeout=1)
    except requests.RequestException:
        log.info("Langfuse is not reachable at %s; tracing is off.", host)
        return False

    from strands.telemetry import StrandsTelemetry

    token = base64.b64encode(f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{host}/api/public/otel/v1/traces"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {token}"
    StrandsTelemetry().setup_otlp_exporter()
    _DONE = True
    return True

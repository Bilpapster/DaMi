"""A Strands hook that sends agent metrics to VictoriaMetrics (shown in Grafana).

This hook is ready to use: you do not need to change it. Start the metrics stack
with `dami obs up` and open Grafana to see the "DaMi cockpit" dashboard.
If VictoriaMetrics is not running, the hook does nothing.

Metrics (one sample per event, so you can count, average and plot them):
    dami_tool_call_duration_seconds{tool, status}     one sample per tool call
    dami_model_call_duration_seconds{stop_reason}     one sample per model call
    dami_model_input_tokens / dami_model_output_tokens one sample per model call
    dami_run_duration_seconds, dami_run_model_calls, dami_run_tool_calls   one sample per run
    dami_context_limit_tokens                          the num_ctx that DaMi asked for (0 = server default)
All metrics also have the labels `model` and `session`.
"""

import logging
import queue
import threading
import time

import requests
from strands.hooks import (
    AfterInvocationEvent,
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeModelCallEvent,
    HookProvider,
    HookRegistry,
)

from dami.config import Settings

log = logging.getLogger(__name__)


def _labels(**labels) -> str:
    def esc(v) -> str:
        return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in labels.items()) + "}"


class _Pusher:
    """Sends lines in Prometheus text format to VictoriaMetrics from a background thread."""

    def __init__(self, url: str):
        self.url = url.rstrip("/") + "/api/v1/import/prometheus"
        self.q: queue.Queue[str] = queue.Queue(maxsize=10_000)
        self._paused_until = 0.0
        threading.Thread(target=self._run, daemon=True, name="dami-metrics").start()

    def put(self, line: str) -> None:
        if time.time() < self._paused_until:
            return
        try:
            self.q.put_nowait(line)
        except queue.Full:
            pass

    def _run(self) -> None:
        while True:
            lines = [self.q.get()]
            while not self.q.empty() and len(lines) < 500:
                lines.append(self.q.get_nowait())
            try:
                requests.post(self.url, data="\n".join(lines) + "\n", timeout=2)
            except requests.RequestException:
                if self._paused_until == 0.0:
                    log.info("VictoriaMetrics is not reachable at %s; metrics are off for now.", self.url)
                self._paused_until = time.time() + 60


_PUSHERS: dict[str, _Pusher] = {}


class VictoriaMetricsHook(HookProvider):
    def __init__(self, settings: Settings, session: str = "chat"):
        self.base = {"model": settings.model_id, "session": session}
        self.context_limit = settings.context_length or 0
        url = settings.victoriametrics_url
        self.pusher = _PUSHERS.setdefault(url, _Pusher(url))
        self._run_started = 0.0
        self._model_started = 0.0
        self._tool_calls = 0

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_run_start)
        registry.add_callback(BeforeModelCallEvent, self.on_model_start)
        registry.add_callback(AfterModelCallEvent, self.on_model_end)
        registry.add_callback(AfterToolCallEvent, self.on_tool)
        registry.add_callback(AfterInvocationEvent, self.on_run_end)

    def _emit(self, name: str, value: float, **labels) -> None:
        ts = int(time.time() * 1000)
        self.pusher.put(f"{name}{_labels(**self.base, **labels)} {value} {ts}")

    def on_run_start(self, event: BeforeInvocationEvent) -> None:
        self._run_started = time.time()
        self._tool_calls = 0
        self._emit("dami_context_limit_tokens", self.context_limit)

    def on_model_start(self, event: BeforeModelCallEvent) -> None:
        self._model_started = time.time()

    def on_model_end(self, event: AfterModelCallEvent) -> None:
        if event.stop_response is not None:
            reason = event.stop_response.stop_reason
        else:
            reason = "exception"
        self._emit("dami_model_call_duration_seconds", round(time.time() - self._model_started, 3), stop_reason=reason)

    def on_tool(self, event: AfterToolCallEvent) -> None:
        self._tool_calls += 1
        status = event.result.get("status", "unknown")
        self._emit("dami_tool_call_duration_seconds", round(event.duration or 0.0, 3), tool=event.tool_use["name"], status=status)

    def on_run_end(self, event: AfterInvocationEvent) -> None:
        invocation = event.agent.event_loop_metrics.latest_agent_invocation
        cycles = invocation.cycles if invocation else []
        for cycle in cycles:
            self._emit("dami_model_input_tokens", cycle.usage.get("inputTokens", 0))
            self._emit("dami_model_output_tokens", cycle.usage.get("outputTokens", 0))
        self._emit("dami_run_duration_seconds", round(time.time() - self._run_started, 3))
        self._emit("dami_run_model_calls", len(cycles))
        self._emit("dami_run_tool_calls", self._tool_calls)

"""Build DaMi: brain (model) + hands (MCP tools) + harness (loop, prompt, memory, hooks).

Everything that is not the model is "the harness": the code that decides what the
model sees, which tools it can call, what happens when a tool fails, how much
history it keeps, and what is recorded. Strands' `Agent` class is a harness.
In this file you choose its settings.
"""

import os
import sys

from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.tools.mcp import MCPClient

from dami.config import Settings, get_settings
from dami.hooks.metrics import VictoriaMetricsHook
from dami.hooks.recorder import RunRecorder
from dami.model import make_model
from dami.telemetry import setup_tracing

# How many messages of the conversation DaMi keeps. A small number keeps the context small.
MAX_HISTORY_MESSAGES = 8


def make_mcp_client() -> MCPClient:
    """Start DaMi's MCP server as a child process and connect to it over stdio."""
    # Pass our environment to the child: by default the MCP SDK passes only a few safe variables.
    params = StdioServerParameters(command=sys.executable, args=["-m", "dami.mcp_server.server"], env=dict(os.environ))
    return MCPClient(lambda: stdio_client(params))


def load_system_prompt(settings: Settings) -> str:
    template = settings.prompt_file.read_text(encoding="utf-8")
    return template.format(data_dir=settings.data_dir, plots_dir=settings.plots_dir)


def build_agent(settings: Settings | None = None, *, session: str = "chat", extra_hooks=None) -> Agent:
    """Create a ready-to-use DaMi agent."""
    s = settings or get_settings()
    setup_tracing(s)

    recorder = RunRecorder(s.runs_dir, session=session)
    hooks = [recorder, VictoriaMetricsHook(s, session=session)]
    hooks += list(extra_hooks or [])

    agent = Agent(
        name="DaMi",
        model=make_model(s),
        tools=[make_mcp_client()],
        system_prompt=load_system_prompt(s),
        conversation_manager=SlidingWindowConversationManager(window_size=MAX_HISTORY_MESSAGES),
        hooks=hooks,
        callback_handler=None,
        trace_attributes={"session.id": session, "dami.model": s.model_id},
    )
    agent.dami_recorder = recorder  # the UI and the exam read the last run from here
    return agent

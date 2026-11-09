"""DaMi's front door: the web chat. Start it with `dami ui`.

Page flow only; the building blocks (live progress, status checks, "under the hood")
are in parts.py, the colours in .streamlit/config.toml and style.css.
"""

import re
from pathlib import Path

import streamlit as st

from dami.agent import build_agent
from dami.config import get_settings
from dami.ui import parts

st.set_page_config(page_title="DaMi Detective Agency", page_icon="🕵️", layout="wide")
st.html(Path(__file__).with_name("style.css"))
st.logo(parts.LOGO, size="large")
settings = get_settings()
state = st.session_state


def start_dami() -> None:
    """Build the agent once per browser session (it keeps the conversation and the MCP server)."""
    if "agent" not in state:
        state.live = parts.LiveProgress()
        with st.spinner("Waking up DaMi (starting the tool server)..."):
            state.agent = build_agent(settings, session="ui", extra_hooks=[state.live])
        state.history = []


def reload_dami() -> None:
    """Throw the agent away. Needed after you change tools, the prompt or .env."""
    if "agent" in state:
        state.agent.cleanup()
        del state.agent
    state.history = []
    st.cache_data.clear()


def image_paths(run: dict) -> list[str]:
    found = []
    for tool in run.get("tools", []):
        for match in re.findall(r'"saved_to":\s*"([^"]+\.png)"', tool.get("output_preview", "")):
            if Path(match).exists():
                found.append(match)
    return found


def show_images(paths: list[str]) -> None:
    for n, path in enumerate(paths):
        st.image(path, width=620, caption=f"Exhibit {chr(65 + n)} · {Path(path).name}")


# ---------------------------------------------------------------- sidebar: the case file
with st.sidebar:
    st.badge(settings.model_id, icon=":material/psychology:", color="primary")
    brain = parts.brain_status(settings.ollama_host, settings.model_id)
    if brain["ok"]:
        st.badge(f"Brain online · Ollama {brain['version']}", icon=":material/cloud_done:", color="green")
    else:
        st.badge(f"Brain: {brain['why']}", icon=":material/cloud_off:", color="red")
    if "agent" in state:
        st.badge(f"Hands: {len(state.agent.tool_names)} tools", icon=":material/build:", color="green")

    with st.popover("Brain settings", icon=":material/tune:", width="stretch"):
        st.markdown(f"**Brain URL:** `{settings.ollama_host or 'not set'}`")
        st.markdown(f"**temperature** `{settings.temperature}` · **think** `{settings.think}`")
        st.markdown(f"**num_ctx DaMi asks for:** `{settings.context_length or 'nothing (server default)'}`")
        st.markdown(f"**Context of the loaded model (server):** `{brain.get('server_context') or 'not loaded yet'}`")
        if st.button("Check again", icon=":material/refresh:"):
            st.cache_data.clear()
            st.rerun()

    if "agent" in state:
        used = state.agent.event_loop_metrics.latest_context_size
        limit = settings.context_length or brain.get("server_context")
        if used and limit:
            st.progress(min(used / limit, 1.0), text=f"Context of the last call: {used:,} / {limit:,} tokens")
        elif used:
            st.caption(f"Context of the last call: {used:,} tokens (limit unknown)")

    left, right = st.columns(2)
    if left.button("New case", icon=":material/cleaning_services:", width="stretch",
                   help="Forget the conversation."):
        if "agent" in state:
            state.agent.messages.clear()
        state.history = []
        st.rerun()
    if right.button("Reload", icon=":material/restart_alt:", width="stretch",
                    help="Restart DaMi: needed after you change the tools, the prompt or .env."):
        reload_dami()
        st.rerun()

    st.divider()
    obs = parts.observability_status(settings.victoriametrics_url, settings.langfuse_host)
    st.markdown(("[:material/monitoring: Grafana cockpit](http://127.0.0.1:3001)" if obs["grafana"]
                 else ":material/monitoring: Grafana: not running") + "  \n" +
                ("[:material/account_tree: Langfuse traces](http://127.0.0.1:3000)" if obs["langfuse"]
                 else ":material/account_tree: Langfuse: not running"))
    if not (obs["grafana"] and obs["langfuse"]):
        st.caption("Start them with `dami obs up` (add `--traces` for Langfuse).")

# ---------------------------------------------------------------- main page
st.html('<div class="dami-wordmark">DAMI<b>·</b>DETECTIVE AGENCY</div>')
st.caption("Ask about the database: customers, products, marketing, sensors, transactions.")

if state.pop("running", False):
    st.warning("The last run was interrupted. Start a **New case** if DaMi seems confused.", icon=":material/warning:")

try:
    start_dami()
except Exception as e:  # noqa: BLE001 - explain it in the page
    parts.show_error(e)
    st.stop()

agent, live = state.agent, state.live

if not state.history:
    examples = parts.example_prompts()
    case = st.segmented_control("Examples", list(examples), default="Case 0", label_visibility="collapsed")
    st.pills("Try one", examples[case or "Case 0"], key="chip", label_visibility="collapsed",
             on_change=lambda: state.update(queued=state.chip, chip=None))

for item in state.history:
    with st.chat_message(item["role"], avatar=parts.USER_AVATAR if item["role"] == "user" else parts.DAMI_AVATAR):
        st.markdown(item["text"])
        if item.get("error"):
            parts.show_error(item["error"])
        show_images(item.get("images", []))
        if item.get("snap"):
            parts.under_the_hood(item["snap"], settings)

prompt = st.chat_input("What should DaMi investigate?", submit_mode="disable") or state.pop("queued", None)
if prompt:
    state.history.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar=parts.USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=parts.DAMI_AVATAR):
        state.running = True
        before = dict(agent.event_loop_metrics.accumulated_usage)
        answer, error = parts.run_streaming(agent, live, prompt)
        state.running = False
        run = agent.dami_recorder.last_run or {}
        snap = parts.snapshot(agent, live, run, before) if not error else None
        images = image_paths(run) if not error else []

        st.markdown(answer)
        if error:
            parts.show_error(error)
        show_images(images)
        if snap:
            parts.under_the_hood(snap, settings)

    state.history.append({"role": "assistant", "text": answer, "error": error, "images": images, "snap": snap})
    st.rerun()

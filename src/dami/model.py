"""DaMi's brain: the connection to the LLM that runs in Ollama.

Use `make_model()` everywhere you need a model (the agent, a sub-agent, a judge
for evaluations, a summarizer...). Strands has a default model, but that default
is a cloud model that needs an AWS account. We use our own free model instead.
"""

import dataclasses

from strands.models.ollama import OllamaModel

from dami.config import Settings, get_settings

# ngrok shows a "browser warning" page to unknown clients. This header skips it.
NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}


def make_model(settings: Settings | None = None, **overrides) -> OllamaModel:
    """Create a Strands model object that talks to our Ollama server."""
    s = settings or get_settings()
    if not s.ollama_host:
        raise ValueError(
            "OLLAMA_HOST is not set. Put the ngrok URL of your Kaggle notebook in the .env file "
            "(see README: 'Start the brain')."
        )

    options = {}
    if s.context_length:
        options["num_ctx"] = s.context_length

    config = dict(
        model_id=s.model_id,
        temperature=s.temperature,
        keep_alive=s.keep_alive,
        options=options or None,
        additional_args={"think": s.think},
    )
    config.update(overrides)

    return OllamaModel(
        s.ollama_host,
        ollama_client_args={"headers": NGROK_HEADERS, "timeout": s.request_timeout_s},
        **config,
    )


def make_model_b(settings: Settings | None = None, **overrides) -> OllamaModel:
    """The second brain (Case 6): OLLAMA_HOST_B, your partner's Kaggle notebook.

    Without OLLAMA_HOST_B, it falls back to your own brain (OLLAMA_HOST): one brain plays both roles.
    """
    s = settings or get_settings()
    s_b = dataclasses.replace(s, ollama_host=s.ollama_host_b or s.ollama_host, model_id=s.model_id_b or s.model_id)
    return make_model(s_b, **overrides)

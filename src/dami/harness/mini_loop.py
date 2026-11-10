"""Harness task (Step 4): write your own tiny agent harness, without Strands.

An agent is a loop:

    1. send the messages (system prompt + history + tool schemas) to the model
    2. if the model asks for tool calls: run them, add the results to the messages, go to 1
    3. else: the model's text is the final answer

Strands does this for you (plus a lot more). Here you write it yourself with the
plain `ollama` client, so that you see every message that goes to the model.

Run it with:   dami mini "Which tables do we have, and how many rows has customers?"

Then compare with Strands: ask DaMi the same question and look at its run file in
runs/ (and in Langfuse, if it runs). What does Strands do that your loop does not?
"""

import json

import numpy as np
import ollama

from dami.config import get_settings
from dami.core import algorithms
from dami.core.data import catalog, load_table, numeric_columns
from dami.model import NGROK_HEADERS

SYSTEM_PROMPT = "You are DaMi, a data-mining assistant. Use the tools to answer. Be brief."


# --- The tools: plain Python functions. The ollama client builds the JSON schema from
# --- the type hints and the docstring, like Strands and MCP do.
def list_tables() -> str:
    """List the tables of the database with their descriptions."""
    return json.dumps({name: info.get("description", "") for name, info in catalog().items()})


def count_rows(table: str) -> str:
    """Count the rows of a table.

    Args:
        table: name of the table
    """
    return str(len(load_table(table)))


def kmeans_sizes(table: str, n_clusters: int) -> str:
    """Run K-means on a table and return the size of each cluster.

    Args:
        table: name of the table
        n_clusters: number of clusters
    """
    df = load_table(table)
    labels = algorithms.kmeans(df[numeric_columns(df)].to_numpy(), n_clusters=n_clusters)["labels"]
    return json.dumps({int(k): int(v) for k, v in zip(*np.unique(labels, return_counts=True))})


TOOLS = {f.__name__: f for f in (list_tables, count_rows, kmeans_sizes)}


def run(question: str, max_steps: int = 8, verbose: bool = True) -> str:
    s = get_settings()
    client = ollama.Client(host=s.ollama_host, headers=NGROK_HEADERS)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for step in range(1, max_steps + 1):
        response = client.chat(
            model=s.model_id,
            messages=messages,
            tools=list(TOOLS.values()),
            think=False,
            options={"temperature": 0.2},
        )
        message = response.message
        if verbose:
            print(f"--- step {step}: prompt tokens={response.prompt_eval_count}, output tokens={response.eval_count}")

        # TODO 1: add the model's message to `messages` (the history).

        # TODO 2: if the model did NOT ask for tools (message.tool_calls is empty), return message.content.

        # TODO 3: for each call in message.tool_calls:
        #           - find the Python function in TOOLS by call.function.name
        #           - call it with **call.function.arguments
        #           - if it fails, do not crash: give the error text to the model instead
        #           - append {"role": "tool", "tool_name": <name>, "content": <result text>} to messages
        #           - print the call and the first 200 characters of the result (when verbose)
        raise NotImplementedError("Finish the loop: see TODO 1-3 in src/dami/harness/mini_loop.py")

    return "I stopped because I reached the step limit."

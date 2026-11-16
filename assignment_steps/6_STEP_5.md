# 👯 DaMi Step 5: Two brains are better than one?

> One agent drives, the others get their hands dirty.

## Prerequisites

This step is **optional**. Please make sure you have completed Steps 1 to 4 before starting it. It works best with the observability stack from Step 3, so make sure `dami obs up --traces` works for you.

## 🧩 The setup

A factory has 4 machines (M1 to M4) with sensors for temperature, pressure, vibration and power. The readings are in `data/duo/factory_line.csv`, and the data is dirty. A fixed outlier detector runs on the table, and its findings are compared with hidden labels of the real anomalies. The detector never changes, so the only way to a better F1 score is cleaner data.

DaMi now works as a small team:
- The **driver** (brain A) never sees the data. It starts sub-agents, writes their system prompts, scores their plans and keeps a journal.
- Each **sub-agent** (brain B) inspects the data with read-only tools and proposes a cleaning plan: an ordered list of steps from a fixed set of 7 steps (see `src/dami/duo/cleaning.py`).
- The **journal** (`workspace/duo/journal.md`) is the team's memory across sessions: the best plans so far, their scores, and lessons the driver wrote.

The code is in `src/dami/duo/` and the driver's system prompt is in `src/dami/prompts/duo_driver.md`.

## 🎬 DO

0. Activate your virtual environment.

1. Set up two brains. Each team member starts their own Kaggle notebook. One member shares their notebook with the other on kaggle.com and the other one sets `PARTNER_NOTEBOOK` in `.env` and runs `dami kaggle partner`. Now `OLLAMA_HOST_B` points to the second brain.

   > _Hint_: Working alone or only one notebook running? Without `OLLAMA_HOST_B`, one brain plays both roles. It is slower, but it works.

1. Start the observability stack and run a session with `dami duo run`. A session takes about 10-15 minutes. Follow it in Langfuse (filter by the session id): what does the driver write as the system prompt of each sub-agent, which tools does each sub-agent call, and which plan does it propose?

1. When the session finishes, open the journal (`dami duo journal`, or `workspace/duo/journal.md`):
   - Which plans did the sub-agents propose, and how did each one score against no cleaning?
   - Which lessons and next steps did the driver write for the next session? Do they make sense?

1. Leveraging your Data Mining expertise, extend the team with **one** of the following:
   - a new cleaning step in `src/dami/duo/cleaning.py` (for example, fill missing values per machine instead of over the whole table), or
   - a new read-only tool for the sub-agents in `src/dami/duo/agents.py`.

   Run another session and check whether the agents use your addition and whether the score improves.

## 🤔💭 THINK AND ANSWER

1. Why does DaMi split the work between a driver and sub-agents, instead of one agent that both inspects the data and scores the plans? What does each of them know, and what does it not know? Think of privacy (the driver never sees the data) and of the context window (every sub-agent starts with a fresh, small context).

1. What is the journal for? What does the driver read from it at the start of a session, and what would a new session do without it? (You can try it: `dami duo reset` starts without memory and keeps your journal as a backup.)

1. The scores in the journal are written by the tools, while the lessons are written by the driver. Why this split? Pick one lesson: is it true, or did one lucky score mislead the driver? How could you check?

1. In the traces, does a new sub-agent learn from the plans and scores of the earlier ones, or does it start from scratch? What decides this?

1. Look at the best plan in your journal, step by step. Does it really clean the data, or did it find a way to raise the F1 score without cleaning anything (e.g., by setting a whole column to 0)? What is the detector rewarding, and how could you stop the agents from cheating?

1. Did the agents use your new cleaning step or tool? How do you know, and did the score improve?

1. Using the tokens and the time you saw in Grafana and Langfuse: when does a team of agents pay off, and when is it just overhead compared to a single agent?

## 📝 RECAP

Congratulations! You have successfully completed the fifth and last (optional) step of the assignment. Here is what you did in this step:
1. You ran a multi-agent system and followed how a driver and its sub-agents pass information to each other.
1. You saw how a journal gives a team of agents a memory across sessions, and why facts and opinions are kept apart in it.
1. You extended the agents' toolbox with your own data cleaning knowledge.
1. You weighed the benefits of multiple agents against their cost.

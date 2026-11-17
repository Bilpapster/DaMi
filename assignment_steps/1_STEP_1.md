# 🤗 DaMi Step 1: Hello DaMi!

> DaMi's first day on the job!

## Prerequisites

This step requires having set up uv, your Kaggle and ngrok accounts, as well as your `.env` file with the appropriate variables. If you have not completed the required installations, please stop here and complete those first as described in the repository's README before continuing. The rest of this document assumes that the set up has been successfully completed. All commands should run from the root directory of the project.

## 📓 Your notes

Throughout the assignment you will run experiments, observe DaMi, and answer questions. Keep notes as you go: they will make your answers and your final presentation much easier. The repository has a notebook for this, `JOURNAL.md`, at its root. You can use it to write down your observations, together with the evidence for each one (a run id from `runs/`, an exam file, a screenshot or a trace). Using it is optional: if you prefer, keep your notes in your own personal notes instead.

## 🎬 DO

0. Make sure you have activated your virtual environment with `source .venv/bin/activate` (Linux, MacOS)  or `.venv\Scripts\activate` (Windows).

1. Familiarize yourself with the `dami` command suite - you will use it a lot throughout this assignment. Run `dami --help` and observe the options. Explore the different sub-commands with `dami [sub-command] --help` (e.g., `dami kaggle --help`).

2. Run `dami doctor` and read the output. You should see something like this:
```
🩺 DaMi doctor
  ✅ .env file found

🧠 Brain (Ollama on Kaggle)
  ℹ️  OLLAMA_HOST = https://<some-numbers-and-letters>.ngrok-free.app
  ❌ HTTP 404: the Kaggle notebook is not running (start it: `dami kaggle start`)

🖐️  Hands (MCP tool server)
  ✅ MCP server started with 11 tools: list_tables, describe_table, get_table_info, kmeans, dbscan, plot_table, plot_clusters, plot_outliers, get_workspace_paths, list_csv_files_in, add

[... some logs about observability tools]
```

3. It's time to run DaMi end-to-end for the first time. Run `dami kaggle start` and read the logs. The command uploads `src/dami/kaggle/llm_DaMi.ipynb` to your Kaggle account and polls the log to discover the ngrok tunnel URL. Kaggle can keep the notebook in a queue until a GPU is free, so please allow up to 2 hours for it to complete (the command waits that long). In the end you should see something like this:
```
🔗 tunnel URL from the notebook log: https://<some-numbers-and-letters>.ngrok-free.app (written to .env as OLLAMA_HOST)
✅ DaMi's brain is ready at https://<some-numbers-and-letters>.ngrok-free.app. It stops by itself after 20 idle minutes.
```

4. Once the ngrok tunnel is available, use the  `dami ask` command to ask DaMi what its name is. Read the response. Ask a couple more questions to break the ice!

5. Asking questions from the command line is fast, but nothing compares to a good UI! Use the `ui` sub-command of the `dami` suite to start the streamlit UI. Open the URL printed in the console in a browser. Ask DaMi questions through the UI. Read the answers and explore the UI options (e.g., expanding the "Under the hood" section of each reply)


## 🤔💭 THINK AND ANSWER

1. Take a look at the Python Notebook that we uploaded to kaggle (`src/dami/kaggle/llm_DaMi.ipynb`). 
    1. What is the code in there doing? Which technologies of the assignment's tech stack does it cover?
    2. Where does this code run? Why can't we just run it locally?

2. Recall asking DaMi its name.
    1. How does DaMi know its name?
    2. What other information does DaMi get on startup? Where does this information live in the code base?
    3. Can you make DaMi always respond with just a Haiku poem, no matter what the user asks? How would you do that? (Note: every time you change DaMi's system prompt, make sure to stop the UI command with Ctrl+C and restart it with `dami ui` so that your changes take effect).

3. Find where DaMi is put together in the code base.
    1. Where is the agent created? Which model, system prompt and tools does it get there?
    2. Where do DaMi's tools live? How does the agent find out which tools it has?
    3. Find the conversation manager of the agent. What does it do, and how many messages of a conversation does DaMi keep?

4. Test DaMi's memory. In a new chat, tell DaMi something about you (e.g., your team name). Then ask it 4-5 other questions, some of which need tools (e.g., "Describe the customers table"). Finally, ask DaMi what your team name is.
    1. Does DaMi remember it? Use your answer to question 3.3 to explain why.
    2. Does DaMi forget sooner when your questions need tools? Why?

## 📝 RECAP

Congratulations! You have successfully completed the first step of the assignment. Here is what you did in this step:
1. You started a Python Notebook running an LLM on Kaggle.
2. You communicated with this LLM using both the command line and a UI.
3. You discovered where DaMi's system prompt lives and experimented with manipulating it.
4. You found where DaMi's agent, tools and conversation manager are configured.
5. You tested how much of a conversation DaMi remembers, and why.

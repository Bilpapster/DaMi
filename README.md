# DaMi: Your Intelligent DAta MIning Companion 🤖

_DaMi is a AI agent specialized in Data Mining. He particularly likes clustering and outlier detection!_

**DaMi needs your help! Can you provide him with high-quality, well-explained tools?** Keep reading to learn how you can lend a hand!

## Instructions Overview
- [Prerequisites](#prerequisites) &larr; &larr; &larr; START HERE, DO NOT SKIP!
  - [Environment file](#environment-file)
  - [`uv` installation](#uv-installation)
  - [Kaggle account creation](#kaggle-account)
  - [NGROK account creation](#ngrok-account)
  - [NGROK authentication token](#ngrok-authentication-token)
  - [Kaggle notebook upload](#kaggle-notebook-upload)
- [How to](#how-to) &larr; &larr; &larr; Your cookbook to complete the assignment
  - [Edit the system prompt](#edit-the-system-prompt)
  - [Add a new dataset](#add-a-dataset)
  - [Add a new tool](#add-a-tool)
  - [Test your tools without DaMi](#test-your-tools-without-dami)
  - [Improve the description of a tool](#improve-the-description-of-a-tool)
  - [Test your tools with DaMi](#test-your-tools-with-dami)
  - [Use a different LLM](#use-a-different-llm)
  - [Ask a question about the assignment](#ask-a-question-about-the-assignment)
 
- [Understand what you have done](#understand-what-you-have-done) &larr; &larr; &larr; Read this to get the most out of the assignment

## Prerequisites
This section covers the prerequisites for running DaMi. All steps described below need to be completed _just once_ **per person**.
Please make sure that you complete the prerequisites in the order they are presented. 
Once you have set up all the prerequisites, move to the [How to](#how-to) section.

### Environment file
An environment file (usually `.env`) is a plain text file that stores configuration settings as key-value pairs. It's used to define environment variables, such as API keys, database credentials, and other sensitive information, separating them from the application's source code.

**Your task:** Download the `.env` file from E-learning. Place it in the root folder of the project (i.e., where this README is located).

### `uv` installation
`uv` is a unified package and project manager for Python. It combines `pip`, `pyenv`, and `Poetry` into a single, highly performant
tool written in Rust. 

**Your task:** Navigate to `uv`'s [official documentation](https://docs.astral.sh/uv/getting-started/installation/) and run the 
installation command for your operating system.

### Kaggle account
Kaggle is an online community platform for data scientists and machine learning engineers that hosts data science competitions, 
provides datasets, and offers a web-based environment for building and sharing models.

**Your task:** If you already have a Kaggle account, make sure you can log in. If you do not have an account, create one for free
[here](https://www.kaggle.com/account/login?phase=startRegisterTab). You will need a valid phone number to receive a verification SMS.

### NGROK account

NGROK is a tool that creates a secure tunnel between a public internet endpoint and a local server on your machine, 
allowing you to expose your local development environment to the internet.

**Your task:** If you already have an NGROK account, make sure you can log in. If you do not have an account, create one for free.
[here](https://dashboard.ngrok.com/signup)

### NGROK authentication token

An NGROK authentication token is a unique API key that authorizes the ngrok agent to connect to your account, enabling most of 
its features like tunneling.

**Your task:** Make sure you have created an NGROK account in the previous step. Then, find your token through 
[NGROK's portal](https://dashboard.ngrok.com/get-started/your-authtoken). You will need this token for the next step.

### Kaggle notebook upload

A Kaggle Notebook is a cloud-based, interactive environment for data science and machine learning that runs in a web browser. 
It allows users to write and execute code in Python.

**Your task:** Download the `llm_DaMi.ipynb` located in the `kaggle/` directory of the repository. Then, navigate to
[Kaggle](https://www.kaggle.com/) &rarr; _+ Create_ &rarr; _<> Notebook_ &rarr; (a new notebook opens in your browser) 
&rarr; File &rarr; Import Notebook &rarr; (upload the `llm_DaMi.ipynb` file) &rarr; (optional) rename the notebook title 
to `llm_DaMi` for convenience. Then, click _Add-ons_ &rarr; _Secrets_. You must see a secret called `NGROK_AUTHTOKEN`.
Edit the value by pasting the authentication token from the previous step. Make sure to save your changes.

**Congratulations! You have successfully completed all the prerequisites!**
 
## How to
This section provides instructions on how to perform various tasks in order to help DaMi get access to high-quality, well-explained tools.

### Edit the system prompt
The system prompt is defined in the `src/agent/system_prompt.py`. Feel free to experiment with different variations of the system prompt. Make sure to restart your agent for the changes to take effect.

### Add a dataset
**PENDING**

### Add a tool
All tools that DaMi has access to are placed in the `src/tools/` directory of the project. They are further organized into sub-directories based on
their domain. For example, the tools for clustering can be found inside the `src/tools/clustering/` directory. To add a new tool, see how existing tools
are defined and create yours! 

_Hint:_ You might need to change more than one files to make your tool visible to DaMi!
 
### Test your tools without DaMi

From inside the `src/` directory run  `uv run mcp dev mcp_server.py` in a terminal. If this is the first time you run this command, you may
be asked to install some packages. Type `y` and hit enter. You must see a web interface in your browser. 
Click _Connect_ &rarr; _Tools_ &rarr; _List Tools_. You must see all available tools. Select the one you want to test and fill in the parameters.
Click _Run tool_ to call the tool (as if you were DaMi) and see the output. Debug your tool if the output does not match your expectations. 

**Note**: We have added a dummy `add` tool, in case you want a quick verification that your MCP server works. Once you set everything up, feel
free to remove this tool (or even the whole `src/tools/math/` directory).

### Improve the description of a tool
All tools that DaMi has access to are placed in the `src/tools/` directory of the project. They are further organized into sub-directories based on
their domain. For example, the tools for clustering can be found inside the `src/tools/clustering/` directory. What DaMi actually sees for every tool
is the documentation (docstrings) of each tool. To improve the documentation of an existing tool, review the tool to understand what the source code
does and, then, update the docstrings to clearly (and concisely) reflect the tool's functionality. Imagine you are DaMi. How would you explain the tool to
yourself so that you know when to use (and when to not use) it, without looking at the source code?

### Test your tools with DaMi

Open the Kaggle notebook you created during the prerequisites stage. Make sure you have enabled GPU acceleration (_Settings_ &rarr; _Accelerator_ &rarr; _GPU T4 x 2_). Make sure you have added your NGROK authentication token as a secret to the notebook. From the top menu, click _Run All_ and wait until all 5 cells run successfully (this might take a couple of minutes). Go to the output of the 4th cell. You must see a URL in the format `https://someLettersAndNumbers.ngrok-free.app`. Copy this URL and paste it to update the `OLLAMA_HOST` variable in the `.env` file of your local project.

**Important Notice:** If you want to understand what you have done, please see the [Understand what you have done](#understand-what-you-have-done) section. Unfortunately you will need to create a new URL (and upate the `.env`) every time you want to run DaMi. Finally, the Kaggle notebook will automatically close if the notebook receives no activity for 10-15 minutes. So, if you want to test for longer, please make sure you produce some activity (e.g., clicking at a cell, typing letters) every now and then. If your session terminates due to inactivity, do not panic. On the top menu, click the three dots &rarr; _Restart and run all cells_. You will get a new URL to use in your `.env` file.

While your Kaggle session is running and your local `.env` file contains the latest URL (remember, latest output of cell 4) you are all set to run DaMi. From the `src/` directory, run `uv run streamlit run ui/chat_interface.py`. DaMi runs in [localhost:8501](http://localhost:8501/) and is ready to chat with you!

**Important Notice:** When you are done with your testing, make sure you stop the Kaggle session to save quota. Kaggle provides for free 30 hours of GPU usage per week per person, which must be more than sufficient for the purposes of this assignment! To stop the UI, hit Ctrl + C in the terminal where you previously ran `uv run streamlit run ui/chat_interface.py`. This will terminate the DaMi chat in your browser.


### Use a different LLM
_Or else, how to change DaMi's brain._

If you haven't changed anything, DaMi runs [gpt-oss](https://ollama.com/library/gpt-oss) (20B parameters) on Kaggle. This must be sufficient for the needs of this assignment. However, if you want to experiment with other models, feel free to explore the [available options](https://ollama.com/search) on Ollama. Please note that [models with reasoning capabilities](https://ollama.com/search?c=thinking) are typically more suitable for agents. In any case, feel free to explore models with trial and error.

Once you have selected a model, you need to change two things:
- In the Kaggle notebook, change the `model` variable in cell 5. Re-run all cells and make sure you update the URL in the `.env`.
- In your local code, change the `OLLAMA_MODEL` environment variable in `.env` to the match the model you have used. If your UI is running, you will need to restart it (Ctrl + C and then `uv run streamlit run ui/chat_interface.py`). 



### Ask a question about the assignment
This README should cover everything you need in order to successfully complete the assignment. However, if you find any blockers, please follow the steps below in order:
1. Search again this documentation. Make sure you have completed all prerequisites. Make sure your question cannot be answered based on what is written here.
2. Search the web or ask an LLM. If you are running into an error, search for the error message online. If you are running into some other issue, search for resources on how to do what you want to do. Make sure you understand the solution before copy-pasting.
3. If you are still unable to find an answer, navigate to the e-learning website of the module. Find the forum dedicated to the assignment. Search for existing threads that are relevant to your issue. It might be the case that someone else had the same issue before you!
4. If you are still unable to find an answer, create a new thread. Make sure you describe:
    - Your issue clearly in a concise, informative title, so that other people can find it easily;
    - What you want to do;
    - What you have already tried before posting;
    - Why what you have tried failed;
    - How can others replicate your error;
    - Any additional context that can be useful to others in order to help you.

**Important Notice**: Messages such as "I have problem with X." (without any other information), or questions that can be answered with the information provided in this README will be ignored.

## Understand what you have done
This section is optional. However, we strongly encourage you to go through it, in order to understand what you have done and how all the pieces connect together. This section will help you wrap up the knowledge and skills you acquired through this assignment and help you get the most out of it.

- **What is DaMi actually?** _Answer_: DaMi is actually three distinct components working together: an MCP server with tools (DaMi's hands), an LLM (DaMi's brain), and a web application in Streamlit (DaMi's front door). The MCP server defines the tools and the way they are visible to DaMi. The LLM uses these tools and its reasoning capabilities to answer your prompts. The web application just creates a beautiful chat interface between you and the LLM. Learn more: [MCP](https://modelcontextprotocol.github.io/python-sdk/) | [Streamlit](https://streamlit.io/)

- **What happens every time I run the Kaggle notebook?** _or else_ **Where is the LLM?** _Answer_: **PENDING** Learn more: [Ollama](https://docs.ollama.com/)

- **What happens every time I send a message to DaMi?** **PENDING**



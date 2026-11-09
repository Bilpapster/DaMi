# 📦 DaMi Step 3: Opening the black box!

> Diving into DaMi's internals.

## Prerequisites

Please make sure you have completed Steps 1 and 2 before starting this one. This step also requires a local docker installation, so if your team has decided to not install docker (for example, Windows users without WSL) feel free to skip this step.

## 🎬 DO

0. Activate your virtual environment.

1. Start a kaggle notebook and the UI. Then run `dami obs up --traces` (_obs_ as a shorthand of _observability_). If this is the first time running this command please allow a couple of minutes for the script to pull all necessary artifacts (docker images). Before exiting, the command prints in the terminal your credentials for logging in to grafana and langfuse. Note these credentials as they will be needed for the next step. The credentials should look like this:
   ```
   Logins (local only):
     Grafana   http://127.0.0.1:3001   user: admin   password: <a-password>
     Langfuse  http://127.0.0.1:3000   user: detective@dami.local   password: <a-password>
   ```

1. Open the DaMi UI. On the left hand side panel, click on "Grafana cockpit" and "Langfuse traces" to open them in a new tab. Use your credentials to log in to both tools.

1. In the Grafana UI, open "Dashboards" (left hand side panel) -> DaMi -> DaMi cockpit.

1. In the Langfuse UI, locate the "DaMi" project and click on "Go to project" and then "Tracing".

1. Keeping the Langfuse UI and Grafana UI open, head back to the DaMi UI and start chatting with DaMi. Observe the tool calls using the "under the hood" button at the end of each DaMi's message. Then head back to Langfuse and Grafana and compare the information you see there about the tool calls and DaMi's raw messages.

1. Read about [Strands hooks](https://strandsagents.com/docs/user-guide/sdk/agents/hooks/) and find some existing hooks in the code base. Read through their code and understand what each hook measures.

1. Find the `recorder` hook. Identify where the numbers from this hook are displayed and then compare them with the numbers you see in Grafana and Langfuse. One source does not agree with the other two sources, right? Investigate why, try to fix it, and verify that your fix works.

1. Read through the `src/dami/harness/mini_loop.py` file. Try to identify what it could be used for and how it connects with the `dami mini` command. Fix the three TODOs in the code and then use the `dami mini` command to test your fix. Compare the metrics from `mini` (number of tool calls, token usage) with the metrics from normal DaMi and try to explain the differences.

## 🤔💭 THINK AND ANSWER

1. What is the Grafana UI displaying? How can it help us gain control over DaMi's operations?

1. What is the Langfuse UI displaying? How can it help us gain control over DaMi's operations?

1. Looking at the Langfuse traces, how many times is the system prompt included in the messages of a single conversation? What does this mean for the context length of every next human message in a single conversation with DaMi?

1. Browse through DaMi's tool calls, reasoning, and responses. Find at least one example where DaMi takes a wrong or unnecessary step. Can you write a search filter to identify whether the specific pattern has occurred more than once?

1. Why is the `recorder` hook computing fewer tokens than Grafana and Langfuse? How is this connected with your answer to question 3?

1. How does your `mini` harness compare against the Strands harness? What learnings can we extract about Agentic harnesses?

## 📝 RECAP

Congratulations! You have successfully completed the third step of the assignment. Here is what you did in this step:
1. You spun up docker containers running Grafana and Langfuse; two widely used tools for Agentic AI observability
1. You monitored in real time DaMi's operations through these dedicated tools
1. You effectively used these tools to identify a failure mode of DaMi and took action to mitigate it
1. You re-invented the wheel building an Agentic harness of your own, understanding what out-of-the-box harnesses (such as Strands) silently offer

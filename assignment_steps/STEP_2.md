# ✍️ DaMi Step 2: Is DaMi getting any better?

> Same questions, every step, numbers instead of feelings.

## What is the exam?

The exam is a fixed set of data mining questions (`exam/questions.yaml`) that you ask DaMi again and again: once before you change anything (the baseline) and once after every step. Each question runs in a **new conversation**, so that the questions do not influence each other. In the end, you get a table that shows how DaMi's answers, tool calls, token usage, and latency change as you improve it.

The exam does **not** grade DaMi. You do! You are the data mining experts of the team.

## Prerequisites

Please make sure you have completed Step 1 and that DaMi's brain is running (`dami kaggle start`).

## 🎬 DO

0. Activate your virtual environment.

1. Take a look at `exam/questions.yaml`. You may add your own questions at the end of the file, but do **not** change the existing ones. Otherwise, the comparison between the steps is not fair.

1. Before you start Step 3, run the exam for the first time:
   ```bash
   dami exam --tag baseline
   ```
   The command prints every answer while it runs and, in the end, the path of a summary file (`runs/exam-baseline-<date-time>.csv`). Please allow some time for it to complete: some questions take a few minutes and some can fail. This is expected, the exam goes on with the next question.

1. Open the summary file and fill the `correct` column of each row with `yes`, `partly`, or `no`. Check the answers yourselves (e.g., with the MCP Inspector or a few lines of pandas): a confident answer is not always a correct one!

1. Run the exam again after every step, each time with a new tag, e.g., `dami exam --tag step3`, `dami exam --tag step4`, `dami exam --tag step5`. Fill the `correct` column again and compare the summary files.

1. Useful options:
    1. `--only Q2,Q5` runs only some of the questions (fast checks while you work).
    1. `--repeat 3` asks each question 3 times. Does DaMi always give the same answer?

1. Want to try a single exam question interactively? Open the DaMi UI and select "Exam" in the examples above the chat.

## 🤔💭 THINK AND ANSWER

1. Which questions did DaMi answer better after each step? Which change in the code base explains each improvement?

1. Did any answer get worse after a step? If so, why?

1. Run a few questions with `--repeat 3`. Are the answers the same every time? What could explain the differences?

1. How did the number of tool calls, the token usage, and the latency change from the baseline to your last run?

1. How did you decide if an answer is correct? Can you think of a way to automate this decision? What could go wrong if you did so?

## 📝 RECAP

Here is what you did with the exam:
1. You measured DaMi's performance on a fixed set of questions, before and after every improvement.
1. You graded DaMi's answers using your own data mining expertise.
1. You backed your improvements with numbers, ready for your presentation!

# ✍️ DaMi Exam: Is DaMi getting any better?

> Same questions, every step, numbers instead of feelings.

## What is the exam?

Before you improve DaMi, decide what "better" means. The exam is how you write that down: a fixed set of data mining questions (`exam/questions.yaml`) that describes what you expect DaMi to do well. Every question is a small test of a skill you care about, e.g., finding the right table, choosing a sensible clustering, or spotting outliers.

You ask DaMi the same questions again and again: once before you change anything (the baseline) and then after every change you make. Each question runs in a **new conversation**, so that the questions do not influence each other. In the end, you get a table that shows how DaMi's answers, tool calls, token usage, and latency change as you improve it.

The exam is your compass for the rest of the assignment: whenever you change DaMi, come back here and check whether it really got better.

The exam does **not** grade DaMi. You do! You are the data mining experts of the team.

## Prerequisites

Please make sure you have completed Step 1 and that DaMi's brain is running (`dami kaggle start`).

## 🎬 DO

0. Activate your virtual environment.

1. Take a look at `exam/questions.yaml`.
   The exam grows with you: you are free to add new questions at any time, whenever you find a better way to evaluate DaMi. Do **not** edit or remove existing questions (including your own ones once you have run them), otherwise the comparison between the runs is not fair. A question you add later has no answer in the earlier runs, so compare it only from the run where you added it. Keep a short log of every question you add (when and why) and report it in your final presentation.

1. Before you start Step 2, run the exam for the first time:
   ```bash
   dami exam --tag baseline
   ```
   The command prints every answer while it runs and, in the end, the paths of two files: a summary table (`runs/exam-baseline-<date-time>.csv`) and a report with the full answers (`runs/exam-baseline-<date-time>.md`). Please allow some time for it to complete: some questions take a few minutes and some can fail. This is expected, the exam goes on with the next question.

1. Grade the answers with `yes`, `partly`, or `no`:

   > **📖 Read the `.md`, ✍️ grade in the `.csv`, or 🖥️ do both in the UI.**
   >
   > - **Without the UI:** read the full answers in the `.md` report and type your grades in the `correct` column of the `.csv` file.
   > - **With the UI:** run `dami ui`, turn on "Exam results" in the sidebar, and pick your run. You read each full answer (with its plots and tool calls) and grade it on the same page. Your grades are saved in the `correct` column of the `.csv` file.

   Check the answers yourselves (e.g., with the MCP Inspector or a few lines of pandas): a confident answer is not always a correct one!

1. Come back to the exam after every step, and run it with a new tag each time, e.g., `dami exam --tag step2`, `dami exam --tag step3`, `dami exam --tag step4`. Grade the new answers in the same way, and compare the runs in the tables at the top of "Exam results" (or in the `.csv` files).

   > _Hint_: Do not wait for the end of a step. After every single change (a new tool, a new system prompt, a fixed bug), run the questions it should affect with `--only` and check that it helped, and that nothing else broke.

1. Useful options:
    1. `--only Q2,Q5` runs only some of the questions (fast checks while you work).
    1. `--repeat 3` asks each question 3 times. Does DaMi always give the same answer?

1. Want to try a single exam question interactively? Open the DaMi UI and select "Exam" in the examples above the chat.

## 🤔💭 THINK AND ANSWER

1. Which questions did DaMi answer better after each step? Which change in the code base explains each improvement?

1. Did any answer get worse after a step? If so, why?

1. Run a few questions with `--repeat 3`. Are the answers the same every time? What could explain the differences?

1. How did the number of tool calls, the token usage, and the latency change from the baseline to your last run?

1. Which of your own questions told you the most about DaMi?

1. Which questions did you add during the assignment, and why? Which one helped you evaluate DaMi better?

1. How did you decide if an answer is correct? Can you think of a way to automate this decision? What could go wrong if you did so?

## 📝 RECAP

Here is what you did with the exam:
1. You designed your own exam, a set of questions that defines what a good DaMi is for you, and extended it along the way.
1. You measured DaMi's performance on this exam, before and after every improvement.
1. You graded DaMi's answers using your own data mining expertise.
1. You backed your improvements with numbers and kept a log of how your exam evolved, ready for your final presentation!

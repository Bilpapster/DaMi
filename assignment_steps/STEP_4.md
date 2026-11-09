# 💪 DaMi Step 4: upSKILLing!

> Can an old dog learn new tricks?

## Prerequisites

Please make sure you have completed Steps 1, 2, and (optionally) 3 before starting this one.

## 🎬 DO

0. Activate your virtual environment.

1. Start a kaggle notebook and the UI. Optionally start the observability stack.

1. Study [Agent Skills](https://agentskills.io/) and search for any relevant existing files in the code base.

   > _Hint_: DaMi does not load skills by itself. Read and follow the instructions in `skills/README.md` to make this work out of the box.

1. Leveraging your Data Mining expertise and what you have learned in this course, create 3 skills for DaMi. For example, one skill could be a complex outlier detection workflow that first uses `kmeans` to identify microclusters and then performs post-processing to identify outliers. Be creative and add the new skills in the appropriate folder of the code base.

1. Find ways to test out DaMi's new skills. Add more datasets, create test cases and/or ask more complex, open-ended data mining questions!

## 🤔💭 THINK AND ANSWER

1. What is the difference between a tool and a skill in the context of DaMi?

1. Try adding all skills at the system prompt and removing them from `skills/`. Try the same test cases with and without skills (i.e., in the system prompt). In which case is DaMi performing better and why? What is the impact on the token usage in each case?

1. After all, when would you advise a friend to use skills and when not to do so?

## 📝 RECAP

Congratulations! You have successfully completed the fourth step of the assignment. Here is what you did in this step:
1. You learnt about agent skills and understood their difference from the tools.
1. You created your own skills for DaMi, encapsulating your human data mining expertise.
1. You observed in practice the impact of using skills on DaMi's performance and token usage.
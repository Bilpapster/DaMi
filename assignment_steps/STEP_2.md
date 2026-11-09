# 🕵️ DaMi Step 2: DaMi tools, not dummy tools!

> Helping DaMi do the job the right way.

## Prerequisites

Please make sure you have completed Step 1 before starting this one.

## 🎬 DO

0. Activate your virtual environment.

1. Inspect the MCP tools that DaMi can use. Run `ALLOWED_ORIGINS=http://localhost:6275,http://127.0.0.1:6275  uv run --with mcp==2.3.0 mcp dev src/dami/mcp_server/server.py`. This opens an MCP Inspector window in your browser that allows you to run tools without an LLM. Connect to the "uv" server and click on "Tools" from the top menu.

1. Start with the `add` tool. Try to invoke it with two numbers of your preference and observe the result. Then browse through the rest of the tools. Take a closer look at their name, description, and arguments. Try to identify things that do not look quite right. This will be very helpful for answering some of the questions at the end of this step!

1. Call `kmeans` on `customers`, then `plot_clusters` with the `result_id` and open the `saved_to` path. See the produced clustering plot. It doesn't feel quite right, does it?

1. Try to find where these tools live in the code base. First read only the names and docstrings of these tools/functions. This is actually what DaMi sees, not the code. Then, read through their code. Try to identify flaws throughout. Test out your fixes by disconnecting from the server (top right button) and then connecting again to reload the tools.

1. Add a new tool, `suggest_k`, that can help DaMi choose the number of clusters when applying `kmeans` (e.g., using the elbow method). Run `dami kaggle start` and ask DaMi something that requires clustering. Is DaMi using the tool all the times? Why/Why not? Iterate to help DaMi improve its tool calling.

1. Add at least two new tools for outlier detection. Write a proper name and documentation for these tools. Then write the source code and restart the `dami ui` for your chages to take effect. Verify that DaMi can now answer questions that explicitly or implicitly require outlier detection.

## 🤔💭 THINK AND ANSWER

1. Are all tool descriptions concise, accurate, and informative? What did you change to improve them? How did you verify that your fixes worked as expected?

1. What is the main flaw in the `kmeans` tool that produces such a poor clustering result? Is it at the documentation or at the implementation level? Should the fix be applied to any other tool as well? How did you verify that your fix works?

1. After adding the `suggest_k` tool, was DaMi able to use it every time you expect it to do so? Why or why not? What could you do to enforce that DaMi always uses the `suggest_k` tool before using `k_means`?

1. After adding the outlier detection tools, was DaMi able to use them effectively when solving the task at hand required to do so? Are there any edge cases (e.g., input table size) that you, as the tool designer, need to take into account? What did you do in this case?


## 📝 RECAP

Congratulations! You have successfully completed the second step of the assignment. Here is what you did in this step:
1. You inspected the MCP server and the tools that DaMi has access to.
1. You ran the tools yourself without an LLM.
1. You spotted flaws in the tool docstrings and implementations.
1. You fixed the flaws and directly observed the improvements in DaMi's performance.
1. You used your human expertise to equip DaMi with new tools.

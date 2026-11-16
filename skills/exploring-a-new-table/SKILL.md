---
name: exploring-a-new-table
description: First look at a table you have not analysed yet. Use it when the user asks what a table contains, or before any analysis of a table you have not described in this conversation.
---

# Exploring a new table

Follow these steps in order. Do not start clustering or plotting before step 3.

1. Call `list_tables` to check that the table exists and to read its short description.
   If the user's name for the table does not match exactly, pick the closest table and say which one you used.
2. Call `describe_table` with the exact table name. Read the columns, their meaning, the statistics and the sample rows.
3. Write a short summary for the user:
   - how many rows and columns the table has, and what one row represents;
   - which columns are numeric (usable by the clustering tools) and which are not;
   - anything that needs care before an analysis: missing values, very different value ranges between
     columns, extreme values, or columns that look like ids.
4. Suggest one or two analyses that fit this table (for example segments, groups, or unusual rows), and ask
   the user which one to run. Do not run them yet.

Use only numbers that the tools returned. If a tool fails, say so and do not guess the values.

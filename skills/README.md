# Agent Skills (Step 4)

An *Agent Skill* is a folder with a `SKILL.md` file: a short name and description at the top
(frontmatter), then instructions, and optionally scripts or reference files. The agent sees only
the name and description of each skill. It loads the full instructions only when it needs them
("progressive disclosure"). This keeps the context small, which matters a lot for a 9B model.

## Example skill

This folder already has one skill that you can use as a template:
[`exploring-a-new-table/SKILL.md`](exploring-a-new-table/SKILL.md). It tells DaMi how to take a
first look at a table before it analyses it.

```
skills/
  exploring-a-new-table/     <- the example
    SKILL.md
  your-new-skill/            <- add your own skills next to it
    SKILL.md
```

A `SKILL.md` starts with a name (it must match the folder name) and a description. The description
is what DaMi reads to decide when to use the skill, so make it say *when* the skill is useful:

```markdown
---
name: exploring-a-new-table
description: First look at a table you have not analysed yet. Use it when ...
---

# Exploring a new table

1. Call `list_tables` ...
2. ...
```

## Plug the skills into DaMi

DaMi does not load this folder by itself. Strands has a plugin for it, `AgentSkills`:

```python
from strands.vended_plugins.skills import AgentSkills

AgentSkills(skills=["./skills/"])
```

It is up to you to find where DaMi's agent is built, and to plug `AgentSkills` in there. Once it
works, DaMi gets a new tool, `skills`, and you can see in Langfuse (or in the "Under the hood"
section of the UI) when DaMi loads a skill.

Read more: https://agentskills.io and the Strands documentation ("Skills").

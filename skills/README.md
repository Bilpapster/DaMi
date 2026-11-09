# Agent Skills (Case 5, option A)

An *Agent Skill* is a folder with a `SKILL.md` file: a short name and description at the top
(frontmatter), then instructions, and optionally scripts or reference files. The agent sees only
the name and description of each skill. It loads the full instructions only when it needs them
("progressive disclosure"). This keeps the context small, which matters a lot for a 9B model.

Example layout:

```
skills/
  choosing-a-clustering-method/
    SKILL.md
  outlier-investigation/
    SKILL.md
```

Example `SKILL.md`:

```markdown
---
name: outlier-investigation
description: Step-by-step method to find and explain unusual rows in a table.
---
1. Describe the table first ...
2. ...
```

Load skills in DaMi (in `src/dami/agent.py`):

```python
from strands.vended_plugins.skills import AgentSkills

Agent(..., plugins=[AgentSkills(skills=["./skills/"])])
```

Read more: https://agentskills.io and the Strands documentation ("Skills").

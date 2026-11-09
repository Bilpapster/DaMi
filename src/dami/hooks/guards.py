"""Harness task (Case 4, optional module): a guard for expensive or risky tool calls.

A prompt can *ask* the model not to run DBSCAN on 500,000 rows. A guard in the
harness *makes sure* it does not happen. Write a hook that looks at each tool
call before it runs and decides: allow it, cancel it with a helpful message
(for example "sample the table first"), or ask the human.

Ideas for rules:
- block `dbscan` on tables with more than N rows;
- block `save_path` values outside the workspace folder;
- ask the user to confirm (see "interrupts" in the Strands documentation).

Use `BeforeToolCallEvent`: `event.tool_use["name"]`, `event.tool_use["input"]`, and
`event.cancel_tool = "<message for the model>"`.
"""

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry


class ToolGuard(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check)

    def check(self, event: BeforeToolCallEvent) -> None:
        # TODO (Case 4): your rules here
        pass

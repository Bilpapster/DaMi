"""Harness task (Case 2): a tool-call budget.

Small models sometimes call the same tool again and again. A *budget* is a
harness rule that stops this: after `max_tool_calls` tool calls in one run,
every new tool call is cancelled with a message that tells the model to answer
with what it already has.

How to use it, after you implement it:

    from dami.hooks.budget import ToolBudget
    agent = build_agent(extra_hooks=[ToolBudget(max_tool_calls=6)])

Hints:
- `BeforeInvocationEvent` fires once at the start of each run (reset the counter there).
- `BeforeToolCallEvent` fires before each tool call. Set `event.cancel_tool = "<message>"`
  to stop the call. The model receives your message as the tool result.
"""

from strands.hooks import BeforeInvocationEvent, BeforeToolCallEvent, HookProvider, HookRegistry


class ToolBudget(HookProvider):
    def __init__(self, max_tool_calls: int = 6):
        self.max_tool_calls = max_tool_calls
        self.calls = 0

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_start)
        registry.add_callback(BeforeToolCallEvent, self.on_tool)

    def on_start(self, event: BeforeInvocationEvent) -> None:
        # TODO: reset the counter
        pass

    def on_tool(self, event: BeforeToolCallEvent) -> None:
        # TODO: count the call; when the budget is used up, cancel the tool call
        pass

"""Protect your laptop: limit how much memory the tool server may use.

Some tool calls can need a huge amount of memory (try to find out which ones, and why!).
Without a limit, the operating system may freeze, or kill processes when the memory is full.
With this limit, such a call fails with a MemoryError inside the tool, and DaMi keeps working.

Set DAMI_TOOL_MEMORY_GB in .env to change the limit (0 = no limit). This works on Linux.
On macOS it may be ignored, and on Windows it is not available.
"""

import os
import sys


def limit_memory() -> None:
    gb = float(os.getenv("DAMI_TOOL_MEMORY_GB", "4") or 0)
    if gb <= 0 or sys.platform == "win32":
        return
    try:
        import resource

        _, hard = resource.getrlimit(resource.RLIMIT_DATA)
        limit = int(gb * 1024**3)
        if hard != resource.RLIM_INFINITY:
            limit = min(limit, hard)
        resource.setrlimit(resource.RLIMIT_DATA, (limit, hard))
    except (ImportError, ValueError, OSError):
        pass  # not supported here: run without a limit

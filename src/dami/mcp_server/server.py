"""DaMi's hands: an MCP server that offers data-mining tools to any MCP client.

The agent starts this server as a child process and talks to it over stdin/stdout.
You can also start it alone and test the tools without any LLM:

    mcp dev src/dami/mcp_server/server.py
"""

from mcp.server.mcpserver import MCPServer

from dami.mcp_server.safety import limit_memory
from dami.mcp_server.tools import clustering_tools, data_tools, misc_tools, plot_tools

limit_memory()  # protects your laptop: see safety.py

mcp = MCPServer("DaMi")

data_tools.register(mcp)
clustering_tools.register(mcp)
plot_tools.register(mcp)
misc_tools.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

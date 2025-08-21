# MCP Servers for gpt-oss reference tools

This directory contains MCP servers for the reference tools in the [gpt-oss](https://github.com/openai/gpt-oss) repository.
You can set up these tools behind MCP servers and use them in your applications.
For inference service that integrates with MCP, you can also use these as reference tools.

In particular, this directory contains a `build-system-prompt.py` script that will generate exactly the same system prompt as `reference-system-prompt.py`.
The build system prompt script show case all the care needed to automatically discover the tools and construct the system prompt before feeding it into Harmony.

## Usage

```bash
# Install the dependencies
uv pip install -r requirements.txt
```

Single command (activate venv and run over STDIO):

```bash
~/python/mcp-venv/bin/mcp run -t stdio /home/ineersa/python/gpt-oss/gpt-oss-mcp-server/python_server.py:mcp
~/python/mcp-venv/bin/mcp run -t stdio /home/ineersa/python/gpt-oss/gpt-oss-mcp-server/browser_server.py:mcp
```

You can now use MCP inspector or any STDIO-compatible client to play with the tools.

Browser server backend:
- The browser server now uses a SearxNG-backed SimpleBrowserTool (no proprietary Exa API).
- Configure your SearxNG instance URL via SEARXNG_URL (defaults to http://server:8088):
  SEARXNG_URL=http://your-searx-host:8088 ~/python/mcp-venv/bin/mcp run -t stdio /home/ineersa/python/gpt-oss/gpt-oss-mcp-server/browser_server.py:mcp

Logging:
- By default, logs are written to files and not to STDERR to avoid interfering with STDIO transport.
  - python_server.py -> ~/python/logs/python_server.log
  - browser_server.py -> ~/python/logs/browser_server.log
- You can override the path with MCP_LOG_FILE and the level with MCP_LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL). Example:
  MCP_LOG_FILE=/tmp/python_server.log MCP_LOG_LEVEL=DEBUG ~/python/mcp-venv/bin/mcp run -t stdio /home/ineersa/python/gpt-oss/gpt-oss-mcp-server/python_server.py:mcp

To compare the system prompt and see how to construct it via MCP service discovery, see `build-system-prompt.py`.
This script will generate exactly the same system prompt as `reference-system-prompt.py`.

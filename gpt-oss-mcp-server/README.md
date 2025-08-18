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

Logging and STDERR:
- By default (MCP_QUIET_STDERR=1), these STDIO servers suppress DEBUG/INFO/WARNING to avoid noisy STDERR output that can confuse STDIO clients. ERROR and CRITICAL are still emitted.
- To re-enable full library logging (including INFO), set MCP_QUIET_STDERR=0 before launching, e.g.:
  MCP_QUIET_STDERR=0 /home/ineersa/python/mcp-venv/bin/mcp run -t stdio /home/ineersa/python/gpt-oss/gpt-oss-mcp-server/python_server.py:mcp

To compare the system prompt and see how to construct it via MCP service discovery, see `build-system-prompt.py`.
This script will generate exactly the same system prompt as `reference-system-prompt.py`.

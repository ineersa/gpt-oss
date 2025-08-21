from mcp.server.fastmcp import FastMCP
from gpt_oss.tools.python_docker.docker_tool import PythonTool
from openai_harmony import Message, TextContent, Author, Role

# Configure logging to write to file (no STDERR) by default
import os
import logging
from pathlib import Path

# Default log path: ~/python/logs/pytho_server.log (can be overridden)
_log_file = os.environ.get("MCP_LOG_FILE")
if not _log_file:
    _log_dir = Path(os.path.expanduser("~/python/logs"))
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file = str(_log_dir / "python_server.log")

# File-only logging; no StreamHandler to STDERR
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.FileHandler(_log_file, encoding="utf-8")],
    force=True,
)

# Pass lifespan to server
mcp = FastMCP(
    name="python",
    instructions=r"""
Use this tool to execute Python code in your chain of thought. The code will not be shown to the user. This tool should be used for internal reasoning, but not for code that is intended to be visible to the user (e.g. when creating plots, tables, or files).
When you send a message containing python code to python, it will be executed in a stateless docker container, and the stdout of that process will be returned to you.
""".strip(),
)


@mcp.tool(
    name="python",
    title="Execute Python code",
    description="""
Use this tool to execute Python code in your chain of thought. The code will not be shown to the user. This tool should be used for internal reasoning, but not for code that is intended to be visible to the user (e.g. when creating plots, tables, or files).
When you send a message containing python code to python, it will be executed in a stateless docker container, and the stdout of that process will be returned to you.
    """,
    annotations={
        # Harmony format don't want this schema to be part of it because it's simple text in text out
        "include_in_prompt": False,
    })
async def python(code: str) -> str:
    tool = PythonTool()
    messages = []
    async for message in tool.process(
            Message(author=Author(role=Role.TOOL, name="python"),
                    content=[TextContent(text=code)])):
        messages.append(message)
    return "\n".join([message.content[0].text for message in messages])


if __name__ == "__main__":
    import anyio
    from mcp.server.stdio import stdio_server

    async def _main() -> None:
        async with stdio_server() as (read, write):
            await mcp.run(read, write)

    anyio.run(_main)

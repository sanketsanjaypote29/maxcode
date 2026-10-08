import shutil
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from maxcode.mcp.maxcode_mcp_config import load_maxcode_mcp_configs
from maxcode.observability.logger import get_logger

logger = get_logger(__name__)

async def get_maxcode_mcp_tools() -> dict:
    """Connect to all configured mcp servers and return their tools."""
    configs = load_maxcode_mcp_configs()
    for config in configs.values():
        command = config.get("command")
        resolved_command = shutil.which(command) if command else None
        if not resolved_command:
            continue

        if command.lower() == "npx" and resolved_command.lower().endswith((".cmd", ".bat")):
            node = shutil.which("node")
            npx_cli = Path(resolved_command).parent / "node_modules" / "npm" / "bin" / "npx-cli.js"
            if node and npx_cli.is_file():
                config["command"] = node
                config["args"] = [str(npx_cli), *config.get("args", [])]
                continue

        config["command"] = resolved_command

    logger.info(f"Connecting to MCP servers: {list(configs.keys())}")
    client = MultiServerMCPClient(configs)
    tools = await client.get_tools()
    logger.info(f"Loaded {len(tools)} tools from MCP servers")
    return tools
    

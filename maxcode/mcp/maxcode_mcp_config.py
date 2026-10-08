import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


_CONFIG_PATH = Path(__file__).parent.parent /"maxcode_mcp_server.json"


def load_maxcode_mcp_configs() -> dict:
    """
    Return mcp_servers dict from maxcode_mcp_servers.json with env vars resolved.
    CWD is injected at load time so ${CWD} in the config always resolved to the
    directory where maxcode was launched - not the package install location."""
    os.environ.setdefault("CWD", str(Path.cwd()))
    raw = json.loads(_CONFIG_PATH.read_text())

    def resolve(value):
        if isinstance(value, str):
            return re.sub(r"\$\{(\w+)\}", lambda match: os.getenv(match.group(1), ""), value)
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            return {key: resolve(item) for key, item in value.items()}
        return value

    return resolve(raw).get("mcp_servers", {})


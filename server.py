import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from netmiko import ConnectHandler


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_NODES_FILE = BASE_DIR / "nodes.txt"
env_path = BASE_DIR / ".env"
load_dotenv(env_path)


mcp = FastMCP(
    name="cisco-cli-lab",
    instructions=(
        "Read-only access to the Cisco lab. List routers first, then run "
        "single-line Cisco CLI commands beginning with 'show' or 'ping'"
    ),
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
    streamable_http_path="/mcp",
)


@dataclass(frozen=True)
class Router:
    name: str
    host: str
    port: int


_NODE_PATTERN = re.compile(
    r"\{\s*(?P<name>[A-Za-z0-9_-]+)\s*:\s*"
    r"\{\s*(?P<host>[A-Za-z0-9_.:-]+)\s*:\s*(?P<port>\d+)\s*}\s*}"
)


def _nodes_path() -> Path:
    configured = os.getenv("CISCO_NODES_FILE")
    if not configured:
        return DEFAULT_NODES_FILE
    path = Path(configured).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def load_routers(path: Path | None = None) -> dict[str, Router]:
    """Load the compact ``{name: {host: port}}`` entries from nodes.txt."""
    nodes_path = path or _nodes_path()
    try:
        contents = nodes_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot read router inventory {nodes_path}: {exc}") from exc

    routers: dict[str, Router] = {}
    for match in _NODE_PATTERN.finditer(contents):
        router = Router(
            name=match.group("name"),
            host=match.group("host"),
            port=int(match.group("port")),
        )
        key = router.name.casefold()
        if key in routers:
            raise RuntimeError(f"Duplicate router name in {nodes_path}: {router.name}")
        routers[key] = router

    if not routers:
        raise RuntimeError(f"No router entries found in {nodes_path}")
    return routers


def _legacy_env_values() -> dict[str, str]:
    """Read the original ``key: value`` .env syntax used by this lab."""
    env_path = BASE_DIR / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)", stripped)
        if match:
            values[match.group(1).casefold()] = match.group(2).strip().strip("'\"")
    return values


def get_credentials() -> tuple[str, str]:
    legacy = _legacy_env_values()
    username = os.getenv("CISCO_USERNAME") or legacy.get("username")
    password = os.getenv("CISCO_PASSWORD") or legacy.get("password")
    if not username or not password:
        raise RuntimeError(
            "Missing credentials. Set CISCO_USERNAME and CISCO_PASSWORD in .env."
        )
    return username, password


def get_router(name: str) -> Router:
    routers = load_routers()
    router = routers.get(name.strip().casefold())
    if router is None:
        available = ", ".join(item.name for item in routers.values())
        raise ValueError(f"Unknown router {name!r}. Available routers: {available}")
    return router


def validate_show_command(command: str) -> str:
    """Return a normalized command only when it is a safe, single-line show command."""
    normalized = command.strip()
    if not normalized:
        raise ValueError("Command cannot be empty")
    if not normalized.isprintable() or ";" in normalized:
        raise ValueError("Command must be a single CLI line without command separators")
    if not re.match(r"^show(?:\s|$)", normalized, flags=re.IGNORECASE):
        raise ValueError("Only commands beginning with 'show' are allowed")
    return normalized


def validate_ping_command(command: str) -> str:
    """Return a normalized command only when it is a single-line ping command."""
    normalized = command.strip()
    if not normalized:
        raise ValueError("Ping command cannot be empty")
    if not normalized.isprintable() or ";" in normalized:
        raise ValueError("Command must be a single CLI line without command separators")
    if not re.match(r"^ping\s+\S", normalized, flags=re.IGNORECASE):
        raise ValueError("Only complete commands beginning with 'ping' are allowed")
    return normalized


def run_cisco_command(router_name: str, command: str) -> str:
    router = get_router(router_name)
    username, password = get_credentials()
    device: dict[str, object] = {
        "device_type": os.getenv("NETMIKO_DEVICE_TYPE", "cisco_ios"),
        "host": router.host,
        "port": router.port,
        "username": username,
        "password": password,
        "conn_timeout": int(os.getenv("CISCO_CONNECT_TIMEOUT", "10")),
    }

    enable_secret = os.getenv("CISCO_ENABLE")
    if enable_secret:
        device["secret"] = enable_secret

    try:
        with ConnectHandler(**device) as connection:
            if enable_secret:
                connection.enable()
            output = connection.send_command(
                command,
                read_timeout=int(os.getenv("CISCO_READ_TIMEOUT", "30")),
            )
    except Exception as exc:
        raise RuntimeError(
            f"SSH command failed on {router.name} ({router.host}:{router.port}): {exc}"
        ) from exc
    return output.strip()


@mcp.tool(
    name="list_cisco_routers",
    title="List Cisco Routers",
    description="List the router names available in the Cisco lab inventory.",
)
def list_cisco_routers() -> list[str]:
    return [router.name for router in load_routers().values()]


@mcp.tool(
    name="cisco_show_version",
    title="Cisco Show Version",
    description="Run the read-only 'show version' command on a named lab router.",
)
def cisco_show_version(router: str) -> str:
    return run_cisco_command(router, "show version")


@mcp.tool(
    name="cisco_show_command",
    title="Run Cisco Show Command",
    description=(
        "Run one read-only, single-line Cisco CLI command beginning with 'show' "
        "on a named lab router. Examples: 'show clock', 'show interfaces brief', "
        "or 'show route'."
    ),
)
def cisco_show_command(router: str, command: str) -> str:
    return run_cisco_command(router, validate_show_command(command))


@mcp.tool(
    name="cisco_ping",
    title="Ping from Cisco Router",
    description=(
        "Run one single-line Cisco CLI ping command on a named lab router. The "
        "complete command must begin with 'ping'. Additional Cisco ping options "
        "are accepted, for example: 'ping 172.16.0.2 source 172.16.0.1'."
    ),
)
def cisco_ping(router: str, command: str) -> str:
    return run_cisco_command(router, validate_ping_command(command))


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

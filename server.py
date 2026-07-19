import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from netmiko import ConnectHandler


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_NODES_FILE = BASE_DIR / "nodes.json"
env_path = BASE_DIR / ".env"
load_dotenv(env_path)


mcp = FastMCP(
    name="cisco-cli-lab",
    instructions=(
        "Guarded, non-configuring access to the Cisco lab. List routers first, "
        "then run printable, single-line Cisco CLI commands beginning with "
        "'show' or 'ping'"
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


def load_routers() -> dict[str, Router]:
    """Load routers from the JSON inventory in nodes.json."""
    with DEFAULT_NODES_FILE.open(encoding="utf-8") as inventory:
        nodes = json.load(inventory)

    routers: dict[str, Router] = {}
    for name, connection in nodes.items():
        router = Router(
            name=name,
            host=connection["host"],
            port=connection["port"],
        )
        routers[name.casefold()] = router
    return routers


def get_credentials() -> tuple[str, str]:
    username = os.getenv("CISCO_USERNAME")
    password = os.getenv("CISCO_PASSWORD")
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
    """Return a normalized, printable, single-line show command."""
    normalized = command.strip()
    if not normalized:
        raise ValueError("Command cannot be empty")
    if not normalized.isprintable():
        raise ValueError("Command must not contain non-printable characters")
    if not re.match(r"^show(?:\s)", normalized, flags=re.IGNORECASE):
        raise ValueError("Only commands beginning with 'show' are allowed")
    return normalized


def validate_ping_command(command: str) -> str:
    """Return a normalized command only when it is a single-line ping command."""
    normalized = command.strip()
    if not normalized:
        raise ValueError("Ping command cannot be empty")
    if not normalized.isprintable():
        raise ValueError("Command must not contain non-printable characters")
    if not re.match(r"^ping\s+\S", normalized, flags=re.IGNORECASE):
        raise ValueError("Only complete commands beginning with 'ping' are allowed")
    return normalized


def run_cisco_command(router_name: str, command: str) -> str:
    router = get_router(router_name)
    username, password = get_credentials()
    enable_secret = os.getenv("CISCO_ENABLE")
    device: dict[str, object] = {
        "device_type": "cisco_ios",
        "host": router.host,
        "port": router.port,
        "username": username,
        "password": password,
        "secret": enable_secret,
        "conn_timeout": 10,
    }

    try:
        with ConnectHandler(**device) as connection:
            if enable_secret:
                connection.enable()
            output = connection.send_command(
                command,
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
    name="cisco_show_command",
    title="Run Cisco Show Command",
    description=(
        "Run one guarded, single-line Cisco CLI command beginning with 'show' "
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
    load_routers()
    try:
        mcp.run(transport="streamable-http")
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

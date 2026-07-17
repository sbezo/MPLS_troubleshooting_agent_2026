import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from netmiko import ConnectHandler


load_dotenv()


mcp = FastMCP(
    name="cisco-cli-lab",
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",
)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run_cisco_command(command: str) -> str:
    device = {
        "device_type": os.getenv("NETMIKO_DEVICE_TYPE", "cisco_ios"),
        "host": get_required_env("CISCO_HOST"),
        "username": get_required_env("CISCO_USERNAME"),
        "password": get_required_env("CISCO_PASSWORD"),
        "port": int(os.getenv("CISCO_PORT", "22")),
        "timeout": 10,
    }

    enable_secret = os.getenv("CISCO_ENABLE")
    if enable_secret:
        device["secret"] = enable_secret

    try:
        with ConnectHandler(**device) as conn:
            if enable_secret:
                conn.enable()
            output = conn.send_command(command, read_timeout=20)
            return output.strip()
    except Exception as exc:
        raise RuntimeError(f"SSH command failed: {exc}") from exc


@mcp.tool(
    name="cisco_show_version",
    title="Cisco Show Version",
    description="Run the Cisco 'show version' command.",
)
def cisco_show_version() -> str:
    return run_cisco_command("show version")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

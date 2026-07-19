import argparse
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = "http://127.0.0.1:8000/mcp"


async def run(args: argparse.Namespace) -> None:
    async with streamable_http_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "cisco_show_command",
                {"router": args.router, "command": args.command},
            )

    print(result.structuredContent["result"])    


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple Cisco lab MCP client",
        epilog='Example:\n  python client_simple.py --router PE1 --command "show clock"',
        )
    parser.add_argument("--router", required=True)
    parser.add_argument("--command", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))

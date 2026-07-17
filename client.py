"""Deterministic Python client for demonstrating MCP calls."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"


def print_step(number: int, operation: str, details: str = "") -> None:
    print(f"\n{number}. {operation}")
    if details:
        print(details)


def result_value(result: Any) -> Any:
    """Extract the useful value from an MCP CallToolResult."""
    if result.structuredContent is not None:
        structured = result.structuredContent
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured

    text_items = [item.text for item in result.content if item.type == "text"]
    return "\n".join(text_items)


async def call_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    print(f"Request: tools/call {name}({json.dumps(arguments)})")
    result = await session.call_tool(name, arguments)
    value = result_value(result)
    if result.isError:
        raise RuntimeError(f"MCP tool {name} failed: {value}")
    return value


async def run(mcp_url: str, router: str, list_only: bool) -> None:
    timeout = httpx.Timeout(connect=10, read=None, write=30, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as http_client:
        async with streamable_http_client(
            mcp_url,
            http_client=http_client,
        ) as (read_stream, write_stream, get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                print_step(1, "initialize", f"Connecting to {mcp_url}")
                server = await session.initialize()
                print(f"Server: {server.serverInfo.name} {server.serverInfo.version}")
                print(f"Session ID: {get_session_id()}")

                print_step(2, "tools/list", "Discovering tools exposed by MCP")
                tools = (await session.list_tools()).tools
                for tool in tools:
                    print(f"- {tool.name}: {tool.description}")

                print_step(3, "tools/call: list_cisco_routers")
                routers = await call_tool(session, "list_cisco_routers", {})
                print(f"Response: {json.dumps(routers, indent=2)}")

                if list_only:
                    return

                print_step(4, "tools/call: cisco_show_version")
                output = await call_tool(
                    session,
                    "cisco_show_version",
                    {"router": router},
                )
                print(f"Response from {router}:\n{output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic calls against the Cisco lab MCP server."
    )
    parser.add_argument(
        "--mcp-url",
        default=os.getenv("MCP_URL", DEFAULT_MCP_URL),
        help=f"MCP endpoint (default: {DEFAULT_MCP_URL})",
    )
    parser.add_argument(
        "--router",
        default="P0",
        help="Router used for show version (default: P0)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Stop after listing MCP tools and routers.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args.mcp_url, args.router, args.list_only))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

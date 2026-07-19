# MPLS Troubleshooting Agent Demo

A small demo for troubleshooting an MPLS lab with an AI agent. It exposes Cisco routers through a local [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server, allowing the agent to list devices and run guarded `show` and `ping` commands.

The included topology contains provider, route-reflector, and customer-edge routers. Router endpoints are configured as JSON in `nodes.json`, while `topology.txt` describes their links.

## Setup

Requires Python 3.10+ and SSH access to the lab routers.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Update `nodes.json` with the SSH address and port of every router.

Create `.env` with the lab credentials:

```dotenv
CISCO_USERNAME=your_username
CISCO_PASSWORD=your_password
```

If your devices require an enable secret, you can also add:

```dotenv
CISCO_ENABLE=your_enable_secret
```

Do not commit `.env` because it contains credentials.

## Run the demo

Start the MCP server:

```bash
python server.py
```

By default, the server is available at `http://127.0.0.1:8000/mcp`.

In another terminal, activate the same virtual environment and test the `cisco_show_command` tool with the deterministic Python client:

```bash
source .venv/bin/activate
python client_simple.py --router PE1 --command "show mpls forwarding"
```

The client requires both `--router` and `--command`. It is intentionally minimal and calls only the `cisco_show_command` MCP tool.

# MPLS Troubleshooting Agent Demo

A small demo for troubleshooting an MPLS lab with an AI agent. It exposes Cisco routers through a local [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server, allowing the agent to list devices and run guarded `show` and `ping` commands.

The included topology contains provider, route-reflector, and customer-edge routers. Router endpoints are configured in `nodes.txt`, while `topology.txt` describes their links.

## Setup

Requires Python 3.10+ and SSH access to the lab routers.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` with the lab credentials:

```dotenv
CISCO_USERNAME=your_username
CISCO_PASSWORD=your_password
```

## Run the demo

Start the MCP server:

```bash
python server.py
```

In another terminal, you can test MCP server with deterministic python client:   

list the available routers or run a diagnostic command:

```bash
python client.py --list-only
python client.py --router PE1 --command "show mpls forwarding"
python client.py --router PE1 --ping "ping 172.16.0.2 source 172.16.0.1"
```

By default, the server is available at `http://127.0.0.1:8000/mcp`.

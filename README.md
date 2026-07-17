# Cisco lab MCP server

A minimal, read-only MCP server that connects to the routers in `nodes.txt` over
SSH using one shared set of credentials. It currently exposes:

- `list_cisco_routers` — returns the configured router names.
- `cisco_show_version(router)` — runs `show version` on one named router.
- `cisco_show_command(router, command)` — runs any permitted single-line command
  beginning with `show`.
- `cisco_ping(router, command)` — runs a complete single-line Cisco `ping`
  command, including optional source, count, VRF, or other CLI arguments.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


Inventory entries use the existing compact format:

```text
{PE1: {192.0.2.10:22}}
```

Start the server:

```bash
source .venv/bin/activate
python server.py
```

The streamable HTTP MCP endpoint is `http://127.0.0.1:8000/mcp`. Set `MCP_HOST`
to `0.0.0.0` only when remote clients must reach it and the network is trusted.

Example MCP client configuration for a server already running locally:

```json
{
  "mcpServers": {
    "cisco-lab": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## Deterministic Python client

`client.py` automates the same MCP protocol flow shown in the `curl` examples.
There is no LLM, API key, tool selection, or reasoning involved:

```text
Python client
    -> initialize MCP session
    -> tools/list
    -> tools/call list_cisco_routers
    -> tools/call cisco_show_command {"router": "P0", "command": "show version"}
    -> print the MCP response
```

Run `server.py` in the first terminal. In a second terminal, start the
client:

```bash
source .venv/bin/activate
python client.py
```

Choose another router:

```bash
python client.py --router PE1
```

Choose any read-only `show` command:

```bash
python client.py --router PE1 --command "show clock"
python client.py --router P0 --command "show interfaces brief"
```

Commands that do not begin with `show`, contain a newline, or use a semicolon
command separator are rejected by the MCP server.

Run a ping through the MCP tool:

```bash
python client.py --router P0 --ping "ping 127.0.0.1"
python client.py --router PE1 --ping "ping 172.16.0.2 source 172.16.0.1"
```

The command must begin with `ping` and contain arguments after it. Multiline and
semicolon-separated commands are rejected.

Only demonstrate initialization, tool discovery, and router listing:

```bash
python client.py --list-only
```

The client prints each MCP operation, the negotiated session ID, discovered
tools, arguments sent to `tools/call`, and the returned router output.

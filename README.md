# JLCPCB Parts MCP Server

Originally created by [@nvsofts](https://github.com/nvsofts).

## What is this

An MCP server that assists with finding parts for JLCPCB's PCBA (PCB Assembly) service.

## Example conversation

Here is an example of searching for ferrite beads classified as Basic Parts.
![Example conversation](images/sample_conversation.png)

Additionally, the following page demonstrates selecting resistor values for a buck DC-DC converter.
https://claude.ai/share/9f02f1a4-7b38-48fb-b29a-f10cf1e608ba

## Setup

This server uses the [JLC PCB SMD Assembly Component Catalogue](https://github.com/yaqwsx/jlcparts) as its database.
You will need the `cache.sqlite3` file provided there as split ZIP files. As of April 2025, the files go up to `cache.z19`.

Set up a Python environment where MCP is available, and specify `server.py` as the server.
You also need to set the `JLCPCB_DB_PATH` environment variable to the path of the database.

Below is an example configuration for Claude Desktop.

```json
{
  "mcpServers": {
    "JLCPCB parts": {
      "command": "python",
      "args": [
        "path/to/server.py"
      ],
      "env": {
        "JLCPCB_DB_PATH": "path/to/database.sqlite3"
      }
    }
  }
}
```

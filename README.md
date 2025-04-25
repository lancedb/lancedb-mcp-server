## LanceDB MCP server

This is a basic, serveless MCP server that uses LanceDB to store and retrieve data. It is intended to be used as a reference for building complex MCP apps with LanceDB.

It provides 3 tools:
* Ingest docs
* Retrieve docs
* Get table details

## Installation
Just add the following config to your claude mcp config file:

```
{
  "mcpServers": {
    "lancedb": {
      "command": "uv",
      "args": [
        "--directory",
        "/Path/to/your/lancedb_mcp",
        "run",
        "/path/to/your/mcp/lancedb_mcp.py"
      ]
    }
  }
}
```

## Ingest docs
Embed your docs and store them into lancedb for retreival. Here's an example of ingesting an entire blog into lancedb.
<img width="827" alt="Screenshot 2025-04-25 at 12 32 00 PM" src="https://github.com/user-attachments/assets/b973161b-4537-4aef-a4cc-e812762d1aeb" />

## Retrieve docs
Query your docs. Here's an example of querying lancedb for a blog post.
<img width="762" alt="Screenshot 2025-04-25 at 12 34 41 PM" src="https://github.com/user-attachments/assets/40b4ff27-0c5b-46ab-97ab-d6d03af364cf" />


## Get table details
Get table details. Here's an example of getting table details.
<img width="866" alt="Screenshot 2025-04-25 at 12 40 44 PM" src="https://github.com/user-attachments/assets/5d1243f7-b0ac-4c55-aaf9-74cd72117ef4" />



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

## Retrieve docs
Query your docs. Here's an example of querying lancedb for a blog post.


## Get table details
Get table details. Here's an example of getting table details.



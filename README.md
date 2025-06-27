# LanceDB MCP Server

A **production-ready**, serverless MCP server that uses LanceDB to store and retrieve data. This implementation provides comprehensive table management, document operations, and advanced search capabilities with enterprise-grade optimizations.

## Features

- **Table Management** - Create, manage, and delete tables with custom schemas and vector dimensions
- **Document Management** - Automatic document ingestion with vector embeddings, updates, and deletions
- **Search Operations** - Vector similarity search and hybrid search with multiple distance metrics
- **Batch Processing** - Efficient bulk operations for large datasets
- **Multi-language Support** - Unicode, emoji, and special character handling
- **Modular Architecture** - Clean separation of concerns across specialized modules
- **Serverless Design** - Stdio-based communication for Claude integration

## Installation

Add the following config to your Claude MCP config file:

```json
{
  "mcpServers": {
    "lancedb": {
      "command": "uv",
      "args": [
        "--directory",
        "/Path/to/your/lancedb-mcp-server",
        "run",
        "/path/to/your/lancedb_mcp.py"
      ]
    }
  }
}
```

## Available Tools

### Core Tools (Backward Compatible)
- **Ingest docs** - Embed and store documents into LanceDB
- **Retrieve docs** - Query documents with vector similarity search
- **Get table details** - Get comprehensive table information

### Advanced Tools (New)
- **Table Management** - Create, list, and delete tables with custom schemas
- **Document Operations** - Update and delete documents with filtering
- **Hybrid Search** - Advanced search with filtering and multiple distance metrics
- **Batch Operations** - Efficient bulk document processing

## Usage Examples

### Ingest docs
Embed your docs and store them into LanceDB for retrieval. Here's an example of ingesting an entire blog into LanceDB.

### Retrieve docs
Query your docs with advanced search capabilities. Here's an example of querying LanceDB for a blog post.

### Get table details
Get comprehensive table details including schema, row counts, and statistics.

## Configuration

Configure the server using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LANCEDB_URI` | Database location | `~/lancedb` |
| `TABLE_NAME` | Default table name | `lancedb-mcp-table` |
| `EMBEDDING_FUNCTION` | Embedding model type | `sentence-transformers` |
| `MODEL_NAME` | Specific model to use | `all-MiniLM-L6-v2` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Architecture

The project follows a clean, modular architecture:

```
src/mcp_lancedb/
├── server.py              # Main MCP server entry point
├── cli.py                 # Command-line interface
├── core/                  # Core infrastructure
│   ├── config.py         #   Configuration management
│   ├── logger.py         #   Logging infrastructure  
│   ├── connection.py     #   Database connection management
│   └── schemas.py        #   Data schema definitions
└── operations/            # Business logic modules
    ├── table_management.py    #   Table CRUD operations
    ├── document_management.py #   Document ingestion and updates
    └── search_operations.py   #   Vector and hybrid search
```

## Testing

```bash
# Run all tests
python run_tests.py all

# Run unit tests only
python run_tests.py unit

# Run integration tests
python run_tests.py integration
```

## Performance

- **7/7 integration tests passing**
- **Sub-second performance** for typical operations
- **Enterprise-grade optimizations** with connection reuse and table caching
- **Efficient batch processing** for large datasets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass: `python run_tests.py all`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Acknowledgments

- [LanceDB](https://lancedb.github.io/lancedb/) for the vector database
- [MCP](https://github.com/modelcontextprotocol/python-sdk) for the Model Context Protocol
- [sentence-transformers](https://www.sbert.net/) for embedding models

#!/usr/bin/env python3
"""
LanceDB MCP Server - Production-Ready Implementation

This is a production-ready, serverless MCP server that uses LanceDB to store and retrieve data.
It provides comprehensive table management, document operations, and advanced search capabilities.

Features:
- Table Management: Create, manage, and delete tables with custom schemas
- Document Management: Automatic document ingestion with vector embeddings
- Search Operations: Vector similarity search and hybrid search with multiple metrics
- Batch Processing: Efficient bulk operations for large datasets
- Multi-language Support: Unicode, emoji, and special character handling
- Modular Architecture: Clean separation of concerns across specialized modules
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our package
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mcp_lancedb.server import main

if __name__ == "__main__":
    main() 
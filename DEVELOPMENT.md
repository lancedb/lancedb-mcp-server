# MCP LanceDB - Development Guide

## 🚀 **Status**

✅ **100% Pass Rate** - 72/72 tests passing  
⚡ **~8.5 seconds** - Full test suite execution  

## 🛠️ **Quick Start**

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Quick verification
pytest tests/ -q

# Integration tests (most critical)
pytest tests/integration/ -v
```

## 📁 **Key Files**

- `src/mcp_lancedb/server.py` - MCP server with tool definitions
- `src/mcp_lancedb/document_management.py` - Document ingestion
- `src/mcp_lancedb/search_operations.py` - Vector search
- `src/mcp_lancedb/table_management.py` - Table operations
- `src/mcp_lancedb/connection.py` - Database connectivity

## ⚡ **Essential Rules**

1. **100% test pass rate required**
2. **Integration tests prove functionality**
3. **Use user's environment variables for embedding model**
4. **Parameter order**: `(table_name, data)` for mutations, `(query, table_name)` for searches
5. **Clear error messages with user guidance**

## 🎯 **Success Metrics**

- ✅ All integration tests passing (proves system works)
- ✅ Simplified architecture (no custom embedding complexity)
- ✅ Fast development cycle (<9 second test suite)

---

For detailed architecture, testing patterns, and troubleshooting, see **Cursor Rules** in `.cursor/rules/`

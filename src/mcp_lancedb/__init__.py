"""MCP LanceDB - Vector database operations for Claude via Model Context Protocol."""

__version__ = "0.1.0"

# Import all operations from submodules
from .operations.table_management import (
    create_table,
    delete_table,
    list_tables,
    table_count,
    table_details,
    table_stats
)

from .operations.document_management import (
    ingest_docs,
    update_documents,
    delete_documents
)

from .operations.search_operations import (
    query_table,
    hybrid_search
)

# Import optimization and best practices
from .core.optimization import optimizer

# Import core components
from .core.config import (
    LANCEDB_URI,
    TABLE_NAME,
    EMBEDDING_FUNCTION,
    MODEL_NAME,
    model,
    logger
)

from .core.connection import (
    get_connection,
    get_all_tables,
    get_table_cached,
    clear_table_cache,
    analyze_query_performance
)

from .core.schemas import (
    Schema
)

# Import server and CLI
from .server import run as run_server
from .cli import main as cli_main

# Convenience functions for LanceDB best practices
def optimize_table(table_name: str):
    """Apply LanceDB best practices optimization to a table."""
    return optimizer.optimize_table_performance(table_name)

def table_versions(table_name: str):
    """Get version information and manage table versions."""
    return optimizer.manage_table_versions(table_name)

def get_index_stats(table_name: str):
    """Get detailed index performance statistics following LanceDB best practices."""
    try:
        from .core.connection import sanitize_table_name
        safe_table_name = sanitize_table_name(table_name)
        # LanceDB Best Practice: Use cached table objects
        table = get_table_cached(safe_table_name)
        
        stats = {
            "table_name": table_name,
            "indices": table.list_indices(),
            "basic_stats": table.stats()
        }
        
        # LanceDB Best Practice: Monitor index coverage
        try:
            index_stats = table.index_stats()
            stats["index_performance"] = index_stats
            
            # Check for optimization opportunities
            if 'num_unindexed_rows' in index_stats:
                unindexed = index_stats['num_unindexed_rows']
                if unindexed > 0:
                    stats["optimization_needed"] = f"{unindexed:,} unindexed rows detected"
                else:
                    stats["index_coverage"] = "Excellent - all rows indexed"
        except Exception as e:
            stats["index_performance"] = f"Detailed stats not available: {e}"
        
        return stats
    except Exception as e:
        return {"error": f"Error getting index stats: {e}"}

def analyze_query_perf(table_name: str, query: str = "test", top_k: int = 5):
    """Analyze query performance using LanceDB best practices."""
    try:
        from .core.connection import sanitize_table_name
        safe_table_name = sanitize_table_name(table_name)
        
        # Create a sample query function for analysis
        def create_search_query(table, query, top_k):
            return table.search(query).limit(top_k).select(["doc", "_distance"])
        
        # Use LanceDB's analyze_plan functionality
        analysis = analyze_query_performance(safe_table_name, create_search_query, query, top_k)
        return analysis
    except Exception as e:
        return {"error": f"Error analyzing query performance: {e}"}

# Public API - Keep this organized and clean
__all__ = [
    # Version
    "__version__",
    
    # Table Management Operations
    "create_table",
    "delete_table",
    "list_tables",
    "table_count", 
    "table_details",
    "table_stats",
    
    # Document Management Operations
    "ingest_docs",
    "update_documents",
    "delete_documents",
    
    # Search Operations
    "query_table",
    "hybrid_search",
    
    # LanceDB Best Practices & Optimization
    "optimizer",
    "optimize_table",
    "table_versions",
    "get_index_stats",
    "analyze_query_perf",
    
    # Core Components
    "LANCEDB_URI",
    "TABLE_NAME", 
    "EMBEDDING_FUNCTION",
    "MODEL_NAME",
    "model",
    "logger",
    "get_connection",
    "get_all_tables",
    "Schema",
    
    # Entry Points
    "run_server",
    "cli_main"
] 
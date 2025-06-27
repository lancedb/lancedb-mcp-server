"""MCP LanceDB server implementation - Modular version."""

from mcp.server.fastmcp import FastMCP
from typing import List, Optional, Union
from .core.config import logger

# Initialize MCP server
mcp = FastMCP("LanceDB MCP Server")

@mcp.prompt()
def lancedb_help() -> str:
    """Get help about using the LanceDB tools"""
    return """I can help you with LanceDB operations:

1. Table Management:
   - Use 'create_table' to create new tables (automatically uses embedding model dimensions)
   - Use 'list_tables' to see all available tables with details
   - Use 'table_count' to get just the total number of tables (lightweight)
   - Use 'table_details' for basic table info with enhanced schema display
   - Use 'table_stats' for detailed table statistics with field categorization
   - Use 'delete_table' to remove tables
   - Example: {"table_name": "my_table", "additional_fields": {"category": "str"}}

2. Document Management:
   - Use 'ingest_docs' to store documents (single or batch)
   - Configure embedding model via environment variables
   - Use 'update_documents' to modify existing documents
   - Use 'delete_documents' to remove documents
   - Example: {"docs": ["Hello world"], "embedding_model": "all-mpnet-base-v2"}

3. Search Operations:
   - Use 'query_table' for basic vector search
   - Use 'hybrid_search' for combined vector + scalar filtering
   - Support for multiple distance metrics (cosine, dot, euclidean)
   - Example: {"query": "Hello", "top_k": 5, "filter_expr": "metadata > 0.5"}

Would you like to try any of these operations?"""

# Table Management Tools
@mcp.tool()
def create_table(
    table_name: str,
    schema: Optional[dict] = None
):
    """
    Create a new LanceDB table with automatic vector dimensions from the configured embedding model.

    Args:
        table_name (str): Name of the table to create
        schema (dict): Optional custom schema definition. Must include:
            - doc: str (required) - Document field
            - vector: Vector(ndims) (required) - Vector field with dimensions (automatically determined)
            - Additional fields are optional

    Returns:
        str: Success or error message
    """
    from .operations.table_management import create_table as create_table_op
    return create_table_op(table_name, schema)

@mcp.tool()
def table_details(
    table_name: Optional[str] = None,
    db_uri: Optional[str] = None,
):
    """
    Get the details of a LanceDB table with enhanced schema display.

    Args:
        table_name (str): The name of the table to get details of (optional, uses default table if not specified)
        db_uri (str): Optional database URI (uses default if not specified)

    Returns:
        dict: A dictionary of the table details with enhanced schema information
    """
    from .operations.table_management import table_details as table_details_op
    return table_details_op(table_name)

@mcp.tool()
def table_stats(
    table_name: Optional[str] = None,
):
    """
    Get detailed statistics for a LanceDB table with field categorization.

    Args:
        table_name (str): The name of the table to get statistics for (optional, uses default table if not specified)

    Returns:
        dict: A dictionary containing detailed table statistics including row count, schema info, and field categorization
    """
    from .operations.table_management import table_stats as table_stats_op
    return table_stats_op(table_name)

@mcp.tool()
def list_tables():
    """
    List all available tables in the LanceDB database.

    Returns:
        dict: A dictionary containing table names and basic information
    """
    from .operations.table_management import list_tables as list_tables_op
    return list_tables_op()

@mcp.tool()
def table_count():
    """
    Get the total number of tables in the LanceDB database.
    
    This is a lightweight operation that only counts tables without
    loading their detailed information.

    Returns:
        dict: A dictionary containing just the total table count
    """
    from .operations.table_management import table_count as table_count_op
    return table_count_op()

@mcp.tool()
def delete_table(table_name: str):
    """
    Delete a LanceDB table completely.

    Args:
        table_name (str): Name of the table to delete

    Returns:
        str: Success or error message
    """
    from .operations.table_management import delete_table as delete_table_op
    return delete_table_op(table_name)

# Document Management Tools
@mcp.tool()
def ingest_docs(docs: Union[str, List[str]], table_name: Optional[str] = None, auto_create_table: bool = True):
    """
    Ingest documents into a LanceDB table.

    Args:
        docs (Union[str, List[str]]): Document or list of documents to ingest
        table_name (str): Optional table name to ingest into (uses default if not specified)
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        str: Success or error message
    """
    from .operations.document_management import ingest_docs as ingest_docs_op
    return ingest_docs_op(table_name, docs, auto_create_table)

@mcp.tool()
def update_documents(
    table_name: str,
    filter_expr: str,
    updates: dict
):
    """
    Update documents in a LanceDB table based on a filter expression.

    Args:
        table_name (str): Name of the table containing documents to update
        filter_expr (str): Filter expression to select which documents to update
        updates (dict): Dictionary of field updates to apply

    Returns:
        str: Success or error message
    """
    from .operations.document_management import update_documents as update_documents_op
    return update_documents_op(table_name, filter_expr, updates)

@mcp.tool()
def delete_documents(
    table_name: str,
    filter_expr: str
):
    """
    Delete documents from a LanceDB table based on a filter expression.

    Args:
        table_name (str): Name of the table containing documents to delete
        filter_expr (str): Filter expression to select which documents to delete

    Returns:
        str: Success or error message
    """
    from .operations.document_management import delete_documents as delete_documents_op
    return delete_documents_op(table_name, filter_expr)

# Search Operations Tools
@mcp.tool()
def query_table(query: str,
                table_name: Optional[str] = None,
                top_k: int = 5,
                query_type: str = "vector",
                auto_create_table: bool = False):
    """
    Query a LanceDB table with a query string and return the top k results.

    Args:
        query (str): The query string to search for
        table_name (str): Optional table name to query (uses default if not specified)
        top_k (int): The number of results to return (default: 5, set to 0 to just check existence)
        query_type (str): The type of query to perform (default: "vector")
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        List[dict]: A list of matching documents if top_k > 0, or bool if top_k = 0
    """
    from .operations.search_operations import query_table as query_table_op
    return query_table_op(query, table_name, top_k, query_type, auto_create_table)

@mcp.tool()
def hybrid_search(
    query: str,
    table_name: Optional[str] = None,
    filter_expr: Optional[str] = None,
    top_k: int = 5,
    metric: str = "cosine",
    distance_threshold: Optional[float] = None,
    auto_create_table: bool = False
):
    """
    Perform a hybrid search combining vector similarity with scalar filtering.

    Args:
        query (str): The query string for vector search
        table_name (str): Optional table name to search (uses default if not specified)
        filter_expr (str): Optional filter expression for scalar filtering
        top_k (int): Number of results to return (default: 5, set to 0 to just check existence)
        metric (str): Distance metric to use ("cosine", "dot", "l2", "euclidean", "hamming")
        distance_threshold (float): Optional maximum distance threshold for filtering results
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        List[dict]: A list of matching documents with similarity scores if top_k > 0, or bool if top_k = 0
    """
    from .operations.search_operations import hybrid_search as hybrid_search_op
    return hybrid_search_op(query, table_name, filter_expr, top_k, metric, distance_threshold, auto_create_table)

# LanceDB Best Practices & Optimization Tools
@mcp.tool()
def optimize_table(table_name: str) -> dict:
    """
    Apply LanceDB best practices optimization to a table for better performance.
    
    Includes:
    - Scalar indexing for fast filtering
    - Vector index optimization
    - Full-text search indexing
    - Table storage optimization
    - Index prewarming
    
    Args:
        table_name (str): Name of the table to optimize
        
    Returns:
        dict: Optimization results and performance recommendations
    """
    from .core.optimization import optimizer
    return optimizer.optimize_table_performance(table_name)

@mcp.tool()
def table_versions(table_name: str) -> dict:
    """
    Manage table versions and get version history information.
    
    LanceDB automatically versions every table mutation for:
    - Time-travel debugging
    - Atomic rollbacks
    - ML reproducibility
    - Branching workflows
    
    Args:
        table_name (str): Name of the table to get version info for
        
    Returns:
        dict: Version information and cleanup status
    """
    from .core.optimization import optimizer
    return optimizer.manage_table_versions(table_name)

@mcp.tool()
def index_stats(table_name: str) -> dict:
    """
    Get detailed index performance statistics for a table.
    
    Provides insights into:
    - Index usage patterns
    - Query performance metrics
    - Optimization recommendations
    
    Args:
        table_name (str): Name of the table to analyze
        
    Returns:
        dict: Index statistics and performance metrics
    """
    try:
        from .core.connection import get_fresh_connection
        db = get_fresh_connection()
        table = db.open_table(table_name)
        
        # Get comprehensive index information
        result = {
            "table_name": table_name,
            "indices": table.list_indices(),
            "stats": table.stats()
        }
        
        # Try to get detailed index stats (Enterprise feature)
        try:
            result["index_performance"] = table.index_stats()
        except Exception as e:
            result["index_performance"] = f"Detailed index stats not available: {e}"
            result["recommendation"] = "Consider upgrading to LanceDB Enterprise for detailed index performance analytics"
        
        return result
        
    except Exception as e:
        return {"error": f"Error getting index stats: {e}"}

def run():
    """Run the MCP server."""
    logger.info("Starting LanceDB MCP Server (Modular Version)")
    mcp.run()

def main():
    """Main entry point for the MCP server."""
    run()

if __name__ == "__main__":
    main() 
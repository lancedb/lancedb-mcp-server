"""Core infrastructure modules for MCP LanceDB."""

from .config import (
    LANCEDB_URI,
    TABLE_NAME,
    EMBEDDING_FUNCTION,
    MODEL_NAME,
    model,
    logger
)
from .schemas import (
    Schema,
    create_custom_schema,
    create_schema_from_dict
)
from .connection import (
    get_connection,
    get_all_tables,
    get_table_cached,
    clear_table_cache,
    analyze_query_performance,
    verify_table_exists,
    open_table_with_retry,
    create_table_with_retry,
    sanitize_table_name
)
from .logger import (
    get_logger,
    set_log_level,
    log_exception,
    log_dict
)

__all__ = [
    # Config
    "LANCEDB_URI",
    "TABLE_NAME", 
    "EMBEDDING_FUNCTION",
    "MODEL_NAME",
    "model",
    "logger",
    # Schemas
    "Schema",
    "create_custom_schema", 
    "create_schema_from_dict",
    # Connection
    "get_connection",
    "get_all_tables", 
    "get_table_cached",
    "clear_table_cache",
    "analyze_query_performance",
    "verify_table_exists",
    "open_table_with_retry",
    "create_table_with_retry",
    "sanitize_table_name",
    # Logger
    "get_logger",
    "set_log_level", 
    "log_exception",
    "log_dict"
] 
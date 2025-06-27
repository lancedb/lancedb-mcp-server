"""Configuration settings for MCP LanceDB server."""

import os
import logging
from lancedb.embeddings import get_registry
from .logger import get_logger, set_log_level

# Get logger for this module
logger = get_logger("config")

# Set the log level based on environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO")
set_log_level(getattr(logging, log_level.upper()))

# Environment variables
LANCEDB_URI = os.environ.get("LANCEDB_URI", "~/lancedb")
TABLE_NAME = os.environ.get("TABLE_NAME", "lancedb-mcp-table")
EMBEDDING_FUNCTION = os.environ.get("EMBEDDING_FUNCTION", "sentence-transformers")
MODEL_NAME = os.environ.get("MODEL_NAME", "all-MiniLM-L6-v2")

# LanceDB Best Practices Configuration
# Consistency Settings (Enterprise Feature)
WEAK_READ_CONSISTENCY_INTERVAL = int(os.environ.get("LANCEDB_WEAK_READ_CONSISTENCY", "30"))  # seconds

# Performance Optimization Settings
AUTO_CREATE_INDICES = os.environ.get("LANCEDB_AUTO_CREATE_INDICES", "true").lower() == "true"
AUTO_OPTIMIZE_TABLES = os.environ.get("LANCEDB_AUTO_OPTIMIZE", "true").lower() == "true"
INDEX_CACHE_SIZE = int(os.environ.get("LANCEDB_INDEX_CACHE_SIZE", "1000"))  # MB
PREWARM_INDICES = os.environ.get("LANCEDB_PREWARM_INDICES", "true").lower() == "true"

# Versioning Configuration  
ENABLE_VERSIONING = os.environ.get("LANCEDB_ENABLE_VERSIONING", "true").lower() == "true"
MAX_VERSIONS_TO_KEEP = int(os.environ.get("LANCEDB_MAX_VERSIONS", "10"))
AUTO_CLEANUP_VERSIONS = os.environ.get("LANCEDB_AUTO_CLEANUP_VERSIONS", "true").lower() == "true"

# GPU Configuration (Enterprise Feature)
USE_GPU_INDEXING = os.environ.get("LANCEDB_USE_GPU_INDEXING", "false").lower() == "true"

# Initialize embedding model
model = get_registry().get(EMBEDDING_FUNCTION).create(name=MODEL_NAME)

logger.info(f"Initialized LanceDB MCP server configuration:")
logger.info(f"  - Database URI: {LANCEDB_URI}")
logger.info(f"  - Default table: {TABLE_NAME}")
logger.info(f"  - Embedding function: {EMBEDDING_FUNCTION}")
logger.info(f"  - Model: {MODEL_NAME}")
logger.info(f"  - Vector dimensions: {model.ndims()}")
logger.info(f"  - Performance optimizations: auto_indices={AUTO_CREATE_INDICES}, auto_optimize={AUTO_OPTIMIZE_TABLES}")
logger.info(f"  - Consistency: weak_read_interval={WEAK_READ_CONSISTENCY_INTERVAL}s")
logger.info(f"  - Versioning: enabled={ENABLE_VERSIONING}, max_versions={MAX_VERSIONS_TO_KEEP}")
logger.info(f"  - GPU indexing: enabled={USE_GPU_INDEXING}") 
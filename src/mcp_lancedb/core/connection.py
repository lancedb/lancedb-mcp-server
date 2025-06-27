"""Centralized connection management for LanceDB MCP server."""

import time
import re
import lancedb
from .config import LANCEDB_URI, logger

# Global connection instance for reuse (LanceDB best practice)
_db_connection = None

# Global table cache for reuse (LanceDB best practice #2)
_table_cache = {}

def get_connection():
    """Get a reused database connection following LanceDB best practices."""
    global _db_connection
    
    if _db_connection is None:
        from .config import WEAK_READ_CONSISTENCY_INTERVAL
        
        # LanceDB Enterprise: Use weak_read_consistency_interval_seconds 
        # LanceDB OSS: Use read_consistency_interval as timedelta
        connection_config = {}
        if WEAK_READ_CONSISTENCY_INTERVAL > 0:
            try:
                # Try Enterprise parameter first
                connection_config['weak_read_consistency_interval_seconds'] = WEAK_READ_CONSISTENCY_INTERVAL
                _db_connection = lancedb.connect(LANCEDB_URI, **connection_config)
                logger.debug(f"Connected with Enterprise consistency: {WEAK_READ_CONSISTENCY_INTERVAL}s")
            except (TypeError, ValueError):
                # Fallback to OSS parameter
                from datetime import timedelta
                connection_config = {'read_consistency_interval': timedelta(seconds=WEAK_READ_CONSISTENCY_INTERVAL)}
                try:
                    _db_connection = lancedb.connect(LANCEDB_URI, **connection_config)
                    logger.debug(f"Connected with OSS consistency: {WEAK_READ_CONSISTENCY_INTERVAL}s")
                except TypeError:
                    # No consistency parameters supported
                    _db_connection = lancedb.connect(LANCEDB_URI)
                    logger.debug("Connected without consistency parameters")
        else:
            _db_connection = lancedb.connect(LANCEDB_URI)
            logger.debug("Connected with default consistency")
    
    return _db_connection

def get_table_cached(table_name: str, force_refresh: bool = False):
    """
    Get a cached table object following LanceDB best practices.
    
    LanceDB Best Practice: "table = db.open_table() should be called once 
    and used for all subsequent table operations"
    
    Args:
        table_name (str): Name of the table
        force_refresh (bool): Force refresh the cached table
        
    Returns:
        LanceTable: Cached table object
    """
    global _table_cache
    
    # Force refresh or table not in cache
    if force_refresh or table_name not in _table_cache:
        try:
            db = get_connection()
            table = db.open_table(table_name)
            _table_cache[table_name] = table
            logger.debug(f"Cached table object for: {table_name}")
        except Exception as e:
            logger.error(f"Failed to cache table {table_name}: {e}")
            raise e
    
    return _table_cache[table_name]

def clear_table_cache(table_name: str = None):
    """
    Clear table cache when tables are modified or deleted.
    
    Args:
        table_name (str): Specific table to remove from cache, or None for all
    """
    global _table_cache
    
    if table_name:
        _table_cache.pop(table_name, None)
        logger.debug(f"Cleared cache for table: {table_name}")
    else:
        _table_cache.clear()
        logger.debug("Cleared all table cache")

def analyze_query_performance(table_name: str, query_function, *args, **kwargs):
    """
    Analyze query performance following LanceDB best practices.
    
    Uses table.analyze_plan() to identify performance bottlenecks
    as recommended in LanceDB Enterprise documentation.
    
    Args:
        table_name (str): Name of the table
        query_function: Function that returns a LanceDB query object
        *args, **kwargs: Arguments to pass to query_function
        
    Returns:
        dict: Performance analysis results
    """
    try:
        table = get_table_cached(table_name)
        query = query_function(table, *args, **kwargs)
        
        # Use LanceDB's analyze_plan for performance analysis
        if hasattr(query, 'analyze_plan'):
            plan_analysis = query.analyze_plan()
            
            # Extract key performance metrics
            analysis = {
                "table_name": table_name,
                "query_plan": str(plan_analysis),
                "performance_insights": _extract_performance_insights(plan_analysis),
                "optimization_recommendations": _get_optimization_recommendations(table, plan_analysis)
            }
            
            logger.info(f"Query performance analysis completed for {table_name}")
            return analysis
        else:
            return {"error": "analyze_plan not available in this LanceDB version"}
            
    except Exception as e:
        logger.error(f"Failed to analyze query performance: {e}")
        return {"error": str(e)}

def _extract_performance_insights(plan_analysis):
    """Extract key performance metrics from query plan."""
    plan_str = str(plan_analysis)
    insights = []
    
    # Look for performance indicators mentioned in LanceDB docs
    if "bytes_read" in plan_str:
        import re
        bytes_match = re.search(r'bytes_read=(\d+)', plan_str)
        if bytes_match:
            bytes_read = int(bytes_match.group(1))
            gb_read = bytes_read / (1024**3)
            insights.append(f"Data read: {gb_read:.2f} GB")
    
    if "iops" in plan_str:
        iops_match = re.search(r'iops=(\d+)', plan_str)
        if iops_match:
            iops = int(iops_match.group(1))
            insights.append(f"I/O operations: {iops}")
    
    if "LanceScan" in plan_str:
        insights.append("Full table scan detected - consider adding indices")
    
    if "index_comparisons" in plan_str:
        comp_match = re.search(r'index_comparisons=(\d+)', plan_str)
        if comp_match:
            comparisons = int(comp_match.group(1))
            insights.append(f"Vector comparisons: {comparisons:,}")
    
    return insights

def _get_optimization_recommendations(table, plan_analysis):
    """Get optimization recommendations based on query plan analysis."""
    recommendations = []
    plan_str = str(plan_analysis)
    
    # Check index coverage as recommended in LanceDB docs
    try:
        index_stats = table.index_stats()
        if 'num_unindexed_rows' in index_stats:
            unindexed = index_stats['num_unindexed_rows']
            if unindexed > 0:
                recommendations.append(f"Index optimization needed: {unindexed:,} unindexed rows")
    except:
        recommendations.append("Enable detailed index monitoring with LanceDB Enterprise")
    
    # Analyze query patterns
    if "LanceScan" in plan_str and "bytes_read" in plan_str:
        recommendations.append("Add scalar indices for commonly filtered columns")
    
    if "KNNVectorDistance" in plan_str:
        recommendations.append("Consider optimizing vector index (IVF_PQ/IVF_HNSW_SQ)")
    
    if "RemoteTake" in plan_str:
        recommendations.append("Use .select() to limit returned columns for better performance")
    
    return recommendations

def get_all_tables():
    """
    Get all table names using proper LanceDB API.
    
    LanceDB's table_names() method has a default limit of 10. This function
    uses a sufficiently high limit to retrieve all tables in one call.
    
    Returns:
        list: List of all table names from LanceDB
    """
    try:
        db = get_connection()
        
        # Use a high limit to get all tables in one call
        # 1000 should be sufficient for most use cases
        table_names = list(db.table_names(limit=1000))
        
        logger.debug(f"LanceDB API found {len(table_names)} tables")
        return sorted(table_names)
        
    except Exception as e:
        logger.error(f"Failed to get table names via LanceDB API: {e}")
        return []

def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name to work around LanceDB persistence issues.
    
    LanceDB appears to have issues with certain table naming patterns:
    - Tables with underscores, hyphens, dots, or all-lowercase names 
      sometimes don't persist properly after creation
    - CamelCase names seem to work reliably
    
    CRITICAL FIX: This function was causing table access failures by changing
    CamelCase to lowercamelcase. Now it preserves existing CamelCase names.
    
    Args:
        table_name (str): Original table name
        
    Returns:
        str: Sanitized table name that should persist properly
    """
    original_name = str(table_name).strip()
    
    # Handle empty or whitespace-only names
    if not original_name:
        logger.warning("Empty table name provided, using default 'DefaultTable'")
        return "DefaultTable"
    
    # If the name is already CamelCase and alphanumeric, keep it as-is
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', original_name):
        # Already proper CamelCase, no sanitization needed
        return original_name
    
    # Convert to CamelCase to avoid persistence issues
    # This ensures the table will persist properly in LanceDB
    
    # Replace ALL non-alphanumeric characters with spaces, preserving word boundaries
    name = re.sub(r'[^a-zA-Z0-9]', ' ', original_name)
    
    # Split into words and capitalize each word properly
    words = [word for word in name.split() if word]
    camel_case = ''.join(word.capitalize() for word in words)
    
    # Ensure it starts with a capital letter (CamelCase pattern)
    if camel_case and not camel_case[0].isupper():
        camel_case = camel_case.capitalize()
    
    # Fallback to a default if we end up with nothing
    if not camel_case:
        camel_case = "Table" + str(hash(original_name) % 10000)
    
    if camel_case != original_name:
        logger.info(f"Table name sanitized: '{original_name}' -> '{camel_case}' (LanceDB compatibility)")
    
    return camel_case

def verify_table_exists(table_name: str, max_retries: int = 3) -> bool:
    """
    Verify a table exists using proper LanceDB API.
    
    Args:
        table_name (str): Name of the table to verify
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        bool: True if table exists and is accessible, False otherwise
    """
    for attempt in range(max_retries):
        try:
            db = get_connection()
            
            # Try to open the table directly - most efficient approach
            try:
                table = db.open_table(table_name)
                # Verify it's accessible by checking schema
                _ = table.schema
                logger.debug(f"Table {table_name} verified successfully")
                return True
            except Exception:
                # Table might not exist or name mismatch, check with table_names()
                table_names = db.table_names()
                
                # Check both exact name and potential variations
                name_variants = [
                    table_name,
                    table_name.lower(),
                    table_name.upper(),
                    table_name.capitalize()
                ]
                
                for variant in name_variants:
                    if variant in table_names:
                        try:
                            table = db.open_table(variant)
                            _ = table.schema
                            logger.debug(f"Table {table_name} verified as {variant}")
                            return True
                        except Exception as e:
                            logger.warning(f"Table {variant} exists but not accessible: {e}")
                
                logger.debug(f"Table {table_name} not found (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    continue
                return False
                
        except Exception as e:
            logger.warning(f"Error checking table existence (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue
            return False
    return False

def create_table_with_retry(table_name: str, schema, max_retries: int = 3):
    """
    Create a table with retry logic and proper verification.
    
    Args:
        table_name (str): Name of the table to create
        schema: The schema to use for table creation
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        tuple: (success: bool, message: str, table: object or None)
    """
    # Sanitize table name for LanceDB compatibility
    safe_table_name = sanitize_table_name(table_name)
    
    # CRITICAL FIX: Convert LanceDB Pydantic schema to PyArrow schema
    # LanceDB has persistence issues with Pydantic schemas containing embedding functions
    if hasattr(schema, 'to_arrow_schema'):
        try:
            # Convert to PyArrow schema for reliable persistence
            arrow_schema = schema.to_arrow_schema()
            logger.info(f"Converted Pydantic schema to PyArrow schema for table {safe_table_name}")
            schema = arrow_schema
        except Exception as e:
            logger.warning(f"Failed to convert schema to PyArrow, using original: {e}")
    elif hasattr(schema, '__fields__'):
        # Fallback: manually convert Pydantic to PyArrow
        try:
            import pyarrow as pa
            fields = []
            for field_name, field in schema.__fields__.items():
                if field_name == 'doc':
                    fields.append(pa.field('doc', pa.string()))
                elif field_name == 'vector':
                    # Extract dimensions from Vector type
                    vector_type = field.annotation
                    if hasattr(vector_type, '_size'):
                        dims = vector_type._size
                    else:
                        dims = 384  # Default dimensions
                    fields.append(pa.field('vector', pa.list_(pa.float32(), dims)))
                else:
                    # Basic type mapping
                    if field.annotation == str:
                        fields.append(pa.field(field_name, pa.string()))
                    elif field.annotation == int:
                        fields.append(pa.field(field_name, pa.int64()))
                    elif field.annotation == float:
                        fields.append(pa.field(field_name, pa.float64()))
                    else:
                        fields.append(pa.field(field_name, pa.string()))  # Fallback
            
            arrow_schema = pa.schema(fields)
            logger.info(f"Manually converted Pydantic schema to PyArrow for table {safe_table_name}")
            schema = arrow_schema
        except Exception as e:
            logger.warning(f"Manual schema conversion failed, using original: {e}")
    
    for attempt in range(max_retries):
        try:
            # Check if table already exists before creating
            if verify_table_exists(safe_table_name):
                logger.info(f"Table {safe_table_name} already exists and is accessible")
                db = get_connection()
                table = db.open_table(safe_table_name)
                return True, f"Table {table_name} already exists (stored as {safe_table_name})", table
            
            # Create the table
            db = get_connection()
            try:
                table = db.create_table(safe_table_name, schema=schema)
                logger.info(f"Created table {safe_table_name} on attempt {attempt + 1}")
                
                # Verify creation with extra retries
                if verify_table_exists(safe_table_name, max_retries=5):
                    logger.info(f"Table {safe_table_name} created and verified successfully")
                    if safe_table_name != table_name:
                        return True, f"Table {table_name} created successfully (stored as {safe_table_name} for LanceDB compatibility)", table
                    else:
                        return True, f"Table {table_name} created successfully", table
                else:
                    logger.warning(f"Table {safe_table_name} created but verification failed on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    
            except ValueError as e:
                if "already exists" in str(e).lower():
                    # Race condition - table was created between our check and create
                    logger.info(f"Table {safe_table_name} created concurrently on attempt {attempt + 1}")
                    if verify_table_exists(safe_table_name, max_retries=5):
                        db = get_connection()
                        table = db.open_table(safe_table_name)
                        if safe_table_name != table_name:
                            return True, f"Table {table_name} created successfully (stored as {safe_table_name}, concurrent)", table
                        else:
                            return True, f"Table {table_name} created successfully (concurrent)", table
                    else:
                        logger.warning(f"Concurrent table creation detected but verification failed on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            continue
                else:
                    logger.error(f"Unexpected error creating table on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return False, f"Error creating table: {e}", None
                        
        except Exception as e:
            logger.error(f"Error on table creation attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                return False, f"Error creating table after {max_retries} attempts: {e}", None
    
    return False, f"Failed to create table {table_name} after {max_retries} attempts", None

def open_table_with_retry(table_name: str, max_retries: int = 3):
    """
    Open a table with retry logic.
    
    Args:
        table_name (str): Name of the table to open
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        LanceTable: The opened table object
        
    Raises:
        Exception: If table cannot be opened after all retries
    """
    for attempt in range(max_retries):
        try:
            db = get_connection()
            table = db.open_table(table_name)
            # Verify the table is actually accessible
            _ = table.schema
            return table
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Failed to open table {table_name} (attempt {attempt + 1}): {e}")
                continue
            else:
                logger.error(f"Failed to open table {table_name} after {max_retries} attempts: {e}")
                raise e 
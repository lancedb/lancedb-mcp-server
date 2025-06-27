"""Table management operations for LanceDB MCP server."""

import lancedb
from typing import Optional
from ..core.config import LANCEDB_URI, TABLE_NAME, logger, AUTO_CREATE_INDICES, AUTO_OPTIMIZE_TABLES
from ..core.schemas import Schema, create_schema_from_dict
from ..core.logger import log_exception
from ..core.connection import get_connection, verify_table_exists, open_table_with_retry, create_table_with_retry, sanitize_table_name, clear_table_cache
from ..core.optimization import optimizer

def create_table(table_name: str, schema: Optional[dict] = None) -> str:
    """
    Create a new LanceDB table with optional custom schema.

    Args:
        table_name (str): Name of the table to create
        schema (dict): Optional custom schema definition

    Returns:
        str: Success or error message
    """
    try:
        logger.info(f"Creating new table: {table_name}")
        
        if schema:
            # Validate required fields
            if "doc" not in schema:
                return "Error: Custom schema must include 'doc' field of type str"
            if "vector" not in schema:
                return "Error: Custom schema must include 'vector' field of type Vector"
                
            try:
                CustomSchema = create_schema_from_dict(schema)
                success, message, table = create_table_with_retry(table_name, CustomSchema)
                return message
            except Exception as e:
                error_msg = f"Error creating table with custom schema: {str(e)}"
                logger.error(error_msg)
                log_exception(logger, error_msg)
                return f"Error: {error_msg}"
        else:
            # Use default schema with robust creation
            success, message, table = create_table_with_retry(table_name, Schema)
            
            # Apply LanceDB best practices optimization after successful creation
            if success and (AUTO_CREATE_INDICES or AUTO_OPTIMIZE_TABLES):
                try:
                    optimization_result = optimizer.optimize_table_performance(table_name)
                    if optimization_result.get("optimizations_applied"):
                        optimizations = optimization_result["optimizations_applied"]
                        message += f" Optimizations applied: {len(optimizations)} performance enhancements."
                        logger.info(f"Applied {len(optimizations)} optimizations to new table {table_name}")
                except Exception as opt_e:
                    logger.warning(f"Table created successfully but optimization failed: {opt_e}")
                    message += " (optimization skipped due to error)"
            
            return message
        
    except Exception as e:
        error_msg = f"Error creating table: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def delete_table(table_name: str) -> str:
    """
    Delete a LanceDB table completely, ensuring all data is removed.

    Args:
        table_name (str): Name of the table to delete

    Returns:
        str: Success or error message
    """
    try:
        logger.info(f"Deleting table: {table_name}")
        actual_table_name = sanitize_table_name(table_name)
        db = get_connection()
        
        # Refresh table names to ensure we have the current state
        initial_tables = set(db.table_names())
        
        # Check both original and sanitized names
        table_to_delete = None
        if table_name in initial_tables:
            table_to_delete = table_name
        elif actual_table_name in initial_tables:
            table_to_delete = actual_table_name
        else:
            return f"Error: Table {table_name} does not exist"
        
        # Try to open and get row count before deletion for verification
        try:
            table = db.open_table(table_to_delete)
            initial_row_count = len(table)
            logger.info(f"Table {table_to_delete} has {initial_row_count} rows before deletion")
        except Exception as e:
            logger.warning(f"Could not get initial row count: {e}")
            initial_row_count = "unknown"
            
        # Delete the table
        db.drop_table(table_to_delete)
        
        # LanceDB Best Practice: Clear table cache after modification
        clear_table_cache(table_to_delete)
        clear_table_cache(actual_table_name)  # Clear both names
        
        logger.info(f"Executed drop_table for {table_to_delete}")
        
        # Force multiple reconnections and verifications
        for attempt in range(3):
            # Create fresh connection
            db = get_connection()
            final_tables = set(db.table_names())
            
            if table_to_delete not in final_tables:
                logger.info(f"Successfully deleted table: {table_to_delete} (verified on attempt {attempt + 1})")
                return f"Table {table_name} deleted successfully (had {initial_row_count} rows)"
            
            # If table still exists, try again immediately
        
        # If we get here, deletion verification failed
        error_msg = f"Failed to delete table {table_to_delete} - table still exists after deletion attempts"
        logger.error(error_msg)
        
        # Try alternative deletion approach - delete all documents first
        try:
            logger.info(f"Attempting alternative deletion by clearing all data from {table_to_delete}")
            table = db.open_table(table_to_delete)
            # Delete all documents
            table.delete(where="true")  # Delete everything
            
            # Try drop_table again
            db.drop_table(table_to_delete)
            
            # Final verification
            db = get_connection()
            if table_to_delete not in db.table_names():
                logger.info(f"Successfully deleted table using alternative method: {table_to_delete}")
                return f"Table {table_name} deleted successfully using alternative method"
        except Exception as alt_e:
            logger.error(f"Alternative deletion method also failed: {alt_e}")
        
        return f"Error: {error_msg}"
        
    except Exception as e:
        error_msg = f"Error deleting table: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def list_tables() -> dict:
    """
    List all available tables in the LanceDB database.

    Returns:
        dict: A dictionary containing table names and basic information
    """
    try:
        logger.info("Listing all tables in database")
        
        # Use proper LanceDB API instead of filesystem operations
        from mcp_lancedb.core.connection import get_all_tables, get_connection
        table_names = get_all_tables()
        db = get_connection()
        
        if not table_names:
            logger.info("No tables found in database")
            return {"tables": [], "count": 0}
        
        # Get detailed information for each table with error handling
        tables_info = []
        for table_name in table_names:
            try:
                table = db.open_table(table_name)
                
                # Try multiple methods to get row count
                try:
                    num_rows = table.count_rows()
                except Exception:
                    try:
                        num_rows = len(table)
                    except Exception:
                        num_rows = 0
                
                table_info = {
                    "name": table_name,
                    "num_rows": num_rows
                }
                tables_info.append(table_info)
                
            except Exception as e:
                logger.warning(f"Could not access table {table_name}: {e}")
                # Still include the table in the list but mark it as inaccessible
                tables_info.append({
                    "name": table_name,
                    "num_rows": "inaccessible",
                    "error": str(e)
                })
        
        logger.info(f"Found {len(table_names)} tables in database")
        return {
            "tables": tables_info,
            "count": len(table_names)
        }
        
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return {"error": f"Error listing tables: {e}"}

def table_count() -> dict:
    """
    Get the total number of tables in the LanceDB database.
    
    This is a lightweight operation that only returns the count without
    loading table details for better performance.

    Returns:
        dict: A dictionary containing just the total table count
    """
    try:
        logger.info("Getting total table count")
        
        # Use proper LanceDB API to get table names only (optimized)
        from mcp_lancedb.core.connection import get_all_tables
        table_names = get_all_tables()
        
        count = len(table_names)
        logger.info(f"Total tables in database: {count}")
        
        return {
            "count": count,
            "message": f"Database contains {count} table{'s' if count != 1 else ''}"
        }
        
    except Exception as e:
        logger.error(f"Error getting table count: {e}")
        return {"error": f"Error getting table count: {e}"}

def table_details(table_name: Optional[str] = None) -> dict:
    """
    Get the details of a LanceDB table.

    Args:
        table_name (str): The name of the table to get details of

    Returns:
        dict: A dictionary of the table details
    """
    try:
        actual_table_name = table_name or TABLE_NAME
        safe_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Getting details for table: {actual_table_name}")
        
        # Use robust table existence check
        if not verify_table_exists(safe_table_name):
            return f"Error: Table {actual_table_name} does not exist or is not accessible"
        
        db = get_connection()
        table = db.open_table(safe_table_name)
        
        # Get accurate row count using multiple methods
        try:
            num_rows = table.count_rows()
            logger.debug(f"Row count from count_rows(): {num_rows}")
        except (AttributeError, Exception):
            try:
                num_rows = len(table)
                logger.debug(f"Row count from len(): {num_rows}")
            except Exception:
                try:
                    # Use head() to check if there's any data
                    sample = table.head(1)
                    if len(sample) > 0:
                        # If we have data, try to count all rows
                        all_data = table.to_pandas()
                        num_rows = len(all_data)
                        logger.debug(f"Row count from to_pandas(): {num_rows}")
                    else:
                        num_rows = 0
                        logger.debug("Table appears to be empty (head returned 0 rows)")
                except Exception as e:
                    logger.warning(f"All row counting methods failed: {e}")
                    num_rows = "Unknown"
        
        # Format schema for better readability with full details
        schema_info = {
            "fields": [],
            "summary": f"{len(table.schema)} fields total",
            "raw_schema_preview": str(table.schema)[:200] + "..." if len(str(table.schema)) > 200 else str(table.schema)
        }
        
        for field in table.schema:
            field_info = {
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable if hasattr(field, 'nullable') else "Unknown"
            }
            
            # Add vector dimension info for vector fields
            if "fixed_size_list" in str(field.type).lower():
                import re
                dim_match = re.search(r'fixed_size_list<.*?>\[(\d+)\]', str(field.type))
                if dim_match:
                    field_info["vector_dimensions"] = int(dim_match.group(1))
                    field_info["description"] = f"Vector field with {field_info['vector_dimensions']} dimensions"
            
            schema_info["fields"].append(field_info)
        
        details = {
            "name": actual_table_name,
            "num_rows": num_rows,
            "schema": schema_info,
        }
        
        logger.info(f"Retrieved details for table with {details['num_rows']} rows")
        return details
    except Exception as e:
        error_msg = f"Error getting table details: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def table_stats(table_name: str) -> dict:
    """
    Get detailed statistics about a table.

    Args:
        table_name (str): Name of the table to analyze

    Returns:
        dict: Detailed table statistics
    """
    try:
        safe_table_name = sanitize_table_name(table_name)
        logger.info(f"Getting detailed statistics for table: {table_name}")
        
        # Use robust table existence check
        if not verify_table_exists(safe_table_name):
            return f"Error: Table {table_name} does not exist or is not accessible"
        
        db = get_connection()
        table = db.open_table(safe_table_name)
        
        # Get row count using multiple methods for accuracy
        try:
            num_rows = table.count_rows()
        except Exception:
            try:
                num_rows = len(table)
            except Exception:
                num_rows = "Unknown"
        
        # Format schema for better readability with comprehensive details
        schema_info = {
            "fields": [],
            "field_count": len(table.schema),
            "summary": f"Table has {len(table.schema)} fields",
            "vector_fields": [],
            "text_fields": [],
            "other_fields": []
        }
        
        for field in table.schema:
            field_info = {
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable if hasattr(field, 'nullable') else "Unknown"
            }
            
            # Enhanced field categorization and analysis
            field_type_str = str(field.type).lower()
            
            if "fixed_size_list" in field_type_str:
                # Vector field
                import re
                dim_match = re.search(r'fixed_size_list<.*?>\[(\d+)\]', str(field.type))
                if dim_match:
                    dimensions = int(dim_match.group(1))
                    field_info["vector_dimensions"] = dimensions
                    field_info["category"] = "vector"
                    field_info["description"] = f"Vector field with {dimensions} dimensions"
                    schema_info["vector_fields"].append(field_info)
                else:
                    field_info["category"] = "vector"
                    field_info["description"] = "Vector field (dimensions unknown)"
                    schema_info["vector_fields"].append(field_info)
            elif "string" in field_type_str or field.name in ["doc", "document", "text", "content"]:
                # Text field
                field_info["category"] = "text"
                field_info["description"] = "Text/string field"
                schema_info["text_fields"].append(field_info)
            else:
                # Other field types
                if "int" in field_type_str:
                    field_info["category"] = "integer"
                    field_info["description"] = "Integer numeric field"
                elif "float" in field_type_str or "double" in field_type_str:
                    field_info["category"] = "float"
                    field_info["description"] = "Floating point numeric field"
                elif "bool" in field_type_str:
                    field_info["category"] = "boolean"
                    field_info["description"] = "Boolean true/false field"
                else:
                    field_info["category"] = "other"
                    field_info["description"] = f"Field of type {field.type}"
                
                schema_info["other_fields"].append(field_info)
            
            schema_info["fields"].append(field_info)
        
        # Build comprehensive statistics
        stats = {
            "table_name": safe_table_name,
            "row_count": num_rows,
            "schema": schema_info,
            "field_summary": {
                "total_fields": len(table.schema),
                "vector_fields": len(schema_info["vector_fields"]),
                "text_fields": len(schema_info["text_fields"]),
                "other_fields": len(schema_info["other_fields"])
            }
        }
        
        # Try to get additional metadata
        try:
            stats["last_modified"] = table.last_modified
        except AttributeError:
            stats["last_modified"] = "Not available"
        
        logger.info(f"Retrieved statistics for table: {safe_table_name}")
        return stats
    except Exception as e:
        error_msg = f"Error getting table statistics: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}" 
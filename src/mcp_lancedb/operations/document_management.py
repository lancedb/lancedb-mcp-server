"""Document management operations for LanceDB MCP server."""

import time
import lancedb
import pyarrow as pa
from typing import List, Optional, Union
from ..core.config import LANCEDB_URI, TABLE_NAME, model, logger
from ..core.schemas import Schema
from ..core.logger import log_exception
from ..core.connection import get_connection, verify_table_exists, open_table_with_retry, create_table_with_retry, sanitize_table_name

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using the configured model.
    
    Args:
        texts (List[str]): List of texts to generate embeddings for
    
    Returns:
        List[List[float]]: List of embedding vectors
    """
    try:
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        
        # Use lancedb's embedding function with the configured model
        embeddings = model.generate_embeddings(texts)
        
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise

def ingest_docs(table_name: Optional[str], docs: Union[str, List[str]], auto_create_table: bool = True) -> str:
    """
    Ingest documents into a LanceDB table using the configured embedding model.

    Args:
        table_name (str): Optional table name to ingest into
        docs (Union[str, List[str]]): Documents to ingest
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        str: Success or error message
    """
    try:
        actual_table_name = table_name or TABLE_NAME
        sanitized_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Attempting to ingest {len(docs) if isinstance(docs, list) else 1} document(s) into table: {actual_table_name}")
        
        # Input validation
        if not docs:
            return "Error: No documents provided. Please provide at least one document to ingest."
        
        if isinstance(docs, str):
            docs = [docs]
        
        validated_docs = []
        for i, doc in enumerate(docs):
            if doc is None:
                logger.warning(f"Document at index {i} is None, skipping")
                continue
            if not isinstance(doc, str):
                try:
                    doc = str(doc)
                except Exception:
                    logger.warning(f"Could not convert document at index {i} to string, skipping")
                    continue
            if not doc.strip():
                logger.warning(f"Document at index {i} is empty or whitespace only, skipping")
                continue
            validated_docs.append(doc.strip())
        
        if not validated_docs:
            return "Error: No valid documents found after validation. Ensure documents are non-empty strings."
        
        docs = validated_docs
        
        db = lancedb.connect(LANCEDB_URI)
        
        # Refresh table names to ensure current state
        table_names = db.table_names()
        logger.debug(f"Current tables in database: {table_names}")
        
        # Check for both original and sanitized table names
        table_to_use = None
        if actual_table_name in table_names:
            table_to_use = actual_table_name
        elif sanitized_table_name in table_names:
            table_to_use = sanitized_table_name
        
        if table_to_use:
            table = db.open_table(table_to_use)
            logger.info(f"Opened existing table: {table_to_use}")
            
            # Check if table vector dimensions match the configured model
            schema = table.schema
            vector_field = None
            for field in schema:
                if "fixed_size_list" in str(field.type).lower():
                    vector_field = field
                    break
            
            if vector_field:
                import re
                dim_match = re.search(r'fixed_size_list<.*?>\[(\d+)\]', str(vector_field.type))
                if dim_match:
                    table_dims = int(dim_match.group(1))
                    model_dims = model.ndims()
                    if table_dims != model_dims:
                        return f"Error: Table vector dimensions ({table_dims}) don't match your configured embedding model dimensions ({model_dims}). Please use a table with {model_dims} dimensions or change your embedding model to match the table."
            
            # Generate embeddings for the documents
            embeddings = get_embeddings(docs)
            
            # Format data according to existing schema
            table_data = []
            schema_fields = [field.name for field in schema]
            logger.debug(f"Existing table schema fields: {schema_fields}")
            
            # Find the vector field in the schema
            vector_field_name = None
            for field in schema:
                if "fixed_size_list" in str(field.type).lower():
                    vector_field_name = field.name
                    break
            
            logger.debug(f"Vector field identified as: {vector_field_name}")
            
            for i, doc in enumerate(docs):
                row_data = {}
                
                # Set the document content in the appropriate field
                if "doc" in schema_fields:
                    row_data["doc"] = doc
                else:
                    # Find the first string field that might be the document field
                    for field in schema:
                        if str(field.type).startswith("string"):
                            row_data[field.name] = doc
                            break
                    else:
                        # Fallback: use the first field
                        if schema_fields:
                            row_data[schema_fields[0]] = doc
                
                # Set the vector embedding if we have a vector field
                if vector_field_name and i < len(embeddings):
                    row_data[vector_field_name] = embeddings[i]
                
                # Add default values for all other required fields (but not vector fields)
                for field in schema:
                    field_name = field.name
                    field_type_str = str(field.type).lower()
                    
                    if field_name not in row_data and not field_type_str.startswith("fixed_size_list"):
                        # Add default values for non-vector fields
                        if "int" in field_type_str:
                            row_data[field_name] = 0
                        elif "double" in field_type_str or "float" in field_type_str:
                            row_data[field_name] = 0.0
                        elif "bool" in field_type_str:
                            row_data[field_name] = False
                        elif "string" in field_type_str:
                            row_data[field_name] = ""
                        elif "list" in field_type_str and not "fixed_size_list" in field_type_str:
                            row_data[field_name] = []
                        else:
                            # For complex types, try to set None or an appropriate default
                            row_data[field_name] = None
                            
                logger.debug(f"Created row data for doc {i}: {list(row_data.keys())}")
                
                table_data.append(row_data)
                
        else:
            # Table doesn't exist - check if auto-creation is allowed
            if not auto_create_table:
                return f"Error: Table {actual_table_name} does not exist or is not accessible. Set auto_create_table=True to create it automatically."
            
            # Generate embeddings for the documents
            embeddings = get_embeddings(docs)
            
            # Create table with default schema using robust creation
            success, message, table = create_table_with_retry(actual_table_name, Schema)
            if not success:
                return f"Error: Failed to auto-create table {actual_table_name}: {message}"
            logger.info(f"Auto-created new table: {actual_table_name}")
            
            # For new tables, create data with both doc and vector fields
            table_data = []
            for i, doc in enumerate(docs):
                row_data = {"doc": doc}
                if i < len(embeddings):
                    row_data["vector"] = embeddings[i]
                table_data.append(row_data)

        table.add(table_data)
        logger.info(f"Successfully added {len(table_data)} documents to table")

        return f"Successfully added {len(table_data)} documents to table {actual_table_name}"
    except Exception as e:
        error_msg = f"Error ingesting documents: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def update_documents(table_name: str, filter_expr: str, updates: dict) -> str:
    """
    Update documents in a table based on a filter expression.

    Args:
        table_name (str): Name of the table
        filter_expr (str): Filter expression to select documents
        updates (dict): Dictionary of fields to update

    Returns:
        str: Success or error message
    """
    try:
        actual_table_name = table_name
        sanitized_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Updating documents in table: {actual_table_name}")
        
        # Input validation
        if not filter_expr or not filter_expr.strip():
            return "Error: Filter expression cannot be empty. Specify a valid filter to select documents to update."
        
        if not updates or len(updates) == 0:
            return "Error: Updates dictionary cannot be empty. Specify at least one field to update."
        
        db = lancedb.connect(LANCEDB_URI)
        
        # Refresh table names to ensure current state
        table_names = db.table_names()
        logger.debug(f"Current tables in database: {table_names}")
        
        # Check for both original and sanitized table names
        table_to_use = None
        if actual_table_name in table_names:
            table_to_use = actual_table_name
        elif sanitized_table_name in table_names:
            table_to_use = sanitized_table_name
        
        if not table_to_use:
            return f"Error: Table {actual_table_name} does not exist. Create the table first using create_table() or ingest_docs()."
        
        table = db.open_table(table_to_use)
        logger.info(f"Opened existing table: {table_to_use}")
        
        # Validate that the table has data to update
        try:
            row_count = table.count_rows()
            if row_count == 0:
                logger.warning(f"Table {actual_table_name} is empty")
                return f"Warning: Table {actual_table_name} is empty. No documents to update."
        except Exception:
            # If count_rows() fails, continue anyway
            pass
        
        table.update(where=filter_expr, values=updates)
        logger.info("Successfully updated documents")
        return f"Documents updated successfully in table {actual_table_name}"
    except Exception as e:
        error_msg = f"Error updating documents: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def delete_documents(table_name: str, filter_expr: str) -> str:
    """
    Delete documents from a table based on a filter expression.

    Args:
        table_name (str): Name of the table
        filter_expr (str): Filter expression to select documents

    Returns:
        str: Success or error message
    """
    try:
        actual_table_name = table_name
        sanitized_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Deleting documents from table: {actual_table_name}")
        
        # Input validation
        if not filter_expr or not filter_expr.strip():
            return "Error: Filter expression cannot be empty. Specify a valid filter to select documents to delete."
        
        # Safety check for dangerous delete operations
        dangerous_filters = ["true", "1=1", "1 = 1"]
        if filter_expr.lower().strip() in dangerous_filters:
            logger.warning(f"Dangerous delete operation attempted with filter: {filter_expr}")
            return f"Warning: Filter '{filter_expr}' would delete ALL documents. Use delete_table() to delete the entire table instead."
        
        db = lancedb.connect(LANCEDB_URI)
        
        # Refresh table names to ensure current state
        table_names = db.table_names()
        logger.debug(f"Current tables in database: {table_names}")
        
        # Check for both original and sanitized table names
        table_to_use = None
        if actual_table_name in table_names:
            table_to_use = actual_table_name
        elif sanitized_table_name in table_names:
            table_to_use = sanitized_table_name
        
        if not table_to_use:
            return f"Error: Table {actual_table_name} does not exist. Cannot delete documents from non-existent table."
        
        table = db.open_table(table_to_use)
        logger.info(f"Opened existing table: {table_to_use}")
        
        # Get initial row count for reporting
        try:
            initial_count = table.count_rows()
            logger.debug(f"Table {actual_table_name} has {initial_count} rows before deletion")
        except Exception:
            initial_count = "unknown"
        
        table.delete(where=filter_expr)
        
        # Get final row count for reporting
        try:
            final_count = table.count_rows()
            deleted_count = initial_count - final_count if isinstance(initial_count, int) else "unknown"
            logger.info(f"Successfully deleted documents. Rows: {initial_count} -> {final_count}")
            return f"Documents deleted successfully from table {actual_table_name}. Deleted {deleted_count} document(s)."
        except Exception:
            logger.info("Successfully deleted documents")
            return f"Documents deleted successfully from table {actual_table_name}"
            
    except Exception as e:
        error_msg = f"Error deleting documents: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}" 
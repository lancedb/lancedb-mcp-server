"""Search operations for LanceDB MCP server."""

import logging
import lancedb
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from typing import List, Optional, Union, Dict, Any
from ..core.config import LANCEDB_URI, TABLE_NAME, logger, model
from ..core.schemas import Schema
from ..core.logger import log_exception, log_dict
from ..core.connection import get_connection, verify_table_exists, open_table_with_retry, create_table_with_retry, sanitize_table_name, get_table_cached, analyze_query_performance

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using the configured model.
    
    Args:
        texts (List[str]): List of texts to generate embeddings for
    
    Returns:
        List[List[float]]: List of embedding vectors
    """
    try:
        from ..core.config import model
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        
        # Use lancedb's embedding function with the configured model
        embeddings = model.embed_documents(texts)
        
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise

def query_table(
    query: str,
    table_name: Optional[str] = None,
    top_k: int = 5,
    query_type: str = "vector",
    auto_create_table: bool = False
) -> Union[List[dict], bool, str]:
    """
    Query a LanceDB table with a query string and return the top k results.

    Args:
        query (str): The query string
        table_name (str): Optional table name to query
        top_k (int): The number of results to return (0 to check existence)
        query_type (str): The type of query to perform
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        List[dict] or bool: If top_k > 0, returns a list of matching documents.
            If top_k = 0, returns True if any matches exist, False otherwise.
    """
    try:
        # Validate top_k parameter
        if top_k < 0:
            return f"Error: top_k must be non-negative (got {top_k}). Use 0 to check existence, or positive values to get results."
        
        actual_table_name = table_name or TABLE_NAME
        safe_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Starting table query: table={actual_table_name}, query='{query}', top_k={top_k}, query_type={query_type}")
        
        # Use robust table existence check
        table_exists = verify_table_exists(safe_table_name)
        
        if not table_exists:
            if not auto_create_table:
                return f"Error: Table {actual_table_name} does not exist or is not accessible. Set auto_create_table=True to create it automatically."
            
            # Auto-create table with default schema using robust creation
            success, message, table = create_table_with_retry(actual_table_name, Schema)
            if not success:
                return f"Error: Failed to auto-create table {actual_table_name}: {message}"
            logger.info(f"Auto-created new table for query: {actual_table_name}")
                     
            # Return empty results for newly created table
            if top_k == 0:
                return False
            else:
                return {
                    "results": [],
                    "query": query,
                    "table_name": actual_table_name,
                    "count": 0
                }
        
        # LanceDB Best Practice: Use cached table objects for better performance
        table = get_table_cached(safe_table_name)
        logger.debug(f"Using cached table: {actual_table_name}")
        
        # Verify table is accessible by checking row count
        try:
            row_count = table.count_rows()
            logger.debug(f"Table {actual_table_name} has {row_count} rows")
            
            # If table is empty, return appropriate empty result
            if row_count == 0:
                logger.info(f"Table {actual_table_name} is empty")
                if top_k == 0:
                    return False
                else:
                    return {
                        "results": [],
                        "query": query,
                        "table_name": actual_table_name,
                        "count": 0
                    }
                    
        except Exception as count_error:
            logger.warning(f"Could not check row count: {count_error}")
            # Continue anyway, but this indicates potential issues
        
        # Check table vector dimensions to use appropriate embedding model
        schema = table.schema
        table_dims = None
        for field in schema:
            if "fixed_size_list" in str(field.type).lower():
                import re
                dim_match = re.search(r'fixed_size_list<.*?>\[(\d+)\]', str(field.type))
                if dim_match:
                    table_dims = int(dim_match.group(1))
                    logger.debug(f"Table has {table_dims}-dimensional vectors")
                break
        
        # Check if table dimensions match default model
        if table_dims and table_dims != model.ndims():
            return f"Error: Table expects {table_dims}-dimensional vectors but your configured embedding model produces {model.ndims()}-dimensional vectors. Please either:\n1. Use a table with {model.ndims()} dimensions, OR\n2. Configure an embedding model that produces {table_dims}-dimensional vectors."
        
        try:
            # Use default model via string query
            results = table.search(query, query_type="vector")
            logger.debug(f"Performed search with query: {query}")
            
        except Exception as search_error:
            logger.error(f"Search failed: {search_error}")
            # Try to refresh table cache and retry once
            try:
                logger.info(f"Retrying search for table {actual_table_name} with fresh table object")
                table = get_table_cached(safe_table_name, force_refresh=True)
                results = table.search(query, query_type="vector")
                logger.info(f"Retry successful for query: {query}")
            except Exception as retry_error:
                logger.error(f"Retry also failed: {retry_error}")
                return f"Error: Unable to search table {actual_table_name}. {retry_error}"
        
        if top_k == 0:
            # Just check if any results exist
            try:
                test_results = results.limit(1).to_list()
                found = len(test_results) > 0
                logger.info(f"Found {'some' if found else 'no'} matching documents")
                return found
            except Exception as e:
                logger.warning(f"Error checking for results existence: {e}")
                return False
        
        # LanceDB Best Practice: Use .select() to limit returned columns for better performance
        results = results.limit(top_k).select(["doc", "_distance"]).to_list()
        logger.info(f"Retrieved {len(results)} results")
        
        if logger.isEnabledFor(logging.DEBUG):
            log_dict(logger, logging.DEBUG, "Query results", {"count": len(results), "results": results})

        # Return structured result for consistency with tests
        return {
            "results": results,
            "query": query,
            "table_name": actual_table_name,
            "count": len(results)
        }
        
    except Exception as e:
        error_msg = f"Error querying table: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}"

def hybrid_search(
    query: str,
    table_name: Optional[str] = None,
    filter_expr: Optional[str] = None,
    top_k: int = 5,
    metric: str = "cosine",
    distance_threshold: Optional[float] = None,
    auto_create_table: bool = False
) -> Union[List[dict], bool, str]:
    """
    Perform a hybrid search combining vector similarity with scalar filtering.

    Args:
        query (str): The query string for vector search
        table_name (str): Optional table name to search
        filter_expr (str): Optional filter expression
        top_k (int): Number of results to return (0 to check existence)
        metric (str): Distance metric to use
        distance_threshold (float): Optional maximum distance threshold
        auto_create_table (bool): Whether to auto-create table if it doesn't exist

    Returns:
        List[dict] or bool: If top_k > 0, returns matching documents with scores.
            If top_k = 0, returns True if any matches exist, False otherwise.
    """
    try:
        # Validate top_k parameter
        if top_k < 0:
            return f"Error: top_k must be non-negative (got {top_k}). Use 0 to check existence, or positive values to get results."
        
        actual_table_name = table_name or TABLE_NAME
        safe_table_name = sanitize_table_name(actual_table_name)
        logger.info(f"Performing hybrid search with query: {query} on table: {actual_table_name}")
        
        # Use robust table existence check
        table_exists = verify_table_exists(safe_table_name)
        
        if not table_exists:
            if not auto_create_table:
                return f"Error: Table {actual_table_name} does not exist or is not accessible. Set auto_create_table=True to create it automatically."
            
            # Auto-create table with default schema using robust creation
            success, message, table = create_table_with_retry(actual_table_name, Schema)
            if not success:
                return f"Error: Failed to auto-create table {actual_table_name}: {message}"
            logger.info(f"Auto-created new table for hybrid search: {actual_table_name}")
                    
            # Return empty results for newly created table
            if top_k == 0:
                return False
            else:
                return {
                    "results": [],
                    "query": query,
                    "table_name": actual_table_name,
                    "search_type": "hybrid",
                    "metric": metric,
                    "count": 0
                }
        
        # LanceDB Best Practice: Use cached table objects
        table = get_table_cached(safe_table_name)
        
        # Map metric names to supported values
        metric_map = {
            "cosine": "cosine",
            "dot": "dot",
            "l2": "l2",
            "euclidean": "l2",  # Map euclidean to l2
            "hamming": "hamming"
        }
        
        # Validate and map metric
        if metric not in metric_map:
            supported = ", ".join(sorted(set(metric_map.keys())))
            return f"Error: Invalid distance metric '{metric}'. Must be one of: {supported}"
            
        mapped_metric = metric_map[metric]
        
        # Start search
        search = table.search(query)
        
        # Set metric before applying filters
        search = search.metric(mapped_metric)
        
        # Apply scalar filter if provided, with intelligent distance filter conversion
        if filter_expr:
            # Check if the filter expression contains distance-based filtering
            distance_filter_patterns = [
                r'_distance\s*([<>=!]+)\s*([0-9.]+)',
                r'distance\s*([<>=!]+)\s*([0-9.]+)',
                r'score\s*([<>=!]+)\s*([0-9.]+)'
            ]
            
            import re
            converted_filter = filter_expr
            distance_extracted = None
            
            for pattern in distance_filter_patterns:
                match = re.search(pattern, filter_expr, re.IGNORECASE)
                if match:
                    operator = match.group(1).strip()
                    threshold_value = float(match.group(2))
                    
                    # Convert distance filter to distance_threshold parameter
                    if operator in ['<=', '<', '==', '=']:
                        distance_extracted = threshold_value
                        logger.info(f"Converted distance filter '{match.group(0)}' to distance_threshold={threshold_value}")
                    elif operator in ['>=', '>']:
                        # For >= or >, we can't easily convert to distance_threshold
                        # but we can warn the user
                        logger.warning(f"Distance filter '{match.group(0)}' with >= operator cannot be converted. Use distance_threshold parameter instead.")
                    
                    # Remove the distance filter from the main filter expression
                    converted_filter = re.sub(pattern, '', converted_filter, flags=re.IGNORECASE)
                    converted_filter = re.sub(r'\s*and\s*$|^\s*and\s*', '', converted_filter.strip(), flags=re.IGNORECASE)
                    converted_filter = re.sub(r'\s*or\s*$|^\s*or\s*', '', converted_filter.strip(), flags=re.IGNORECASE)
                    converted_filter = converted_filter.strip()
                    break
            
            # Apply the non-distance filters
            if converted_filter:
                try:
                    search = search.where(converted_filter)
                except Exception as e:
                    logger.warning(f"Filter expression '{converted_filter}' failed: {e}")
                    return f"Error: Invalid filter expression: {e}"
            
            # If we extracted a distance threshold, use it (override the parameter if both are provided)
            if distance_extracted is not None:
                if distance_threshold is not None:
                    logger.info(f"Distance filter from expression ({distance_extracted}) overrides distance_threshold parameter ({distance_threshold})")
                distance_threshold = distance_extracted
        
        # Apply distance threshold if specified
        if distance_threshold is not None:
            logger.info(f"Applying distance threshold: {distance_threshold}")
            
            # Validate threshold value for different metrics
            if mapped_metric == "cosine":
                if not (0.0 <= distance_threshold <= 2.0):
                    logger.warning(f"Distance threshold {distance_threshold} may be outside typical cosine range [0.0, 2.0]")
            elif mapped_metric in ["l2", "euclidean"]:
                if distance_threshold < 0.0:
                    logger.warning(f"Distance threshold {distance_threshold} should be non-negative for L2 distance")
            
            # Note: LanceDB doesn't have a direct distance threshold filter
            # We'll apply it post-processing
        
        # Apply limit and execute search
        if top_k == 0:
            # Just check if any results exist
            try:
                test_results = search.limit(1).to_list()
                found = len(test_results) > 0
                logger.info(f"Found {'some' if found else 'no'} matching documents")
                return found
            except Exception as e:
                logger.warning(f"Error checking for results existence: {e}")
                return False
        
        # Get more results than needed if we're filtering by distance
        fetch_limit = top_k * 2 if distance_threshold is not None else top_k
        
        try:
            results = search.limit(fetch_limit).to_list()
            logger.debug(f"Retrieved {len(results)} raw results from search")
        except Exception as e:
            logger.warning(f"Search execution failed: {e}")
            return f"Error: Search failed: {e}"
        
        # Post-process results for distance threshold filtering
        if distance_threshold is not None and results:
            filtered_results = []
            for result in results:
                # Get distance from result (different methods depending on what's available)
                distance = None
                if hasattr(result, '_distance'):
                    distance = result._distance
                elif isinstance(result, dict) and '_distance' in result:
                    distance = result['_distance']
                elif hasattr(result, 'distance'):
                    distance = result.distance
                elif isinstance(result, dict) and 'distance' in result:
                    distance = result['distance']
                
                if distance is not None:
                    # Apply threshold based on metric type
                    if mapped_metric == "cosine":
                        # For cosine, lower distances are better (higher similarity)
                        if distance <= distance_threshold:
                            filtered_results.append(result)
                    else:
                        # For L2/euclidean, lower distances are better
                        if distance <= distance_threshold:
                            filtered_results.append(result)
                else:
                    # If we can't get distance, include the result
                    filtered_results.append(result)
                
                # Stop when we have enough results
                if len(filtered_results) >= top_k:
                    break
            
            results = filtered_results[:top_k]
            logger.info(f"After distance filtering ({distance_threshold}): {len(results)} results")
        else:
            results = results[:top_k]
        
        logger.info(f"Retrieved {len(results)} final results")
        
        if logger.isEnabledFor(logging.DEBUG):
            log_dict(logger, logging.DEBUG, "Hybrid search results", {"count": len(results), "results": results})
        
        # Return structured result for consistency with tests
        return {
            "results": results,
            "query": query,
            "table_name": actual_table_name,
            "search_type": "hybrid",
            "metric": metric,
            "count": len(results)
        }
        
    except Exception as e:
        error_msg = f"Error performing hybrid search: {str(e)}"
        logger.error(error_msg)
        log_exception(logger, error_msg)
        return f"Error: {error_msg}" 
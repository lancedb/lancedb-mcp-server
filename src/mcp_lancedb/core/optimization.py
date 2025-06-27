"""LanceDB optimization and best practices implementation."""

import time
import logging
from typing import List, Dict, Any, Optional
from .config import (
    AUTO_CREATE_INDICES, AUTO_OPTIMIZE_TABLES, PREWARM_INDICES,
    ENABLE_VERSIONING, MAX_VERSIONS_TO_KEEP, AUTO_CLEANUP_VERSIONS,
    USE_GPU_INDEXING, WEAK_READ_CONSISTENCY_INTERVAL
)
from .logger import get_logger
from .connection import get_connection

logger = get_logger("optimization")

class LanceDBOptimizer:
    """LanceDB optimization manager implementing enterprise best practices."""
    
    def __init__(self):
        self.logger = logger
        
    def optimize_table_performance(self, table_name: str, schema_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Apply LanceDB best practices for table performance optimization.
        
        Args:
            table_name: Name of the table to optimize
            schema_info: Optional schema information for intelligent indexing
            
        Returns:
            Dict with optimization results and recommendations
        """
        try:
            from .connection import sanitize_table_name
            safe_table_name = sanitize_table_name(table_name)
            db = get_connection()
            table = db.open_table(safe_table_name)
            results = {"optimizations_applied": [], "recommendations": []}
            
            # 1. Create Scalar Indices for Fast Filtering (Best Practice)
            if AUTO_CREATE_INDICES:
                scalar_indices = self._create_optimal_scalar_indices(table, schema_info)
                results["optimizations_applied"].extend(scalar_indices)
            
            # 2. Create Vector Index for Fast Similarity Search
            vector_index_result = self._optimize_vector_index(table)
            if vector_index_result:
                results["optimizations_applied"].append(vector_index_result)
            
            # 3. Create Full-Text Search Index if applicable
            fts_result = self._create_fts_index(table)
            if fts_result:
                results["optimizations_applied"].append(fts_result)
            
            # 4. Table Optimization and Compaction
            if AUTO_OPTIMIZE_TABLES:
                optimize_result = self._optimize_table_storage(table)
                results["optimizations_applied"].append(optimize_result)
            
            # 5. Prewarm Indices for Performance
            if PREWARM_INDICES:
                prewarm_result = self._prewarm_indices(table)
                results["optimizations_applied"].append(prewarm_result)
            
            # 6. Performance Analysis and Recommendations
            perf_analysis = self._analyze_table_performance(table)
            results["recommendations"].extend(perf_analysis)
            
            logger.info(f"Applied {len(results['optimizations_applied'])} optimizations to table {table_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing table {table_name}: {e}")
            return {"error": str(e), "optimizations_applied": [], "recommendations": []}
    
    def _create_optimal_scalar_indices(self, table, schema_info: Optional[Dict] = None) -> List[str]:
        """Create scalar indices for commonly filtered fields."""
        indices_created = []
        
        try:
            # Get current indices to avoid duplicates
            existing_indices = table.list_indices()
            existing_names = [idx.get('name', '') for idx in existing_indices]
            
            # Auto-detect filterable fields from schema
            filterable_fields = []
            schema = table.schema
            
            for field in schema:
                field_name = field.name
                field_type = str(field.type)
                
                # Skip vector and document fields
                if field_name in ['vector', 'doc']:
                    continue
                    
                # Create indices for commonly filtered types
                if any(t in field_type.lower() for t in ['int', 'float', 'string', 'timestamp', 'bool']):
                    filterable_fields.append(field_name)
            
            # Create scalar indices for filterable fields
            for field_name in filterable_fields:
                index_name = f"scalar_idx_{field_name}"
                
                if index_name not in existing_names:
                    try:
                        # Try modern API first (without index_name parameter)
                        table.create_scalar_index(field_name)
                        indices_created.append(f"Created scalar index for '{field_name}' field")
                        logger.info(f"Created scalar index for field: {field_name}")
                    except TypeError:
                        # Fallback for older LanceDB versions that support index_name
                        try:
                            table.create_scalar_index(field_name, index_name=index_name)
                            indices_created.append(f"Created scalar index for '{field_name}' field")
                            logger.info(f"Created scalar index for field: {field_name}")
                        except Exception as e:
                            logger.warning(f"Could not create scalar index for {field_name}: {e}")
                    except Exception as e:
                        logger.warning(f"Could not create scalar index for {field_name}: {e}")
                        
        except Exception as e:
            logger.warning(f"Error creating scalar indices: {e}")
            
        return indices_created
    
    def _optimize_vector_index(self, table) -> Optional[str]:
        """Optimize vector index for similarity search performance."""
        try:
            # Check if table has enough data for indexing
            row_count = table.count_rows()
            if row_count == 0:
                logger.debug("Skipping vector index creation for empty table")
                return None
            
            # Check if vector index exists and is optimal
            existing_indices = table.list_indices()
            vector_indices = [idx for idx in existing_indices if 'vector' in idx.get('name', '').lower()]
            
            if not vector_indices:
                # Create optimized vector index based on table size
                if row_count < 256:
                    # For small tables, use simple index
                    try:
                        table.create_index(metric="cosine")
                        logger.info(f"Created simple vector index for small table ({row_count} rows)")
                        return f"Created vector index optimized for small table ({row_count} rows)"
                    except Exception as e:
                        logger.debug(f"Simple index creation failed: {e}")
                        return None
                else:
                    # For larger tables, use IVF_PQ (enterprise-grade)
                    try:
                        table.create_index(
                            metric="cosine",  # Most common for embeddings
                            index_type="IVF_PQ",  # Enterprise-grade index type
                            index_cache_size=1000,  # MB cache
                            num_partitions=min(256, row_count // 10),  # Adaptive partitions
                            use_gpu=USE_GPU_INDEXING
                        )
                        logger.info("Created optimized vector index (IVF_PQ)")
                        return "Created optimized vector index (IVF_PQ) for fast similarity search"
                    except Exception as e:
                        # Fallback to default index
                        table.create_index()
                        logger.info(f"Created default vector index (fallback): {e}")
                        return "Created default vector index"
            else:
                logger.debug("Vector index already exists")
                return None
                
        except Exception as e:
            logger.warning(f"Error optimizing vector index: {e}")
            return None
    
    def _create_fts_index(self, table) -> Optional[str]:
        """Create full-text search index for document fields."""
        try:
            # Check if we have text fields suitable for FTS
            schema = table.schema
            text_fields = []
            
            for field in schema:
                if field.name == 'doc' or 'text' in field.name.lower():
                    text_fields.append(field.name)
            
            if text_fields:
                for field_name in text_fields:
                    try:
                        table.create_fts_index(field_name)
                        logger.info(f"Created FTS index for field: {field_name}")
                        return f"Created full-text search index for '{field_name}' field"
                    except Exception as e:
                        logger.debug(f"FTS index creation skipped for {field_name}: {e}")
                        
        except Exception as e:
            logger.debug(f"FTS index creation not applicable: {e}")
            
        return None
    
    def _optimize_table_storage(self, table) -> str:
        """Optimize table storage following LanceDB best practices."""
        try:
            # Use modern table.optimize() instead of deprecated compact_files()
            # LanceDB Best Practice: table.optimize() replaces compact_files()
            table.optimize()
            
            logger.info("Completed table storage optimization")
            return "Applied table storage optimization (modern LanceDB best practice)"
            
        except Exception as e:
            logger.warning(f"Table optimization failed: {e}")
            return f"Table optimization failed: {e}"
    
    def _prewarm_indices(self, table) -> str:
        """Prewarm indices for better query performance."""
        try:
            # Prewarm the vector index for faster initial queries
            table.prewarm_index()
            logger.info("Prewarmed indices for faster query performance")
            return "Prewarmed indices for faster initial query performance"
            
        except Exception as e:
            logger.debug(f"Index prewarming not available: {e}")
            return "Index prewarming not available in this LanceDB version"
    
    def _analyze_table_performance(self, table) -> List[str]:
        """Analyze table performance following LanceDB best practices."""
        recommendations = []
        
        try:
            # Get table statistics
            stats = table.stats()
            row_count = table.count_rows()
            
            # LanceDB Best Practice: Monitor index coverage
            # "A well-optimized table should have num_unindexed_rows ~ 0"
            try:
                index_stats = table.index_stats()
                
                if 'num_unindexed_rows' in index_stats:
                    unindexed_rows = index_stats['num_unindexed_rows']
                    if unindexed_rows > 0:
                        percentage = (unindexed_rows / row_count * 100) if row_count > 0 else 0
                        recommendations.append(f"❌ Index coverage issue: {unindexed_rows:,} unindexed rows ({percentage:.1f}%)")
                        recommendations.append("✅ Run optimize_table() to improve index coverage")
                    else:
                        recommendations.append("✅ Excellent: All rows are properly indexed (num_unindexed_rows = 0)")
                
                recommendations.append("✅ Detailed index stats available - use get_index_stats() for performance analysis")
                
            except Exception as e:
                recommendations.append(f"⚠️ Index monitoring limited: {e}")
                recommendations.append("Consider upgrading to LanceDB Enterprise for detailed index statistics")
            
            # Row count based recommendations from LanceDB docs
            if row_count > 1_000_000:
                recommendations.append("📊 Large table detected (>1M rows) - consider partitioning or sharding")
            
            if row_count > 100_000:
                recommendations.append("⚡ Consider weak consistency mode for better read performance in high-concurrency scenarios")
            
            # Performance monitoring recommendations
            recommendations.append("📈 Use analyze_query_performance() to identify query bottlenecks")
            recommendations.append("🔍 Monitor memory usage and adjust index_cache_size based on query patterns")
            
            # Version management recommendations
            if ENABLE_VERSIONING:
                try:
                    versions = table.list_versions()
                    if len(versions) > MAX_VERSIONS_TO_KEEP:
                        recommendations.append(f"Found {len(versions)} versions - consider cleanup_old_versions() for storage optimization")
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Performance analysis limited: {e}")
            recommendations.append("Enable detailed logging for comprehensive performance analysis")
            
        return recommendations
    
    def manage_table_versions(self, table_name: str) -> Dict[str, Any]:
        """Manage table versions according to best practices."""
        if not ENABLE_VERSIONING:
            return {"versioning": "disabled"}
            
        try:
            from .connection import sanitize_table_name
            safe_table_name = sanitize_table_name(table_name)
            db = get_connection()
            table = db.open_table(safe_table_name)
            
            results = {
                "current_version": table.version,
                "versions_available": [],
                "cleanup_performed": False
            }
            
            # List all versions
            versions = table.list_versions()
            results["versions_available"] = [v.get("version", "unknown") for v in versions]
            
            # Auto-cleanup old versions if enabled
            if AUTO_CLEANUP_VERSIONS and len(versions) > MAX_VERSIONS_TO_KEEP:
                # Keep the latest versions, clean up the rest
                versions_to_cleanup = len(versions) - MAX_VERSIONS_TO_KEEP
                table.cleanup_old_versions(older_than=versions_to_cleanup)
                results["cleanup_performed"] = True
                logger.info(f"Cleaned up {versions_to_cleanup} old versions for table {table_name}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error managing versions for table {table_name}: {e}")
            return {"error": str(e)}

# Global optimizer instance
optimizer = LanceDBOptimizer() 
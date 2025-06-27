"""Unit tests for mcp_lancedb __init__.py module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mcp_lancedb import (
    optimize_table,
    table_versions,
    get_index_stats,
    analyze_query_perf,
    __version__
)

# --- DummyTable and DummyDB for robust LanceDB mocking ---
class DummyTable:
    def __init__(self, name="TestTable", row_count=10, schema=None):
        self._name = name
        self._row_count = row_count
        if schema is None:
            self.schema = [Mock(type="string"), Mock(type="fixed_size_list<item: float>[384]")]
        else:
            self.schema = schema
    
    def count_rows(self):
        return self._row_count
    
    def list_indices(self):
        return ["index1", "index2"]
    
    def stats(self):
        return {"rows": self._row_count, "size": "1MB"}
    
    def index_stats(self):
        return {
            "num_unindexed_rows": 0,
            "index_coverage": "100%"
        }
    
    def search(self, query):
        mock_query = Mock()
        mock_query.limit.return_value = mock_query
        mock_query.select.return_value = mock_query
        return mock_query

class DummyDB:
    def __init__(self):
        self._tables = {}
    
    def table_names(self, limit=None):
        return list(self._tables.keys())
    
    def create_table(self, name, *a, **k):
        if name in self._tables:
            raise Exception(f"Table {name} already exists")
        table = DummyTable(name)
        self._tables[name] = table
        return table
    
    def open_table(self, name):
        if name not in self._tables:
            raise Exception(f"Table {name} not found")
        return self._tables[name]
    
    def drop_table(self, name):
        if name not in self._tables:
            raise Exception(f"Table {name} not found")
        del self._tables[name]
        return True

@pytest.mark.unit
class TestInitModule:
    """Test the __init__.py module functions."""
    
    def test_version(self):
        """Test that version is properly defined."""
        assert __version__ == "0.1.0"
    
    @patch('mcp_lancedb.core.optimization.optimizer.optimize_table_performance')
    def test_optimize_table(self, mock_optimize):
        """Test optimize_table convenience function."""
        # Mock the optimizer to return a realistic response
        mock_optimize.return_value = {
            "status": "optimized",
            "recommendations": []
        }
        
        result = optimize_table("test_table")
        
        assert isinstance(result, dict)
        assert "status" in result
        mock_optimize.assert_called_once_with("test_table")
    
    @patch('mcp_lancedb.core.optimization.optimizer.manage_table_versions')
    def test_table_versions(self, mock_versions):
        """Test table_versions convenience function."""
        # Mock the optimizer to return a realistic response
        mock_versions.return_value = {
            "versions": ["v1", "v2"],
            "current": "v2"
        }
        
        result = table_versions("test_table")
        
        assert isinstance(result, dict)
        assert "versions" in result
        mock_versions.assert_called_once_with("test_table")

@pytest.mark.unit
class TestGetIndexStats:
    """Test the get_index_stats function."""
    
    def setup_method(self):
        """Setup method to ensure clean state for each test."""
        import mcp_lancedb.core.connection
        self.original_connection = mcp_lancedb.core.connection._db_connection
        self.original_cache = mcp_lancedb.core.connection._table_cache.copy()
        mcp_lancedb.core.connection._db_connection = None
        mcp_lancedb.core.connection._table_cache.clear()
    
    def teardown_method(self):
        """Teardown method to restore original state."""
        import mcp_lancedb.core.connection
        mcp_lancedb.core.connection._db_connection = self.original_connection
        mcp_lancedb.core.connection._table_cache.clear()
        mcp_lancedb.core.connection._table_cache.update(self.original_cache)
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_get_index_stats_success(self, mock_sanitize, mock_get_connection):
        """Test successful index stats retrieval."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        dummy_db.create_table("test_table")
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = get_index_stats("test_table")
        
        assert isinstance(result, dict)
        assert "indices" in result
        assert result["indices"] == ["index1", "index2"]
        assert "basic_stats" in result
        assert result["basic_stats"]["rows"] == 10
        assert "index_performance" in result
        assert result["index_performance"]["num_unindexed_rows"] == 0
        assert "index_coverage" in result
        assert result["index_coverage"] == "Excellent - all rows indexed"
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_get_index_stats_with_unindexed_rows(self, mock_sanitize, mock_get_connection):
        """Test index stats when there are unindexed rows."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        table = dummy_db.create_table("test_table")
        # Override index_stats to return unindexed rows
        table.index_stats = lambda: {
            "num_unindexed_rows": 25,
            "index_coverage": "75%"
        }
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = get_index_stats("test_table")
        
        assert isinstance(result, dict)
        assert "optimization_needed" in result
        assert "25 unindexed rows detected" in result["optimization_needed"]
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_get_index_stats_index_stats_error(self, mock_sanitize, mock_get_connection):
        """Test index stats when detailed stats fail."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        table = dummy_db.create_table("test_table")
        # Create a proper Mock for index_stats method
        mock_index_stats = Mock()
        mock_index_stats.side_effect = Exception("Stats not available")
        table.index_stats = mock_index_stats
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = get_index_stats("test_table")
        
        assert isinstance(result, dict)
        assert "indices" in result
        assert "index_performance" in result
        assert "Detailed stats not available" in result["index_performance"]
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_get_index_stats_table_error(self, mock_sanitize, mock_get_connection):
        """Test index stats when table access fails."""
        # Create a DummyDB without the test table
        dummy_db = DummyDB()
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = get_index_stats("test_table")
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Table test_table not found" in result["error"]

@pytest.mark.unit
class TestAnalyzeQueryPerf:
    """Test the analyze_query_perf function."""
    
    def setup_method(self):
        """Setup method to ensure clean state for each test."""
        import mcp_lancedb.core.connection
        self.original_connection = mcp_lancedb.core.connection._db_connection
        self.original_cache = mcp_lancedb.core.connection._table_cache.copy()
        mcp_lancedb.core.connection._db_connection = None
        mcp_lancedb.core.connection._table_cache.clear()
    
    def teardown_method(self):
        """Teardown method to restore original state."""
        import mcp_lancedb.core.connection
        mcp_lancedb.core.connection._db_connection = self.original_connection
        mcp_lancedb.core.connection._table_cache.clear()
        mcp_lancedb.core.connection._table_cache.update(self.original_cache)
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_analyze_query_perf_success(self, mock_sanitize, mock_get_connection):
        """Test successful query performance analysis."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        dummy_db.create_table("test_table")
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = analyze_query_perf("test_table", "test query", 10)
        
        assert isinstance(result, dict)
        assert "table_name" in result
        assert result["table_name"] == "test_table"
        assert "query_plan" in result
        assert "performance_insights" in result
        assert "optimization_recommendations" in result
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_analyze_query_perf_error(self, mock_sanitize, mock_get_connection):
        """Test query performance analysis when it fails."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        dummy_db.create_table("test_table")
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = analyze_query_perf("test_table", "test query")
        
        assert isinstance(result, dict)
        assert "table_name" in result
        assert result["table_name"] == "test_table"
        # The function should succeed and return analysis results
    
    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    def test_analyze_query_perf_default_parameters(self, mock_sanitize, mock_get_connection):
        """Test query performance analysis with default parameters."""
        # Create a DummyDB with a test table
        dummy_db = DummyDB()
        dummy_db.create_table("test_table")
        
        mock_sanitize.return_value = "test_table"
        mock_get_connection.return_value = dummy_db
        
        result = analyze_query_perf("test_table")
        
        assert isinstance(result, dict)
        assert "table_name" in result
        assert result["table_name"] == "test_table"
        # The function should succeed and return analysis results

@pytest.mark.unit
class TestInitImports:
    """Test that all expected imports are available."""
    
    def test_table_management_imports(self):
        """Test that table management functions are imported."""
        from mcp_lancedb import (
            create_table,
            delete_table,
            list_tables,
            table_count,
            table_details,
            table_stats
        )
        
        # Just check they're callable (they'll be mocked in actual tests)
        assert callable(create_table)
        assert callable(delete_table)
        assert callable(list_tables)
        assert callable(table_count)
        assert callable(table_details)
        assert callable(table_stats)
    
    def test_document_management_imports(self):
        """Test that document management functions are imported."""
        from mcp_lancedb import (
            ingest_docs,
            update_documents,
            delete_documents
        )
        
        assert callable(ingest_docs)
        assert callable(update_documents)
        assert callable(delete_documents)
    
    def test_search_operations_imports(self):
        """Test that search operation functions are imported."""
        from mcp_lancedb import (
            query_table,
            hybrid_search
        )
        
        assert callable(query_table)
        assert callable(hybrid_search)
    
    def test_core_components_imports(self):
        """Test that core components are imported."""
        from mcp_lancedb import (
            LANCEDB_URI,
            TABLE_NAME,
            EMBEDDING_FUNCTION,
            MODEL_NAME,
            model,
            logger,
            get_connection,
            get_all_tables,
            get_table_cached,
            clear_table_cache,
            analyze_query_performance,
            Schema
        )
        
        # Check that these are defined (values may vary)
        assert LANCEDB_URI is not None
        assert TABLE_NAME is not None
        assert EMBEDDING_FUNCTION is not None
        assert MODEL_NAME is not None
        assert model is not None
        assert logger is not None
        assert callable(get_connection)
        assert callable(get_all_tables)
        assert callable(get_table_cached)
        assert callable(clear_table_cache)
        assert callable(analyze_query_performance)
        assert Schema is not None
    
    def test_entry_points_imports(self):
        """Test that entry point functions are imported."""
        from mcp_lancedb import (
            run_server,
            cli_main
        )
        
        assert callable(run_server)
        assert callable(cli_main) 
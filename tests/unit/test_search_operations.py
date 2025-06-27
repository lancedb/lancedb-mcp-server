"""Unit tests for search operations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mcp_lancedb.operations.search_operations import (
    query_table,
    hybrid_search,
    get_embeddings
)

class DummyTable:
    def __init__(self, dims=384, row_count=10, search_results=None):
        mock_field = Mock()
        mock_field.type = f'fixed_size_list<item: float>[{dims}]'
        self.schema = [mock_field]
        self._row_count = row_count
        self._search_results = search_results or [{"doc": "result", "_distance": 0.1}]
    def count_rows(self):
        return self._row_count
    def search(self, *args, **kwargs):
        class DummyQuery:
            def __init__(self, results):
                self._results = results
            def limit(self, *a, **k):
                return self
            def select(self, *a, **k):
                return self
            def to_list(self):
                return self._results
            def metric(self, *a, **k):
                return self
            def where(self, *a, **k):
                return self
        return DummyQuery(self._search_results)

@pytest.mark.unit
class TestGetEmbeddings:
    """Test the get_embeddings function."""
    
    @patch('mcp_lancedb.core.config.model')
    def test_get_embeddings_success(self, mock_model):
        """Test successful embedding generation."""
        mock_model.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        texts = ["Hello world", "Test document"]
        
        result = get_embeddings(texts)
        
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_model.embed_documents.assert_called_once_with(texts)
    
    @patch('mcp_lancedb.core.config.model')
    def test_get_embeddings_error(self, mock_model):
        """Test embedding generation error handling."""
        mock_model.embed_documents.side_effect = Exception("Model error")
        texts = ["Hello world"]
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            with pytest.raises(Exception):
                get_embeddings(texts)

@pytest.mark.unit
class TestQueryTable:
    """Test the query_table function."""
    
    def make_schema(self, dims=384):
        """Create a mock schema with specified dimensions."""
        mock_field = Mock()
        mock_field.type = f'fixed_size_list<item: float>[{dims}]'
        # Make the schema iterable by returning a list
        return [mock_field]

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_success(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test successful table query."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = query_table("test query", table_name="test-table", top_k=5)
        assert isinstance(result, dict)
        assert "results" in result
        assert result["count"] == 1
        assert result["query"] == "test query"
        assert result["table_name"] == "test-table"

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_query_table_not_exists_no_auto_create(self, mock_verify_exists, mock_get_connection):
        """Test query when table doesn't exist and auto_create is False."""
        mock_verify_exists.return_value = False
        mock_db = Mock()
        mock_get_connection.return_value = mock_db
        
        result = query_table("test query", table_name="nonexistent-table", auto_create_table=False)
        
        assert isinstance(result, str)
        assert "does not exist" in result
        assert "auto_create_table=True" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.operations.search_operations.create_table_with_retry')
    def test_query_table_auto_create_success(self, mock_create_table, mock_verify_exists, mock_get_connection):
        """Test auto-creation of table during query."""
        mock_verify_exists.return_value = False
        mock_create_table.return_value = (True, "Success", Mock())
        mock_db = Mock()
        mock_get_connection.return_value = mock_db
        
        result = query_table("test query", table_name="new-table", auto_create_table=True, top_k=0)
        
        assert result is False  # Empty table check returns False
        mock_create_table.assert_called_once()

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.operations.search_operations.create_table_with_retry')
    def test_query_table_auto_create_failure(self, mock_create_table, mock_verify_exists, mock_get_connection):
        """Test auto-creation failure during query."""
        mock_verify_exists.return_value = False
        mock_create_table.return_value = (False, "Creation failed", None)
        mock_db = Mock()
        mock_get_connection.return_value = mock_db
        
        result = query_table("test query", table_name="new-table", auto_create_table=True)
        
        assert isinstance(result, str)
        assert "Failed to auto-create table" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_query_table_empty_table(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test query on empty table."""
        mock_db = Mock()
        mock_table = Mock()
        
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_table.count_rows.return_value = 0
        mock_get_connection.return_value = mock_db
        
        result = query_table("test query", table_name="empty-table", top_k=5)
        
        assert isinstance(result, dict)
        assert result["results"] == []
        assert result["count"] == 0

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_existence_check(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        mock_db = Mock()
        mock_table = DummyTable(row_count=5, search_results=[{"doc": "result"}])
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = query_table("test query", table_name="test-table", top_k=0)
        assert result is True

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_query_table_existence_check_no_results(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test query table with top_k=0 for existence check with no results."""
        mock_db = Mock()
        # Create DummyTable with no search results
        mock_table = DummyTable(row_count=0, search_results=[])
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = query_table("test query", table_name="test-table", top_k=0)
        assert result is False  # No results found

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_dimension_mismatch(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        mock_db = Mock()
        mock_table = DummyTable(dims=512)
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = query_table("test query", table_name="test-table")
        assert isinstance(result, str)
        assert "dimensional vectors" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_search_error_with_retry(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        mock_db = Mock()
        # Simulate search error on first call, success on retry
        class ErrorThenSuccessTable(DummyTable):
            def __init__(self):
                super().__init__()
                self._search_called = 0
            def search(self, *a, **k):
                if self._search_called == 0:
                    self._search_called += 1
                    raise Exception("Search error")
                return super().search(*a, **k)
        mock_table = ErrorThenSuccessTable()
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            result = query_table("test query", table_name="test-table", top_k=5)
            assert isinstance(result, dict)
            assert "results" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_search_error_no_retry(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        mock_db = Mock()
        class AlwaysErrorTable(DummyTable):
            def search(self, *a, **k):
                raise Exception("Search error")
        mock_table = AlwaysErrorTable()
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            result = query_table("test query", table_name="test-table", top_k=5)
            assert isinstance(result, str)
            assert "Unable to search table" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_query_table_count_rows_error(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        mock_db = Mock()
        class CountErrorTable(DummyTable):
            def count_rows(self):
                raise Exception("Count error")
        mock_table = CountErrorTable()
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            result = query_table("test query", table_name="test-table")
            assert isinstance(result, dict)
            assert "results" in result

@pytest.mark.unit
class TestHybridSearch:
    """Test the hybrid_search function."""
    
    def make_schema(self, dims=384):
        """Create a mock schema with specified dimensions."""
        mock_field = Mock()
        mock_field.type = f'fixed_size_list<item: float>[{dims}]'
        return [mock_field]

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.core.config.model')
    def test_hybrid_search_success(self, mock_model, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test successful hybrid search."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_model.ndims.return_value = 384
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", top_k=5)
        assert isinstance(result, dict)
        assert "results" in result
        assert result["count"] == 1

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_table_not_exists_no_auto_create(self, mock_verify_exists, mock_get_connection):
        """Test hybrid search when table doesn't exist and auto_create is False."""
        mock_verify_exists.return_value = False
        mock_db = Mock()
        mock_get_connection.return_value = mock_db
        
        result = hybrid_search("test query", table_name="nonexistent-table", auto_create_table=False)
        
        assert isinstance(result, str)
        assert "does not exist" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    @patch('mcp_lancedb.operations.search_operations.create_table_with_retry')
    def test_hybrid_search_auto_create_success(self, mock_create_table, mock_verify_exists, mock_get_connection):
        """Test auto-creation of table during hybrid search."""
        mock_verify_exists.return_value = False
        mock_create_table.return_value = (True, "Success", Mock())
        mock_db = Mock()
        mock_get_connection.return_value = mock_db
        
        result = hybrid_search("test query", table_name="new-table", auto_create_table=True, top_k=0)
        
        assert result is False  # Empty table check returns False
        mock_create_table.assert_called_once()

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_with_filter(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with filter expression."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", filter_expr="category = 'test'", top_k=5)
        assert isinstance(result, dict)
        assert "results" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_with_distance_filter(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with distance filter."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", filter_expr="_distance <= 0.5", top_k=5)
        assert isinstance(result, dict)
        assert "results" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_with_distance_threshold(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with distance threshold."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", distance_threshold=0.5, top_k=5)
        assert isinstance(result, dict)
        assert "results" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_different_metrics(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with different distance metrics."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", metric="dot", top_k=5)
        assert isinstance(result, dict)
        assert "results" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_invalid_metric(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with invalid distance metric."""
        mock_db = Mock()
        mock_table = DummyTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="lancedb-mcp-table", metric="invalid")
        assert isinstance(result, str)
        assert "Invalid distance metric" in result

    def test_hybrid_search_invalid_top_k(self):
        """Test hybrid search with invalid top_k parameter."""
        result = hybrid_search("test query", top_k=-1)
        assert isinstance(result, str)
        assert "top_k must be" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_filter_error(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with filter error."""
        mock_db = Mock()
        class FilterErrorTable(DummyTable):
            def search(self, *a, **k):
                raise Exception("Filter error")
        mock_table = FilterErrorTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            result = hybrid_search("test query", table_name="test-table", filter_expr="invalid filter", top_k=5)
            assert isinstance(result, str)
            assert "Error performing hybrid search" in result

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_existence_check(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with top_k=0 for existence check."""
        mock_db = Mock()
        mock_table = DummyTable(row_count=5, search_results=[{"doc": "result"}])
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        result = hybrid_search("test query", table_name="test-table", top_k=0)
        assert result is True  # Found results

    @patch('mcp_lancedb.operations.search_operations.get_connection')
    @patch('mcp_lancedb.operations.search_operations.get_table_cached')
    @patch('mcp_lancedb.operations.search_operations.verify_table_exists')
    def test_hybrid_search_search_error(self, mock_verify_exists, mock_get_table, mock_get_connection):
        """Test hybrid search with search error."""
        mock_db = Mock()
        class SearchErrorTable(DummyTable):
            def search(self, *a, **k):
                raise Exception("Search error")
        mock_table = SearchErrorTable()
        mock_verify_exists.return_value = True
        mock_get_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        with patch('mcp_lancedb.operations.search_operations.logger') as mock_logger:
            result = hybrid_search("test query", table_name="test-table", top_k=5)
            assert isinstance(result, str)
            assert "Error performing hybrid search" in result 
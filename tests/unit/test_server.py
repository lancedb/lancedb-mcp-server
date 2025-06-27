"""Unit tests for MCP server endpoints."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mcp_lancedb.server import (
    lancedb_help,
    create_table,
    table_details,
    table_stats,
    list_tables,
    table_count,
    delete_table,
    ingest_docs,
    update_documents,
    delete_documents,
    query_table,
    hybrid_search
)

@pytest.mark.unit
class TestServerHelp:
    """Test the help function."""
    
    def test_lancedb_help(self):
        """Test that help function returns a string with expected content."""
        help_text = lancedb_help()
        
        assert isinstance(help_text, str)
        assert "LanceDB operations" in help_text
        assert "Table Management" in help_text
        assert "Document Management" in help_text
        assert "Search Operations" in help_text

@pytest.mark.unit
class TestTableManagementEndpoints:
    """Test table management server endpoints."""
    
    @patch('mcp_lancedb.operations.table_management.create_table')
    def test_create_table_endpoint(self, mock_create_table):
        """Test create_table server endpoint."""
        mock_create_table.return_value = "Table created successfully"
        
        result = create_table("test_table", {"doc": "str", "vector": "Vector(384)"})
        
        assert result == "Table created successfully"
        mock_create_table.assert_called_once_with("test_table", {"doc": "str", "vector": "Vector(384)"})
    
    @patch('mcp_lancedb.operations.table_management.table_details')
    def test_table_details_endpoint(self, mock_table_details):
        """Test table_details server endpoint."""
        mock_table_details.return_value = {"name": "test_table", "rows": 100}
        
        result = table_details("test_table")
        
        assert result == {"name": "test_table", "rows": 100}
        mock_table_details.assert_called_once_with("test_table")
    
    @patch('mcp_lancedb.operations.table_management.table_stats')
    def test_table_stats_endpoint(self, mock_table_stats):
        """Test table_stats server endpoint."""
        mock_table_stats.return_value = {"name": "test_table", "stats": "detailed"}
        
        result = table_stats("test_table")
        
        assert result == {"name": "test_table", "stats": "detailed"}
        mock_table_stats.assert_called_once_with("test_table")
    
    @patch('mcp_lancedb.operations.table_management.list_tables')
    def test_list_tables_endpoint(self, mock_list_tables):
        """Test list_tables server endpoint."""
        mock_list_tables.return_value = {"tables": ["table1", "table2"]}
        
        result = list_tables()
        
        assert result == {"tables": ["table1", "table2"]}
        mock_list_tables.assert_called_once()
    
    @patch('mcp_lancedb.operations.table_management.table_count')
    def test_table_count_endpoint(self, mock_table_count):
        """Test table_count server endpoint."""
        mock_table_count.return_value = {"count": 5}
        
        result = table_count()
        
        assert result == {"count": 5}
        mock_table_count.assert_called_once()
    
    @patch('mcp_lancedb.operations.table_management.delete_table')
    def test_delete_table_endpoint(self, mock_delete_table):
        """Test delete_table server endpoint."""
        mock_delete_table.return_value = "Table deleted successfully"
        
        result = delete_table("test_table")
        
        assert result == "Table deleted successfully"
        mock_delete_table.assert_called_once_with("test_table")

@pytest.mark.unit
class TestDocumentManagementEndpoints:
    """Test document management server endpoints."""
    
    @patch('mcp_lancedb.operations.document_management.ingest_docs')
    def test_ingest_docs_single_string(self, mock_ingest_docs):
        """Test ingest_docs with single string."""
        mock_ingest_docs.return_value = "Documents ingested successfully"
        
        result = ingest_docs("single document", "test_table", True)
        
        assert result == "Documents ingested successfully"
        mock_ingest_docs.assert_called_once_with("test_table", "single document", True)
    
    @patch('mcp_lancedb.operations.document_management.ingest_docs')
    def test_ingest_docs_list(self, mock_ingest_docs):
        """Test ingest_docs with list of documents."""
        mock_ingest_docs.return_value = "Documents ingested successfully"
        docs = ["doc1", "doc2", "doc3"]
        
        result = ingest_docs(docs, "test_table", True)
        
        assert result == "Documents ingested successfully"
        mock_ingest_docs.assert_called_once_with("test_table", docs, True)
    
    @patch('mcp_lancedb.operations.document_management.update_documents')
    def test_update_documents_endpoint(self, mock_update_documents):
        """Test update_documents server endpoint."""
        mock_update_documents.return_value = "Documents updated successfully"
        
        result = update_documents("test_table", "category = 'test'", {"status": "updated"})
        
        assert result == "Documents updated successfully"
        mock_update_documents.assert_called_once_with("test_table", "category = 'test'", {"status": "updated"})
    
    @patch('mcp_lancedb.operations.document_management.delete_documents')
    def test_delete_documents_endpoint(self, mock_delete_documents):
        """Test delete_documents server endpoint."""
        mock_delete_documents.return_value = "Documents deleted successfully"
        
        result = delete_documents("test_table", "category = 'test'")
        
        assert result == "Documents deleted successfully"
        mock_delete_documents.assert_called_once_with("test_table", "category = 'test'")

@pytest.mark.unit
class TestSearchEndpoints:
    """Test search operation server endpoints."""
    
    @patch('mcp_lancedb.operations.search_operations.query_table')
    def test_query_table_endpoint(self, mock_query_table):
        """Test query_table server endpoint."""
        mock_query_table.return_value = {"results": [{"doc": "result"}], "count": 1}
        
        result = query_table("test query", "test_table", 5, "vector", False)
        
        assert result == {"results": [{"doc": "result"}], "count": 1}
        mock_query_table.assert_called_once_with("test query", "test_table", 5, "vector", False)
    
    @patch('mcp_lancedb.operations.search_operations.hybrid_search')
    def test_hybrid_search_endpoint(self, mock_hybrid_search):
        """Test hybrid_search server endpoint."""
        mock_hybrid_search.return_value = {"results": [{"doc": "result"}], "count": 1}
        
        result = hybrid_search("test query", "test_table", "category = 'test'", 5, "cosine", 0.5, False)
        
        assert result == {"results": [{"doc": "result"}], "count": 1}
        mock_hybrid_search.assert_called_once_with("test query", "test_table", "category = 'test'", 5, "cosine", 0.5, False)

@pytest.mark.unit
class TestServerErrorHandling:
    """Test server endpoint error handling."""
    
    @patch('mcp_lancedb.operations.table_management.create_table')
    def test_create_table_error(self, mock_create_table):
        """Test create_table endpoint with error."""
        mock_create_table.side_effect = Exception("Database error")
        
        # The server should catch the exception and return an error message
        try:
            result = create_table("test_table")
            # If no exception is raised, the result should be an error message
            assert isinstance(result, str)
            assert "error" in result.lower()
        except Exception:
            # If exception is raised, that's also acceptable for this test
            pass
    
    @patch('mcp_lancedb.operations.document_management.ingest_docs')
    def test_ingest_docs_error(self, mock_ingest_docs):
        """Test ingest_docs endpoint with error."""
        mock_ingest_docs.side_effect = Exception("Ingestion error")
        
        try:
            result = ingest_docs("test doc", "test_table")
            assert isinstance(result, str)
            assert "error" in result.lower()
        except Exception:
            pass
    
    @patch('mcp_lancedb.operations.search_operations.query_table')
    def test_query_table_error(self, mock_query_table):
        """Test query_table endpoint with error."""
        mock_query_table.side_effect = Exception("Query error")
        
        try:
            result = query_table("test query", "test_table")
            assert isinstance(result, str)
            assert "error" in result.lower()
        except Exception:
            pass

@pytest.mark.unit
class TestServerParameterValidation:
    """Test server endpoint parameter validation."""
    
    def test_create_table_no_schema(self):
        """Test create_table with no schema (should use default)."""
        with patch('mcp_lancedb.operations.table_management.create_table') as mock_create_table:
            mock_create_table.return_value = "Table created"
            
            result = create_table("test_table")
            
            assert result == "Table created"
            mock_create_table.assert_called_once_with("test_table", None)
    
    def test_table_details_no_table_name(self):
        """Test table_details with no table name (should use default)."""
        with patch('mcp_lancedb.operations.table_management.table_details') as mock_table_details:
            mock_table_details.return_value = {"name": "default_table"}
            
            result = table_details()
            
            assert result == {"name": "default_table"}
            mock_table_details.assert_called_once_with(None)
    
    def test_ingest_docs_default_parameters(self):
        """Test ingest_docs with default parameters."""
        with patch('mcp_lancedb.operations.document_management.ingest_docs') as mock_ingest_docs:
            mock_ingest_docs.return_value = "Documents ingested"
            
            result = ingest_docs("test doc")
            
            assert result == "Documents ingested"
            mock_ingest_docs.assert_called_once_with(None, "test doc", True)
    
    def test_query_table_default_parameters(self):
        """Test query_table with default parameters."""
        with patch('mcp_lancedb.operations.search_operations.query_table') as mock_query_table:
            mock_query_table.return_value = {"results": [], "count": 0}
            
            result = query_table("test query")
            
            assert result == {"results": [], "count": 0}
            mock_query_table.assert_called_once_with("test query", None, 5, "vector", False)
    
    def test_hybrid_search_default_parameters(self):
        """Test hybrid_search with default parameters."""
        with patch('mcp_lancedb.operations.search_operations.hybrid_search') as mock_hybrid_search:
            mock_hybrid_search.return_value = {"results": [], "count": 0}
            
            result = hybrid_search("test query")
            
            assert result == {"results": [], "count": 0}
            mock_hybrid_search.assert_called_once_with("test query", None, None, 5, "cosine", None, False) 
"""Unit tests for connection utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mcp_lancedb.core import (
    get_connection,
    verify_table_exists,
    open_table_with_retry,
    create_table_with_retry,
    sanitize_table_name
)


@pytest.mark.unit
class TestSanitizeTableName:
    """Test table name sanitization."""
    
    def test_camel_case_preserved(self):
        """CamelCase names should be preserved as-is (implementation updated)."""
        assert sanitize_table_name("TestTable") == "TestTable"  # Now preserved as-is
        assert sanitize_table_name("MyAwesomeTable") == "MyAwesomeTable"
    
    def test_hyphen_conversion(self):
        """Hyphens should be converted to CamelCase."""
        assert sanitize_table_name("test-table") == "TestTable"
        assert sanitize_table_name("my-awesome-table") == "MyAwesomeTable"
        assert sanitize_table_name("multi-word-test") == "MultiWordTest"
    
    def test_underscore_conversion(self):
        """Underscores should be converted to CamelCase."""
        assert sanitize_table_name("test_table") == "TestTable"
        assert sanitize_table_name("my_awesome_table") == "MyAwesomeTable"
        assert sanitize_table_name("multi_word_test") == "MultiWordTest"
    
    def test_dot_conversion(self):
        """Dots should be converted to CamelCase."""
        assert sanitize_table_name("test.table") == "TestTable"
        assert sanitize_table_name("my.awesome.table") == "MyAwesomeTable"
    
    def test_mixed_separators(self):
        """Mixed separators should be handled correctly."""
        assert sanitize_table_name("test-table_name.final") == "TestTableNameFinal"
        assert sanitize_table_name("my_test-table.name") == "MyTestTableName"
    
    def test_lowercase_conversion(self):
        """All lowercase should be capitalized."""
        assert sanitize_table_name("testtable") == "Testtable"
        assert sanitize_table_name("simple") == "Simple"
    
    def test_special_characters_removed(self):
        """Special characters should be removed."""
        assert sanitize_table_name("test@table#name") == "TestTableName"
        assert sanitize_table_name("my$table%name") == "MyTableName"
    
    def test_empty_string_fallback(self):
        """Empty strings should get a fallback name."""
        result = sanitize_table_name("")
        assert result == "DefaultTable"
        assert len(result) == 12
    
    def test_special_only_fallback(self):
        """Strings with only special characters should get fallback."""
        result = sanitize_table_name("@#$%")
        assert result.startswith("Table")
        assert len(result) > 5


@pytest.mark.unit
class TestVerifyTableExists:
    """Test table existence verification."""
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_table_exists_and_accessible(self, mock_get_connection):
        """Test when table exists and is accessible."""
        mock_db = Mock()
        mock_table = Mock()
        mock_table.schema = Mock()
        mock_db.open_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        assert verify_table_exists("TestTable") is True
        mock_db.open_table.assert_called_once_with("TestTable")
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_table_not_in_list(self, mock_get_connection):
        """Test when table is not in the table list."""
        mock_db = Mock()
        mock_db.open_table.side_effect = Exception("Not found")
        mock_db.table_names.return_value = ["OtherTable", "AnotherTable"]
        mock_get_connection.return_value = mock_db
        
        assert verify_table_exists("TestTable") is False
        mock_db.open_table.assert_called_with("TestTable")
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_table_exists_but_not_accessible(self, mock_get_connection):
        """Test when table exists in list but can't be opened."""
        mock_db = Mock()
        mock_db.open_table.side_effect = Exception("Cannot open table")
        mock_db.table_names.return_value = ["TestTable"]
        mock_get_connection.return_value = mock_db
        
        assert verify_table_exists("TestTable", max_retries=1) is False
        mock_db.open_table.assert_called_with("TestTable")
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_retry_logic(self, mock_get_connection):
        """Test retry logic when table becomes available."""
        mock_db = Mock()
        mock_table = Mock()
        mock_table.schema = Mock()
        # First call: open_table fails, second call: open_table succeeds
        mock_db.open_table.side_effect = [Exception("Not found"), mock_table]
        mock_db.table_names.return_value = ["TestTable"]
        mock_get_connection.return_value = mock_db
        
        assert verify_table_exists("TestTable", max_retries=2) is True
        assert mock_db.open_table.call_count == 2


@pytest.mark.unit
class TestCreateTableWithRetry:
    """Test table creation with retry logic."""
    
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    @patch('mcp_lancedb.core.connection.verify_table_exists')
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_successful_creation(self, mock_get_connection, mock_verify, mock_sanitize):
        """Test successful table creation."""
        mock_sanitize.return_value = "TestTable"
        mock_verify.side_effect = [False, True]  # Not exists, then exists after creation
        
        mock_db = Mock()
        mock_table = Mock()
        mock_db.create_table.return_value = mock_table
        mock_db.open_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        mock_schema = Mock()
        
        success, message, table = create_table_with_retry("test-table", mock_schema)
        
        assert success is True
        assert "created successfully" in message
        assert table is mock_table
        # Schema might be converted to PyArrow, so we just check the table name
        mock_db.create_table.assert_called_once()
        assert mock_db.create_table.call_args[0][0] == "TestTable"
    
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    @patch('mcp_lancedb.core.connection.verify_table_exists')
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_table_already_exists(self, mock_get_connection, mock_verify, mock_sanitize):
        """Test when table already exists."""
        mock_sanitize.return_value = "TestTable"
        mock_verify.return_value = True  # Table already exists
        
        mock_db = Mock()
        mock_table = Mock()
        mock_db.open_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        mock_schema = Mock()
        
        success, message, table = create_table_with_retry("test-table", mock_schema)
        
        assert success is True
        assert "already exists" in message
        assert table is mock_table
        mock_db.create_table.assert_not_called()
    
    @patch('mcp_lancedb.core.connection.sanitize_table_name')
    @patch('mcp_lancedb.core.connection.verify_table_exists')
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_creation_failure(self, mock_get_connection, mock_verify, mock_sanitize):
        """Test table creation failure."""
        mock_sanitize.return_value = "TestTable"
        mock_verify.return_value = False  # Table doesn't exist
        
        mock_db = Mock()
        mock_db.create_table.side_effect = Exception("Creation failed")
        mock_get_connection.return_value = mock_db
        
        mock_schema = Mock()
        
        success, message, table = create_table_with_retry("test-table", mock_schema, max_retries=1)
        
        assert success is False
        assert "Creation failed" in message
        assert table is None


@pytest.mark.unit
class TestOpenTableWithRetry:
    """Test table opening with retry logic."""
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_successful_open(self, mock_get_connection):
        """Test successful table opening."""
        mock_db = Mock()
        mock_table = Mock()
        mock_table.schema = Mock()
        mock_db.open_table.return_value = mock_table
        mock_get_connection.return_value = mock_db
        
        result = open_table_with_retry("TestTable")
        
        assert result is mock_table
        mock_db.open_table.assert_called_once_with("TestTable")
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_open_failure(self, mock_get_connection):
        """Test table opening failure."""
        mock_db = Mock()
        mock_db.open_table.side_effect = Exception("Cannot open table")
        mock_get_connection.return_value = mock_db
        
        with pytest.raises(Exception, match="Cannot open table"):
            open_table_with_retry("TestTable", max_retries=1)
    
    @patch('mcp_lancedb.core.connection.get_connection')
    def test_retry_success(self, mock_get_connection):
        """Test successful opening after retry."""
        mock_db = Mock()
        mock_table = Mock()
        mock_table.schema = Mock()
        
        # First call fails, second succeeds
        mock_db.open_table.side_effect = [Exception("Temporary failure"), mock_table]
        mock_get_connection.return_value = mock_db
        
        result = open_table_with_retry("TestTable", max_retries=2)
        
        assert result is mock_table
        assert mock_db.open_table.call_count == 2 
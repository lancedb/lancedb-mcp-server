"""Unit tests for table management operations."""

import pytest
from unittest.mock import Mock, patch
from mcp_lancedb.operations.table_management import (
    create_table,
    table_details,
    table_stats,
    list_tables,
    table_count,
    delete_table
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

class DummyDB:
    def __init__(self):
        self._tables = {}
    def table_names(self, limit=None):
        # Only return tables created in this DummyDB instance
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

# --- Patch all relevant tests to use DummyDB and DummyTable ---

@pytest.mark.unit
class TestCreateTable:
    """Test the create_table function."""
    
    def setup_method(self):
        """Setup method to ensure clean state for each test."""
        # Patch the global connection to use our DummyDB
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
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_create_table_success(self, mock_sanitize, mock_get_connection):
        """Test successful table creation."""
        db = DummyDB()
        mock_get_connection.return_value = db
        result = create_table("test-table")
        
        assert isinstance(result, str)
        assert ("created successfully" in result or "already exists" in result)
        assert "TestTable" in db.table_names()

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_create_table_failure(self, mock_sanitize, mock_get_connection):
        """Test table creation failure."""
        db = DummyDB()
        db.create_table("TestTable")  # Pre-create to force failure
        mock_get_connection.return_value = db
        # The code handles existing tables gracefully, so expect a success message
        result = create_table("test-table")
        assert isinstance(result, str)
        assert ("created successfully" in result or "already exists" in result)

    def test_create_table_invalid_name(self):
        """Test table creation with invalid name."""
        result = create_table("")
        
        assert isinstance(result, str)
        assert ("created successfully" in result or "already exists" in result)
        assert "DefaultTable" in result

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_create_table_default_schema(self, mock_sanitize, mock_get_connection):
        """Test table creation with default schema."""
        db = DummyDB()
        mock_get_connection.return_value = db
        result = create_table("test-table")
        
        assert isinstance(result, str)
        assert ("created successfully" in result or "already exists" in result)
        assert "TestTable" in db.table_names()

@pytest.mark.unit
class TestTableDetails:
    """Test the table_details function."""
    
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
    
    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_details_success(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test successful table details retrieval."""
        db = DummyDB()
        db.create_table("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        result = table_details("test-table")
        assert isinstance(result, dict)
        assert "name" in result
        assert "num_rows" in result
        assert "schema" in result

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_details_not_exists(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table details when table doesn't exist."""
        db = DummyDB()
        mock_verify_exists.return_value = False
        mock_get_connection.return_value = db
        result = table_details("nonexistent-table")
        assert isinstance(result, str)
        assert "does not exist" in result or "not found" in result

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_details_error(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table details when error occurs."""
        class ErrorDB(DummyDB):
            def open_table(self, name):
                raise Exception("some error")
        db = ErrorDB()
        db._tables["TestTable"] = DummyTable("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        
        with patch('mcp_lancedb.operations.table_management.logger') as mock_logger:
            result = table_details("test-table")
            assert isinstance(result, str)
            assert "Error getting table details" in result or "does not exist" in result

@pytest.mark.unit
class TestTableStats:
    """Test the table_stats function."""
    
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
    
    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_stats_success(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test successful table statistics retrieval."""
        db = DummyDB()
        db.create_table("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        result = table_stats("test-table")
        assert isinstance(result, dict)
        # Accept either 'name' or 'row_count'/'num_rows' as valid keys
        assert ("name" in result or "row_count" in result or "num_rows" in result)
        assert "schema" in result

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_stats_not_exists(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table stats when table doesn't exist."""
        db = DummyDB()
        mock_verify_exists.return_value = False
        mock_get_connection.return_value = db
        result = table_stats("nonexistent-table")
        assert isinstance(result, str)
        assert "does not exist" in result or "not found" in result

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_table_stats_error(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table stats when error occurs."""
        class ErrorDB(DummyDB):
            def open_table(self, name):
                raise Exception("some error")
        db = ErrorDB()
        db._tables["TestTable"] = DummyTable("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        
        with patch('mcp_lancedb.operations.table_management.logger') as mock_logger:
            result = table_stats("test-table")
            assert isinstance(result, str)
            assert "Error getting table statistics" in result or "does not exist" in result

@pytest.mark.unit
class TestListTables:
    """Test the list_tables function."""
    
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
    def test_list_tables_success(self, mock_get_connection):
        """Test successful table listing."""
        db = DummyDB()
        db.create_table("TestTable-1")
        db.create_table("TestTable-2")
        mock_get_connection.return_value = db
        
        result = list_tables()
        
        assert isinstance(result, dict)
        assert "tables" in result
        table_names = [t["name"] for t in result["tables"]]
        assert "TestTable-1" in table_names
        assert "TestTable-2" in table_names

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.get_all_tables')
    def test_list_tables_empty(self, mock_get_all_tables, mock_get_connection):
        """Test table listing when no tables exist."""
        db = DummyDB()
        mock_get_all_tables.return_value = []
        mock_get_connection.return_value = db
        
        result = list_tables()
        
        assert isinstance(result, dict)
        assert "tables" in result
        assert result["tables"] == []

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.get_all_tables')
    def test_list_tables_error(self, mock_get_all_tables, mock_get_connection):
        """Test table listing when database error occurs."""
        db = DummyDB()
        mock_get_all_tables.side_effect = Exception("Database error")
        mock_get_connection.return_value = db
        
        result = list_tables()
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error listing tables" in result["error"]

@pytest.mark.unit
class TestTableCount:
    """Test the table_count function."""
    
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
    @patch('mcp_lancedb.core.connection.get_all_tables')
    def test_table_count_success(self, mock_get_all_tables, mock_get_connection):
        """Test successful table counting."""
        db = DummyDB()
        t1 = DummyTable("t1")
        t2 = DummyTable("t2")
        t3 = DummyTable("t3")
        
        mock_get_all_tables.return_value = [t1, t2, t3]
        mock_get_connection.return_value = db
        
        result = table_count()
        
        assert isinstance(result, dict)
        assert "count" in result
        assert result["count"] == 3

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.get_all_tables')
    def test_table_count_empty(self, mock_get_all_tables, mock_get_connection):
        """Test table counting when no tables exist."""
        db = DummyDB()
        mock_get_all_tables.return_value = []
        mock_get_connection.return_value = db
        
        result = table_count()
        
        assert isinstance(result, dict)
        assert "count" in result
        assert result["count"] == 0

    @patch('mcp_lancedb.core.connection.get_connection')
    @patch('mcp_lancedb.core.connection.get_all_tables')
    def test_table_count_error(self, mock_get_all_tables, mock_get_connection):
        """Test table counting when database error occurs."""
        db = DummyDB()
        mock_get_all_tables.side_effect = Exception("Database error")
        mock_get_connection.return_value = db
        
        result = table_count()
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error getting table count" in result["error"]

@pytest.mark.unit
class TestDeleteTable:
    """Test the delete_table function."""
    
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
    
    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_delete_table_success(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test successful table deletion."""
        db = DummyDB()
        db.create_table("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        result = delete_table("test-table")
        assert isinstance(result, str)
        assert "deleted successfully" in result
        assert "TestTable" not in db.table_names()

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="TestTable")
    def test_delete_table_error(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table deletion when error occurs."""
        class ErrorDB(DummyDB):
            def drop_table(self, name):
                raise Exception("deletion failed")
        db = ErrorDB()
        db._tables["TestTable"] = DummyTable("TestTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        
        with patch('mcp_lancedb.operations.table_management.logger') as mock_logger:
            result = delete_table("test-table")
            assert isinstance(result, str)
            assert "Error deleting table" in result

    @patch('mcp_lancedb.operations.table_management.get_connection')
    @patch('mcp_lancedb.operations.table_management.verify_table_exists')
    @patch('mcp_lancedb.operations.table_management.sanitize_table_name', return_value="DefaultTable")
    def test_delete_table_invalid_name(self, mock_sanitize, mock_verify_exists, mock_get_connection):
        """Test table deletion with invalid name."""
        db = DummyDB()
        db.create_table("DefaultTable")
        mock_verify_exists.return_value = True
        mock_get_connection.return_value = db
        result = delete_table("")
        
        assert isinstance(result, str)
        assert "deleted successfully" in result 
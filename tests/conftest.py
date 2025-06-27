"""Pytest configuration and shared fixtures for MCP LanceDB tests."""

import pytest
import tempfile
import shutil
import os
from typing import Generator, List
from unittest.mock import patch
import logging
from mcp_lancedb.core.logger import get_logger

# Import test modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_lancedb import delete_table, list_tables, get_connection


@pytest.fixture(scope="session")
def test_db_path() -> Generator[str, None, None]:
    """Create a temporary database path for testing."""
    temp_dir = tempfile.mkdtemp(prefix="mcp_lancedb_test_")
    db_path = os.path.join(temp_dir, "test.lancedb")
    
    # Patch the LANCEDB_URI for all tests
    with patch('mcp_lancedb.core.config.LANCEDB_URI', db_path):
        with patch('mcp_lancedb.core.connection.LANCEDB_URI', db_path):
            with patch('mcp_lancedb.operations.table_management.LANCEDB_URI', db_path):
                with patch('mcp_lancedb.operations.document_management.LANCEDB_URI', db_path):
                    with patch('mcp_lancedb.operations.search_operations.LANCEDB_URI', db_path):
                        yield db_path
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def clean_db(test_db_path: str) -> Generator[str, None, None]:
    """Provide a clean database for each test."""
    # Clean up any existing tables before test
    try:
        tables = list_tables()
        if isinstance(tables, dict) and 'tables' in tables:
            for table_info in tables['tables']:
                table_name = table_info['name']
                delete_table(table_name)
    except Exception:
        pass  # Database might not exist yet
    
    yield test_db_path
    
    # Clean up after test
    try:
        tables = list_tables()
        if isinstance(tables, dict) and 'tables' in tables:
            for table_info in tables['tables']:
                table_name = table_info['name']
                delete_table(table_name)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def suppress_expected_test_errors():
    """Suppress expected error logging during tests to prevent test exceptions from appearing as real errors."""
    # Temporarily set logger level to CRITICAL to suppress ERROR logs during tests
    # This prevents intentional test exceptions from appearing as real errors
    logger = get_logger()
    original_level = logger.level
    
    # Set to CRITICAL to suppress ERROR and WARNING logs during tests
    logger.setLevel(logging.CRITICAL)
    
    yield
    
    # Restore original level after test
    logger.setLevel(original_level)


@pytest.fixture
def mock_lancedb_connection():
    """Mock LanceDB connection for testing."""
    with patch('mcp_lancedb.core.connection.lancedb.connect') as mock_connect:
        mock_db = mock_connect.return_value
        yield mock_db


@pytest.fixture
def sample_documents() -> List[str]:
    """Provide sample documents for testing."""
    return [
        "This is a test document about artificial intelligence.",
        "Machine learning is a subset of AI.",
        "Deep learning uses neural networks.",
        "Natural language processing helps computers understand text.",
        "Computer vision enables machines to see and interpret images."
    ]


@pytest.fixture
def sample_table_name() -> str:
    """Provide a standard test table name."""
    return "test-table"


@pytest.fixture
def custom_schema() -> dict:
    """Provide a custom schema for testing."""
    return {
        "doc": "str",
        "vector": "Vector(768)",
        "metadata": "str",
        "score": "float"
    }


@pytest.fixture
def test_queries() -> List[str]:
    """Provide test queries for search operations."""
    return [
        "machine learning",
        "programming language", 
        "vector database",
        "semantic search",
        "natural language"
    ]


@pytest.fixture
def sample_table_schema():
    """Sample table schema for testing."""
    from mcp_lancedb.core.schemas import Schema
    return Schema


class TestTableManager:
    """Helper class for managing test tables."""
    
    def __init__(self):
        self.created_tables = []
    
    def create_test_table(self, name: str, schema: dict = None) -> str:
        """Create a test table and track it for cleanup."""
        from mcp_lancedb import create_table
        result = create_table(name, schema)
        if "successfully" in result.lower():
            self.created_tables.append(name)
        return result
    
    def cleanup(self):
        """Clean up all created test tables."""
        for table_name in self.created_tables:
            try:
                delete_table(table_name)
            except Exception:
                pass
        self.created_tables.clear()


@pytest.fixture
def table_manager() -> Generator[TestTableManager, None, None]:
    """Provide a table manager for tests."""
    manager = TestTableManager()
    yield manager
    manager.cleanup()


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow 
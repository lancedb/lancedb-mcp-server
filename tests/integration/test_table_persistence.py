"""Integration tests for table persistence and data integrity."""

import pytest
from mcp_lancedb import (
    create_table,
    delete_table,
    list_tables,
    table_details,
    ingest_docs,
    query_table
)


@pytest.mark.integration
class TestTablePersistence:
    """Test that tables persist correctly across all operations."""
    
    def test_custom_table_persistence_workflow(self, clean_db):
        """Test complete workflow with custom table name."""
        test_table = "persistence-test"
        
        # Step 1: Create custom table
        result = create_table(test_table)
        assert "created successfully" in result
        
        # Step 2: Verify table appears in list
        tables = list_tables()
        assert isinstance(tables, dict)
        table_found = False
        for table in tables.get('tables', []):
            # Check for both original and sanitized names (case-insensitive)
            if (test_table.lower() in table['name'].lower() or 
                table['name'].lower() in test_table.lower() or
                "persistencetest" in table['name'].lower()):
                table_found = True
                assert table['num_rows'] == 0  # Should be empty initially
                break
        assert table_found, f"Table '{test_table}' not found in list"
        
        # Step 3: Get table details
        details = table_details(test_table)
        assert isinstance(details, dict)
        assert details['num_rows'] == 0
        assert 'schema' in details
        
        # Step 4: Ingest documents
        test_docs = [
            "Custom table test document 1",
            "Custom table test document 2", 
            "Persistence verification document"
        ]
        ingest_result = ingest_docs(test_table, test_docs)
        assert "Successfully" in ingest_result  # Fixed case sensitivity
        assert "3" in ingest_result
        
        # Step 5: Query the table
        query_result = query_table("test", test_table)  # Fixed parameter order
        assert isinstance(query_result, dict)
        assert "results" in query_result
        assert len(query_result["results"]) > 0
        
        # Verify content
        found_docs = [result.get("doc", "") for result in query_result["results"]]
        assert any("Custom table test" in doc for doc in found_docs)
        
        # Step 6: Final table details verification
        final_details = table_details(test_table)
        assert isinstance(final_details, dict)
        assert final_details['num_rows'] == 3
        
        # Step 7: Cross-function verification
        final_tables = list_tables()
        final_table_found = False
        for table in final_tables.get('tables', []):
            if (test_table.lower() in table['name'].lower() or 
                table['name'].lower() in test_table.lower() or
                "persistencetest" in table['name'].lower()):
                final_table_found = True
                assert table['num_rows'] == 3
                break
        assert final_table_found, f"Table '{test_table}' disappeared from final list"
        
        # Cleanup
        delete_result = delete_table(test_table)
        assert "deleted successfully" in delete_result or "alternative method" in delete_result
    
    def test_multiple_custom_tables_persistence(self, clean_db):
        """Test that multiple custom tables persist independently."""
        table1 = "multi-test-1"
        table2 = "multi-test-2"
        
        # Create both tables
        result1 = create_table(table1)
        result2 = create_table(table2)
        assert "created successfully" in result1
        assert "created successfully" in result2
        
        # Ingest different documents to each
        docs1 = ["Document for table 1", "Another doc for table 1"]
        docs2 = ["Document for table 2", "Another doc for table 2", "Third doc for table 2"]
        
        ingest1 = ingest_docs(table1, docs1)
        ingest2 = ingest_docs(table2, docs2)
        assert "Successfully" in ingest1  # Fixed case sensitivity
        assert "Successfully" in ingest2  # Fixed case sensitivity
        
        # Verify each table has correct data
        details1 = table_details(table1)
        details2 = table_details(table2)
        assert details1["num_rows"] == 2
        assert details2["num_rows"] == 3
        
        # Verify searches are isolated
        search1 = query_table("table 1", table1)  # Fixed parameter order
        search2 = query_table("table 2", table2)  # Fixed parameter order
        
        assert isinstance(search1, dict) and "results" in search1
        assert isinstance(search2, dict) and "results" in search2
        
        # Results should contain appropriate content
        results1_text = " ".join([r.get("doc", "") for r in search1["results"]])
        results2_text = " ".join([r.get("doc", "") for r in search2["results"]])
        
        assert "table 1" in results1_text.lower()
        assert "table 2" in results2_text.lower()
        
        # Verify both tables persist in listing (check for sanitized names too)
        tables = list_tables()
        found_tables = [t["name"] for t in tables["tables"]]
        
        table1_found = any(table1.lower() in name.lower() or name.lower() in table1.lower() or "multitest1" in name.lower() for name in found_tables)
        table2_found = any(table2.lower() in name.lower() or name.lower() in table2.lower() or "multitest2" in name.lower() for name in found_tables)
        
        assert table1_found, f"Table '{table1}' not found in final listing"
        assert table2_found, f"Table '{table2}' not found in final listing"
        
        # Cleanup
        delete_table(table1)
        delete_table(table2)
    
    def test_table_accessibility_after_operations(self, clean_db):
        """Test that tables remain accessible after various operations."""
        table_name = "accessibility-test"
        
        # Create table
        create_result = create_table(table_name)
        assert "created successfully" in create_result
        
        # Perform multiple operations and verify accessibility after each
        operations = [
            ("Initial details", lambda: table_details(table_name)),
            ("List tables", lambda: list_tables()),
            ("Ingest docs", lambda: ingest_docs(table_name, ["Test document"])),
            ("Query table", lambda: query_table("test", table_name)),  # Fixed parameter order
            ("Final details", lambda: table_details(table_name)),
        ]
        
        for operation_name, operation_func in operations:
            result = operation_func()
            
            # Verify operation succeeded
            if operation_name in ["Initial details", "Final details"]:
                assert isinstance(result, dict), f"{operation_name} failed: {result}"
                assert "num_rows" in result
            elif operation_name == "List tables":
                assert isinstance(result, dict), f"{operation_name} failed: {result}"
                assert "tables" in result
            elif operation_name == "Ingest docs":
                assert "Successfully" in result, f"{operation_name} failed: {result}"  # Fixed case sensitivity
            elif operation_name == "Query table":
                assert isinstance(result, dict), f"{operation_name} failed: {result}"
                assert "results" in result
            
            # After each operation, verify table is still accessible
            verification = table_details(table_name)
            assert isinstance(verification, dict), f"Table became inaccessible after {operation_name}"
        
        # Cleanup
        delete_table(table_name)


@pytest.mark.integration
class TestTableNamingSanitization:
    """Test that table name sanitization works correctly."""
    
    @pytest.mark.parametrize("original_name,expected_pattern", [
        ("test-table", "TestTable"),
        ("my_awesome_table", "MyAwesomeTable"),
        ("test.table.name", "TestTableName"),
        ("mixed-name_test.final", "MixedNameTestFinal"),
        ("simple", "Simple"),
    ])
    def test_table_name_sanitization(self, clean_db, original_name, expected_pattern):
        """Test that various table names are sanitized correctly."""
        # Create table with problematic name
        result = create_table(original_name)
        assert "created successfully" in result
        
        # Verify table exists (may have sanitized name)
        tables = list_tables()
        table_names = [t["name"] for t in tables["tables"]]
        
        # Should find a table that matches the expected pattern
        found_sanitized = any(expected_pattern.lower() in name.lower() for name in table_names)
        assert found_sanitized, f"Sanitized table name not found. Expected pattern: {expected_pattern}, Found: {table_names}"
        
        # Operations should work with original name
        ingest_result = ingest_docs(original_name, ["Test document"])
        assert "Successfully" in ingest_result  # Fixed case sensitivity
        
        query_result = query_table("test", original_name)  # Fixed parameter order
        assert isinstance(query_result, dict)
        assert "results" in query_result
        
        details_result = table_details(original_name)
        assert isinstance(details_result, dict)
        assert details_result["num_rows"] == 1
        
        # Cleanup
        delete_table(original_name) 
"""Integration tests for complete MCP LanceDB workflows."""

import pytest
from typing import List, Dict, Any
from mcp_lancedb import (
    create_table,
    delete_table,
    list_tables,
    table_count,
    table_details,
    table_stats,
    ingest_docs,
    query_table,
    hybrid_search
)


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete document ingestion and search workflow."""
    
    def test_default_table_workflow(self, clean_db, sample_documents, sample_table_name):
        """Test complete workflow with default table schema."""
        # Step 1: Create table
        result = create_table(sample_table_name)
        assert "created successfully" in result
        
        # Step 2: Verify table exists in listing
        tables = list_tables()
        assert isinstance(tables, dict)
        assert tables["count"] >= 1
        table_names = [t["name"] for t in tables["tables"]]
        # Account for table name sanitization (test-table -> TestTable)
        assert any(sample_table_name.lower() in name.lower() or name.lower() in sample_table_name.lower() or 
                  "testtable" in name.lower() for name in table_names)
        
        # Step 2.1: Test table_count API consistency
        count_info = table_count()
        assert isinstance(count_info, dict)
        assert "count" in count_info
        assert "message" in count_info
        assert count_info["count"] == tables["count"]  # Both APIs should return same count
        
        # Step 3: Ingest documents
        ingest_result = ingest_docs(sample_table_name, sample_documents)
        assert "Successfully" in ingest_result
        assert str(len(sample_documents)) in ingest_result
        
        # Step 4: Verify table has data
        details = table_details(sample_table_name)
        assert isinstance(details, dict)
        assert details["num_rows"] == len(sample_documents)
        
        # Step 5: Perform search
        search_result = query_table("machine learning", sample_table_name, top_k=3)  # Fixed parameter order
        assert isinstance(search_result, dict)
        assert "results" in search_result
        assert len(search_result["results"]) > 0
        
        # Step 6: Verify search results contain expected content
        found_ml_doc = any("machine learning" in result.get("doc", "").lower() 
                          for result in search_result["results"])
        assert found_ml_doc
        
        # Step 7: Clean up
        delete_result = delete_table(sample_table_name)
        assert "deleted successfully" in delete_result or "alternative method" in delete_result
    
    def test_custom_schema_workflow(self, clean_db, sample_documents):
        """Test workflow with custom schema using automatic embedding dimensions."""
        table_name = "custom-schema-test"
        additional_fields = {"category": "str", "timestamp": "str"}
        
        # Step 1: Create table with custom schema (dimensions determined by embedding model)
        custom_schema = {
            "doc": "str",
            "vector": "Vector(384)",  # Use default model dimensions
            **additional_fields
        }
        result = create_table(table_name, custom_schema)
        assert "created successfully" in result
        
        # Step 2: Verify table structure
        stats = table_stats(table_name)
        assert isinstance(stats, dict)
        assert stats["row_count"] == 0  # Empty initially
        
        # Step 3: Ingest documents using default embedding model
        ingest_result = ingest_docs(table_name, sample_documents[:3])
        assert "Successfully" in ingest_result
        
        # Step 4: Verify data ingestion
        updated_stats = table_stats(table_name)
        assert updated_stats["row_count"] == 3
        
        # Step 5: Perform hybrid search
        hybrid_result = hybrid_search(
            "vector database",
            table_name, 
            top_k=2  # Fixed parameter order and name
        )
        assert isinstance(hybrid_result, dict)
        assert len(hybrid_result["results"]) > 0
        
        # Clean up
        delete_table(table_name)


@pytest.mark.integration
class TestMultiTableOperations:
    """Test operations across multiple tables."""
    
    def test_multiple_tables_isolation(self, clean_db, sample_documents):
        """Test that multiple tables work independently."""
        table1 = "table-one"
        table2 = "table-two"
        
        # Create two tables
        result1 = create_table(table1)
        result2 = create_table(table2)
        assert "created successfully" in result1
        assert "created successfully" in result2
        
        # Ingest different documents to each
        docs1 = sample_documents[:2]
        docs2 = sample_documents[2:4]
        
        ingest1 = ingest_docs(table1, docs1)
        ingest2 = ingest_docs(table2, docs2)
        assert "Successfully" in ingest1
        assert "Successfully" in ingest2
        
        # Verify each table has correct data
        details1 = table_details(table1)
        details2 = table_details(table2)
        assert details1["num_rows"] == 2
        assert details2["num_rows"] == 2
        
        # Verify searches are isolated
        search1 = query_table("machine learning", table1, top_k=5)  # Fixed parameter order
        search2 = query_table("machine learning", table2, top_k=5)  # Fixed parameter order
        
        # Results should be different (different document sets)
        results1_docs = [r.get("doc", "") for r in search1["results"]]
        results2_docs = [r.get("doc", "") for r in search2["results"]]
        
        # At least one result set should be different
        assert results1_docs != results2_docs or len(results1_docs) != len(results2_docs)
        
        # Clean up
        delete_table(table1)
        delete_table(table2)
    
    def test_table_listing_accuracy(self, clean_db):
        """Test that table listing accurately reflects created tables."""
        initial_tables = list_tables()
        initial_count = initial_tables["count"]
        
        # Create multiple tables
        table_names = ["list-test-1", "list-test-2", "list-test-3"]
        for name in table_names:
            result = create_table(name)
            assert "created successfully" in result
        
        # Verify listing shows all tables (account for sanitization)
        updated_tables = list_tables()
        assert updated_tables["count"] >= initial_count + 3  # Allow for sanitization effects
        
        listed_names = [t["name"] for t in updated_tables["tables"]]
        for expected_name in table_names:
            # Check if any listed name contains our expected name (due to sanitization)
            # Convert expected patterns: list-test-1 -> ListTest1
            expected_patterns = [
                expected_name.lower(),
                "".join(word.capitalize() for word in expected_name.replace('-', ' ').split()).lower(),
                expected_name.replace('-', '').lower()
            ]
            found = any(
                any(pattern in listed_name.lower() for pattern in expected_patterns)
                for listed_name in listed_names
            )
            assert found, f"No table matching '{expected_name}' found in {listed_names}"
        
        # Test table_count consistency with list_tables
        count_result = table_count()
        assert count_result["count"] == updated_tables["count"]
        assert "table" in count_result["message"]
        
        # Clean up
        for name in table_names:
            delete_table(name)


@pytest.mark.integration
class TestErrorHandlingWorkflow:
    """Test error handling in complete workflows."""
    
    def test_nonexistent_table_operations(self, clean_db):
        """Test operations on non-existent tables."""
        fake_table = "nonexistent-table"
        
        # All operations should handle non-existent table gracefully
        details = table_details(fake_table)
        assert isinstance(details, str) and "Error" in details
        
        stats = table_stats(fake_table)
        assert isinstance(stats, str) and "Error" in stats
        
        search = query_table("test query", fake_table)  # Fixed parameter order
        assert isinstance(search, str) and "Error" in search
        
        # Test ingest with auto_create_table=False to ensure it errors
        ingest = ingest_docs(fake_table, ["test doc"], auto_create_table=False)
        assert isinstance(ingest, str) and "Error" in ingest
    
    def test_invalid_operations_sequence(self, clean_db, sample_documents):
        """Test invalid operation sequences."""
        table_name = "invalid-ops-test"
        
        # Try to ingest before creating table (with auto_create=False)
        ingest_result = ingest_docs(table_name, sample_documents, auto_create_table=False)
        assert "Error" in ingest_result
        
        # Create table properly
        create_result = create_table(table_name)
        assert "created successfully" in create_result
        
        # Now ingestion should work
        ingest_result = ingest_docs(table_name, sample_documents)
        assert "Successfully" in ingest_result
        
        # Try to create table again (should handle gracefully)
        create_again = create_table(table_name)
        # Should either succeed (table exists) or give appropriate message
        assert "Successfully" in create_again or "exists" in create_again
        
        # Clean up
        delete_table(table_name)


@pytest.mark.integration
@pytest.mark.slow
class TestLargeDataWorkflow:
    """Test workflows with larger datasets."""
    
    def test_batch_ingestion_and_search(self, clean_db):
        """Test ingestion and search with larger document batches."""
        table_name = "large-batch-test"
        
        # Generate larger document set
        large_docs = [
            f"Document {i}: This is a test document about topic {i % 5}. "
            f"It contains information about {'AI' if i % 2 == 0 else 'machine learning'}."
            for i in range(20)
        ]
        
        # Create table
        result = create_table(table_name)
        assert "created successfully" in result
        
        # Ingest large batch
        ingest_result = ingest_docs(table_name, large_docs)
        assert "Successfully" in ingest_result
        assert "20" in ingest_result
        
        # Verify all documents were ingested
        details = table_details(table_name)
        assert details["num_rows"] == 20
        
        # Test search with different limits
        small_search = query_table("AI", table_name, top_k=5)  # Fixed parameter order
        large_search = query_table("AI", table_name, top_k=15)  # Fixed parameter order
        
        assert len(small_search["results"]) <= 5
        assert len(large_search["results"]) <= 15
        assert len(large_search["results"]) >= len(small_search["results"])
        
        # Test hybrid search
        hybrid_result = hybrid_search("machine learning", table_name, top_k=10)  # Fixed parameter order
        assert len(hybrid_result["results"]) <= 10
        
        # Clean up
        delete_table(table_name) 
# MCP LanceDB - QA Functional Testing Guide

> **🎯 Purpose**: Comprehensive functional testing scenarios for MCP LanceDB client validation.

## 📋 **Overview**

MCP LanceDB provides 11 tools for vector database operations through Claude's MCP interface. This guide covers systematic testing of all functionality.

**Available Tools:**
- **Table Management**: `create_table`, `list_tables`, `table_count`, `table_details`, `table_stats`, `delete_table`
- **Document Operations**: `ingest_docs`, `update_documents`, `delete_documents`
- **Search Operations**: `query_table`, `hybrid_search`

**Key Design Principle:** Vector dimensions are automatically determined by the configured embedding model (default: 384 dimensions for `all-MiniLM-L6-v2`). No manual dimension specification is required or supported.

## 🧪 **Functional Test Scenarios**

### **1. Table Management Testing**

#### **1.1 Basic Table Creation**
```json
{
  "tool": "create_table",
  "arguments": {
    "table_name": "basic_test_table"
  }
}
```

**✅ Expected:**
- Success message: `"Table basic_test_table created successfully"`
- Default schema: `doc` (string) + `vector` (384 dimensions automatically)

**🔍 Validate:** Check `table_details` shows correct schema with automatic dimensions

#### **1.2 Custom Schema Tables**
```json
{
  "tool": "create_table",
  "arguments": {
    "table_name": "custom_schema_table",
    "schema": {
      "doc": "str",
      "vector": "Vector(384)",
      "category": "str",
      "score": "float",
      "metadata": "str"
    }
  }
}
```

**✅ Expected:**
- Success with 384-dimensional vectors (matching embedding model)
- Custom fields included: `category`, `score`, `metadata`
- Total schema fields: 5 (doc + vector + 3 custom)

**🔍 Note:** Vector dimensions must match the embedding model's output (384 for default model)

#### **1.3 Table Information Retrieval**
```json
// Test each command
{"tool": "list_tables", "arguments": {}}
{"tool": "table_count", "arguments": {}}
{"tool": "table_details", "arguments": {"table_name": "custom_schema_table"}}
{"tool": "table_stats", "arguments": {"table_name": "custom_schema_table"}}
```

**✅ Expected Results:**
- `list_tables`: Array of all tables with row counts and total count
- `table_count`: Lightweight operation returning only total table count (e.g., `{"count": 55, "message": "Database contains 55 tables"}`)
- `table_details`: Complete schema breakdown with field types
- `table_stats`: Detailed statistics including automatic vector dimensions (384)

**🔍 Performance Notes:**
- `table_count()`: Fastest option when you only need the count
- `list_tables()`: More comprehensive but slightly slower due to row counting per table

#### **1.4 Table Count API Validation**
```json
// Test the dedicated table count API
{"tool": "table_count", "arguments": {}}

// Compare with list_tables count
{"tool": "list_tables", "arguments": {}}
```

**✅ Expected:**
- `table_count()` returns: `{"count": N, "message": "Database contains N tables"}`
- Both methods return identical count values
- `table_count()` executes faster (no row counting overhead)
- Uses proper LanceDB API with `db.table_names(limit=1000)` (not filesystem operations)

**🔍 Validation Points:**
- Count accuracy: Both APIs return same number
- Performance: `table_count()` completes in < 1 second
- No limit issues: Returns all tables (not default limit of 10)
- Proper API usage: Uses LanceDB's `table_names()` method with high limit

#### **1.5 Table Name Sanitization**
```json
{
  "tool": "create_table",
  "arguments": {
    "table_name": "test-table.with_special@chars"
  }
}
```

**✅ Expected:**
- Table created with sanitized name (CamelCase format)
- Original name referenced in success message
- `list_tables` shows sanitized version

#### **1.6 Duplicate Table Handling**
```json
// Create same table twice
{
  "tool": "create_table",
  "arguments": {
    "table_name": "duplicate_test"
  }
}
```

**✅ Expected:**
- First: Success message
- Second: Error about table already existing
- No data corruption or overwrites

### **2. Document Management Testing**

#### **2.1 Single Document Ingestion**
```json
{
  "tool": "ingest_docs",
  "arguments": {
    "docs": ["This is a comprehensive test document about machine learning and artificial intelligence."],
    "table_name": "custom_schema_table",
    "auto_create_table": true
  }
}
```

**✅ Expected:**
- Success: `"Successfully added 1 documents to table custom_schema_table"`
- Automatic vector embedding generation (384 dimensions)
- Document retrievable via search

#### **2.2 Batch Document Ingestion**
```json
{
  "tool": "ingest_docs",
  "arguments": {
    "docs": [
      "Python programming language for data science and machine learning applications",
      "Vector databases enable semantic search capabilities for modern applications",
      "LanceDB provides high-performance vector storage with Apache Arrow integration",
      "Natural language processing using transformer models and attention mechanisms",
      "Deep learning architectures for computer vision and image recognition tasks",
      "Retrieval-augmented generation combines language models with external knowledge",
      "Embeddings capture semantic meaning in high-dimensional vector spaces",
      "Claude AI assistant powered by constitutional AI and helpful behavior",
      "Machine learning operations and MLOps for production model deployment",
      "Data engineering pipelines for processing large-scale datasets efficiently"
    ],
    "table_name": "custom_schema_table"
  }
}
```

**✅ Expected:**
- Success: `"Successfully added 10 documents"`
- All documents have unique embeddings (384 dimensions each)
- Total table count: 11 documents (1 + 10)

#### **2.3 Unicode and Special Content**
```json
{
  "tool": "ingest_docs",
  "arguments": {
    "docs": [
      "测试中文文档处理和向量嵌入生成功能",
      "Тестирование обработки русских документов",
      "🚀 Testing emoji content: 📊📈🎯💡🔍",
      "Special characters: @#$%^&*()+={}[]|\\:;\"'<>?,./",
      "JSON-like content: {\"key\": \"value\", \"nested\": {\"array\": [1,2,3]}}",
      "Code snippet: def function(x): return x**2 + 1",
      "Very long document: " + "Lorem ipsum dolor sit amet. " * 100
    ],
    "table_name": "custom_schema_table"
  }
}
```

**✅ Expected:**
- All Unicode content processed correctly
- No encoding errors or crashes
- Embeddings generated for all documents (384 dimensions each)
- Long documents handled properly

#### **2.4 Document Updates and Deletions**
```json
// First, add documents with metadata
{
  "tool": "ingest_docs",
  "arguments": {
    "docs": ["Document to be updated", "Document to be deleted"],
    "table_name": "custom_schema_table"
  }
}

// Then test updates (Note: This may not work if no metadata filtering is available)
{
  "tool": "update_documents",
  "arguments": {
    "table_name": "custom_schema_table",
    "filter_expr": "doc LIKE '%updated%'",
    "updates": {"category": "modified"}
  }
}

// Test deletions
{
  "tool": "delete_documents",
  "arguments": {
    "table_name": "custom_schema_table",
    "filter_expr": "doc LIKE '%deleted%'"
  }
}
```

**✅ Expected:**
- Update operations modify specified documents
- Delete operations remove matching documents
- Table count decreases appropriately
- Non-matching documents remain unchanged

### **3. Search Operations Testing**

#### **3.1 Basic Vector Search**
```json
{
  "tool": "query_table",
  "arguments": {
    "query": "machine learning and artificial intelligence",
    "table_name": "custom_schema_table",
    "top_k": 5
  }
}
```

**✅ Expected:**
- Returns 5 most relevant documents
- Results ranked by similarity (highest first)
- Includes distance and similarity scores
- Semantically relevant matches (ML/AI content)
- Vector embeddings automatically generated (384 dimensions)

#### **3.2 Hybrid Search with Metrics**
Test each distance metric:
```json
// Cosine similarity (default)
{
  "tool": "hybrid_search",
  "arguments": {
    "query": "vector database storage",
    "table_name": "custom_schema_table",
    "top_k": 3,
    "metric": "cosine"
  }
}

// Euclidean distance
{
  "tool": "hybrid_search",
  "arguments": {
    "query": "vector database storage",
    "table_name": "custom_schema_table",
    "top_k": 3,
    "metric": "euclidean"
  }
}

// Dot product
{
  "tool": "hybrid_search",
  "arguments": {
    "query": "vector database storage",
    "table_name": "custom_schema_table",
    "top_k": 3,
    "metric": "dot"
  }
}
```

**✅ Expected:**
- Each metric returns valid results
- Different ranking orders for same query
- Vector database/LanceDB content ranked highly
- All distance values are reasonable (0-2 range typically)

#### **3.3 Search Result Consistency**
```json
// Run same query multiple times
{
  "tool": "query_table",
  "arguments": {
    "query": "python programming data science",
    "table_name": "custom_schema_table",
    "top_k": 3
  }
}
```

**✅ Expected:**
- Identical results for identical queries
- Consistent similarity scores
- Stable ranking order

#### **3.4 Edge Case Searches**
```json
// Empty query
{
  "tool": "query_table",
  "arguments": {
    "query": "",
    "table_name": "custom_schema_table",
    "top_k": 3
  }
}

// Very specific query
{
  "tool": "query_table",
  "arguments": {
    "query": "Apache Arrow integration high-performance",
    "table_name": "custom_schema_table",
    "top_k": 1
  }
}

// Irrelevant query
{
  "tool": "query_table",
  "arguments": {
    "query": "quantum physics biochemistry astronomy",
    "table_name": "custom_schema_table",
    "top_k": 2
  }
}
```

**✅ Expected:**
- Empty query: Returns some results (random or first documents)
- Specific query: Returns highly relevant LanceDB content
- Irrelevant query: Returns best available matches with lower scores

### **4. Error Handling & Edge Cases**

#### **4.1 Invalid Parameters**
```json
// Invalid table name
{"tool": "create_table", "arguments": {"table_name": ""}}

// Invalid document types
{"tool": "ingest_docs", "arguments": {"docs": [null, 123, {"object": "invalid"}], "table_name": "custom_schema_table"}}

// Invalid top_k
{"tool": "query_table", "arguments": {"query": "test", "table_name": "custom_schema_table", "top_k": -5}}
```

**✅ Expected:**
- Clear error messages for each invalid parameter
- No crashes or data corruption
- Helpful guidance on correct formats

#### **4.2 Nonexistent Resources**
```json
// Nonexistent table operations
{"tool": "query_table", "arguments": {"query": "test", "table_name": "does_not_exist", "auto_create_table": false}}
{"tool": "table_details", "arguments": {"table_name": "missing_table"}}
{"tool": "delete_table", "arguments": {"table_name": "not_found"}}
```

**✅ Expected:**
- Specific error messages about missing resources
- No side effects or partial operations
- Clear guidance on resolution

#### **4.3 Schema Validation**
```json
// Invalid vector dimensions (mismatched with embedding model)
{
  "tool": "create_table",
  "arguments": {
    "table_name": "invalid_dimensions_table",
    "schema": {
      "doc": "str",
      "vector": "Vector(768)"  // Wrong! Should be 384 for default model
    }
  }
}

// Missing required fields
{
  "tool": "create_table",
  "arguments": {
    "table_name": "invalid_schema_table",
    "schema": {"only_text": "str"}
  }
}
```

**✅ Expected:**
- Dimension mismatch errors when schema doesn't match embedding model
- Required field warnings (doc, vector)
- Clear guidance about automatic dimension detection

### **5. Performance & Stress Testing**

#### **5.1 Large Document Batches**
```json
{
  "tool": "ingest_docs",
  "arguments": {
    "docs": [/* Generate 50 varied documents */],
    "table_name": "performance_test_table"
  }
}
```

**✅ Expected Benchmarks:**
- 50 documents: < 60 seconds
- No memory errors or timeouts
- All documents successfully processed with 384-dimensional embeddings

#### **5.2 High-Volume Search Testing**
- Execute 20 different search queries rapidly
- Vary query lengths and complexity

**✅ Expected Performance:**
- Average response time: < 3 seconds per query
- No degradation in later queries
- Consistent result quality
- All searches use automatic 384-dimensional embeddings

#### **5.3 Multi-Table Operations**
- Create 5 different tables
- Populate each with different content
- Perform searches across all tables

**✅ Expected:**
- Tables remain isolated
- No cross-contamination of results
- Consistent performance across tables
- All tables use same embedding dimensions automatically

## 🔍 **Validation Criteria**

### **Functional Requirements ✅**
- [ ] All 11 tools respond correctly
- [ ] Vector embeddings generated automatically (384 dimensions)
- [ ] Search results ranked by semantic relevance
- [ ] Tables persist between operations
- [ ] Unicode/special characters handled
- [ ] Error messages are clear and actionable
- [ ] No manual dimension specification required

### **Data Integrity ✅**
- [ ] No data loss during operations
- [ ] Consistent search results for identical queries
- [ ] Table isolation maintained
- [ ] Schema constraints enforced (including automatic dimensions)
- [ ] Document updates/deletes work correctly

### **Performance Standards ✅**
- [ ] Document ingestion: < 2 seconds per document
- [ ] Search queries: < 3 seconds response time
- [ ] Table operations: < 5 seconds
- [ ] Memory usage remains stable
- [ ] Embedding generation maintains consistent 384 dimensions

### **Error Handling ✅**
- [ ] Invalid inputs handled gracefully
- [ ] Clear error messages with guidance
- [ ] No crashes on edge cases
- [ ] Partial failures don't corrupt data
- [ ] Resource conflicts managed properly
- [ ] Schema validation prevents dimension mismatches

## 📊 **Test Execution Summary**

### **Core Functionality** (Essential - 25 minutes)
1. Basic table creation and management (automatic dimensions)
2. Document ingestion and search
3. Error handling for invalid inputs

### **Extended Testing** (Recommended - 35 minutes)
4. Unicode/special character support
5. Multiple search metrics and edge cases
6. Document updates and deletions

### **Stress Testing** (Production Readiness - 30 minutes)
7. Performance benchmarks
8. Multi-table isolation
9. Large document handling

**Total Comprehensive Testing: ~90 minutes**

---

**🎯 Success Criteria**: All functional requirements met + no data integrity issues + performance within benchmarks + automatic dimension handling = Production Ready ✅ 
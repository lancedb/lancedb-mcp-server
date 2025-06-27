"""Unit tests for schema creation and validation in LanceDB MCP server."""

import pytest
from pydantic import ValidationError
from mcp_lancedb.core.schemas import Schema, create_custom_schema, create_schema_from_dict, DocumentInput
import src.mcp_lancedb.core.schemas  # Ensure coverage tracking


def test_document_input_accepts_string():
    # Should accept a single string
    doc = DocumentInput(docs="hello world")
    assert doc.docs == "hello world"

def test_document_input_accepts_list():
    # Should accept a list of strings
    doc = DocumentInput(docs=["a", "b", "c"])
    assert doc.docs == ["a", "b", "c"]

def test_document_input_rejects_non_string():
    # Should raise ValidationError for non-string/list
    with pytest.raises(ValidationError):
        DocumentInput(docs=123)

def test_document_input_rejects_list_of_non_strings():
    # Should raise ValidationError for list of non-strings
    with pytest.raises(ValidationError):
        DocumentInput(docs=[1, 2, 3])

def test_default_schema_fields():
    # Schema should have 'doc' and 'vector' fields
    s = Schema(doc="foo", vector=[0.0]*384)
    assert hasattr(s, "doc")
    assert hasattr(s, "vector")
    assert isinstance(s.doc, str)
    assert isinstance(s.vector, list)
    assert len(s.vector) == 384

def test_create_custom_schema_basic():
    # Should create a schema with custom vector dimensions
    Custom = create_custom_schema(128)
    s = Custom(doc="bar", vector=[0.0]*128)
    assert hasattr(s, "doc")
    assert hasattr(s, "vector")
    assert len(s.vector) == 128

def test_create_custom_schema_with_additional_fields():
    # Should add extra fields with correct types
    Custom = create_custom_schema(16, {"user_id": int, "score": float, "flag": bool})
    s = Custom(doc="baz", vector=[0.0]*16, user_id=42, score=3.14, flag=True)
    assert s.user_id == 42
    assert isinstance(s.score, float)
    assert s.flag is True

def test_create_custom_schema_with_type_strings():
    # Should accept type names as strings
    Custom = create_custom_schema(8, {"category": "str", "count": "int64"})
    s = Custom(doc="x", vector=[0.0]*8, category="cat", count=7)
    assert s.category == "cat"
    assert s.count == 7

def test_create_custom_schema_invalid_field_type():
    # Should fallback to str if type can't be resolved
    Custom = create_custom_schema(4, {"mystery": "unknown_type"})
    s = Custom(doc="y", vector=[0.0]*4, mystery="something")
    assert isinstance(s.mystery, str)

def test_create_schema_from_dict_basic():
    # Should create a schema from a dict
    schema_dict = {"doc": "str", "vector": "Vector(10)", "score": "float"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="z", vector=[0.0]*10, score=1.23)
    assert s.doc == "z"
    assert len(s.vector) == 10
    assert s.score == 1.23

def test_create_schema_from_dict_type_resolution():
    # Should resolve int, float, bool, bytes
    schema_dict = {"doc": "str", "vector": "Vector(5)", "flag": "bool", "data": "bytes"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="a", vector=[0.0]*5, flag=True, data=b"abc")
    assert s.flag is True
    assert s.data == b"abc"

def test_create_schema_from_dict_invalid_type():
    # Should fallback to str for unknown types
    schema_dict = {"doc": "str", "vector": "Vector(3)", "mystery": "unknown_type"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="b", vector=[0.0]*3, mystery="foo")
    assert isinstance(s.mystery, str)

def test_create_schema_from_dict_missing_vector_dims():
    # Should use default dims if not specified
    schema_dict = {"doc": "str", "vector": "float", "extra": "int"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="c", vector=[0.0]*384, extra=99)
    assert len(s.vector) == 384
    assert s.extra == 99

def test_create_schema_from_dict_additional_fields():
    # Should add all additional fields
    schema_dict = {"doc": "str", "vector": "Vector(2)", "foo": "str", "bar": "int"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="d", vector=[0.0, 1.0], foo="hi", bar=7)
    assert s.foo == "hi"
    assert s.bar == 7

def test_create_schema_from_dict_field_type_objects():
    # Should accept actual type objects
    schema_dict = {"doc": str, "vector": "Vector(2)", "score": float}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="e", vector=[0.0, 1.0], score=2.71)
    assert s.score == 2.71

def test_create_schema_from_dict_vector_type_string_fallback():
    # Should fallback to default dims if Vector() string is malformed
    schema_dict = {"doc": "str", "vector": "Vector(xyz)", "foo": "str"}
    Custom = create_schema_from_dict(schema_dict)
    s = Custom(doc="f", vector=[0.0]*384, foo="bar")
    assert len(s.vector) == 384
    assert s.foo == "bar" 
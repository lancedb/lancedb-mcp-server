"""Schema definitions and utilities for LanceDB MCP server."""

from typing import List, Union
from pydantic import BaseModel, Field
from lancedb.pydantic import LanceModel, Vector
from .config import model

class Schema(LanceModel):
    """Default schema for LanceDB table."""
    doc: str = model.SourceField()
    vector: Vector(model.ndims()) = model.VectorField()

class DocumentInput(BaseModel):
    """Input model for document ingestion."""
    docs: Union[str, List[str]] = Field(..., description="Document or list of documents to ingest")

def create_custom_schema(vector_dimensions: int, additional_fields: dict = None):
    """
    Create a custom schema class with specified vector dimensions.
    
    Args:
        vector_dimensions (int): Number of vector dimensions
        additional_fields (dict): Optional additional fields
        
    Returns:
        LanceModel: Custom schema class
    """
    # Create dynamic schema with custom dimensions
    class_attrs = {"__module__": __name__}
    annotations = {
        "doc": str,
        "vector": Vector(vector_dimensions)
    }
    
    # Add the required fields
    class_attrs["doc"] = model.SourceField()
    class_attrs["vector"] = model.VectorField()
    
    # Add additional fields if provided
    if additional_fields:
        type_map = {
            'str': str, 'string': str,
            'int': int, 'integer': int, 'int64': int,
            'float': float, 'double': float, 'float64': float,
            'bool': bool, 'boolean': bool
        }
        for field_name, field_type in additional_fields.items():
            if isinstance(field_type, str):
                if field_type.lower() in type_map:
                    annotations[field_name] = type_map[field_type.lower()]
                else:
                    # Try to resolve the type name
                    try:
                        annotations[field_name] = eval(field_type)
                    except Exception:
                        annotations[field_name] = str
            else:
                annotations[field_name] = field_type
    
    class_attrs["__annotations__"] = annotations
    
    # Create the dynamic schema class
    return type(f"Schema_{vector_dimensions}D", (LanceModel,), class_attrs)

def create_schema_from_dict(schema_dict: dict):
    """
    Create a schema class from a dictionary definition.
    
    Args:
        schema_dict (dict): Schema definition with field names and types
        
    Returns:
        LanceModel: Custom schema class
    """
    # Create proper type mappings
    type_map = {
        'str': str,
        'int': int,
        'int64': int,
        'float': float,
        'float64': float,
        'bool': bool,
        'bytes': bytes
    }
    
    # Process schema and build proper class attributes
    class_attrs = {"__module__": __name__}
    annotations = {}
    
    for field_name, field_type in schema_dict.items():
        if field_name == "doc":
            annotations["doc"] = str
            class_attrs["doc"] = model.SourceField()
        elif field_name == "vector":
            # Handle vector field - extract dimensions if specified
            if isinstance(field_type, str) and field_type.startswith("Vector"):
                # Extract dimensions from Vector(n) format
                import re
                match = re.search(r'Vector\((\d+)\)', field_type)
                dims = int(match.group(1)) if match else model.ndims()
                annotations["vector"] = Vector(dims)
            else:
                annotations["vector"] = Vector(model.ndims())
            class_attrs["vector"] = model.VectorField()
        else:
            # Handle other field types
            if isinstance(field_type, str):
                # Convert string type names to actual types
                if field_type in type_map:
                    annotations[field_name] = type_map[field_type]
                else:
                    # Try to resolve the type name
                    try:
                        annotations[field_name] = eval(field_type)
                    except:
                        # Default to str if type can't be resolved
                        annotations[field_name] = str
            else:
                # Use the type as-is
                annotations[field_name] = field_type
    
    # Add annotations to class attributes
    class_attrs["__annotations__"] = annotations
    
    # Create the dynamic schema class
    return type("CustomSchema", (LanceModel,), class_attrs) 
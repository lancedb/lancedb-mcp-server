import os
import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from mcp.server.fastmcp import FastMCP
from typing import List, Optional, Union


LANCEDB_URI = os.environ.get("LANCEDB_URI", "~/lancedb")
TABLE_NAME =  os.environ.get("TABLE_NAME", "lancedb-mcp-table")
EMBEDDING_FUNCTION = os.environ.get("EMBEDDING_FUNCTION", "sentence-transformers")
MODEL_NAME = os.environ.get("MODEL_NAME", "all-MiniLM-L6-v2")

model = get_registry().get(EMBEDDING_FUNCTION).create(name=MODEL_NAME)
mcp = FastMCP("lancedb")

class Schema(LanceModel):
    doc: str = model.SourceField()
    vector: Vector(model.ndims()) = model.VectorField()

@mcp.tool()
def ingest_docs(docs: Union[str, List[str]]):
    """
    Ingests a list of documents into a LanceDB table. It is critical that the metdata must be a string literal

    Args:
        docs (Union[str, List[str]]): A string or a list of strings to ingest.

    Returns:
        None
    
    example:
        ingest_docs(
            docs=["Hello world", "Hello world 2"],
        )
    """

    if isinstance(docs, str):
        docs = [docs]
    
    db = lancedb.connect(LANCEDB_URI)
    if TABLE_NAME in db.table_names():
        table = db.open_table(TABLE_NAME)
    else:
        table = db.create_table(TABLE_NAME, schema=Schema)

    table_data = [
        {
            "doc": doc,
        }
        for doc in docs
    ]
    table.add(table_data)

    return "Data added to lancedb successfully"

@mcp.tool()
def query_table(query: str,
                top_k: int = 5,
                query_type: str = "vector"): # TODO: add support for advanced query types
    """
    Query a LanceDB table with a query string and return the top k results.

    Args:

        query (str): The query string.
        top_k (int): The number of results to return. Defaults to 5.
        query_type (str): The type of query to perform. Defaults to "vector".

    Returns:

        List[Schema]: A list of Schema objects.
    """
    db = lancedb.connect(LANCEDB_URI)
    table = db.open_table(TABLE_NAME)
    results = table.search(query, query_type="vector") # TODO 
    results = results.limit(top_k).select(["doc"]).to_list()

    return results


@mcp.tool()
def table_details(
    table_name: Optional[str] = None,
    db_uri: Optional[str] = None,
):
    """
    Get the details of a LanceDB table.

    Args:

        table_name (str): The name of the table to get the details of. Defaults to "lancedb_table".
        db_uri (str): The URI of the LanceDB database. Defaults to "~/lancedb".

    Returns:
        dict: A dictionary of the table details.
    """
    db = lancedb.connect(LANCEDB_URI)
    table = db.open_table(TABLE_NAME)
    return {
        "name": table_name,
        "num_rows": len(table),
        "Schema": table.schema,
    }

if __name__ == "__main__":
    mcp.run()

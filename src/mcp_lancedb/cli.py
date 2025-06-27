"""CLI entry point for mcp-lancedb."""

import sys
import logging
import click
from .server import run

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Log to stderr to avoid interfering with stdio
)
logger = logging.getLogger("mcp_lancedb.cli")

@click.command()
def main():
    """Run the MCP LanceDB server using stdio."""
    try:
        logger.info("Starting MCP LanceDB server in stdio mode")
        run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 
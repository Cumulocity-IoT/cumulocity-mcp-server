"""
MCP Cumulocity Server - Cumulocity functionality for MCP
"""

import logging
import sys

import click

from .server import mcp

# Configure logging
logger = logging.getLogger(__name__)


# CLI Entry Point
@click.command()
@click.option("-v", "--verbose", count=True)
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=9000, help="Port to bind the server to")
def main(verbose: bool, host: str, port: int) -> None:
    """MCP Cumulocity Server - Cumulocity functionality for MCP"""
    # Configure logging based on verbosity
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        stream=sys.stderr,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting MCP Cumulocity Server")

    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()

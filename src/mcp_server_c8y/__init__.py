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
@click.option("--port", default=80, help="Port to bind the server to")
@click.option(
    "--transport",
    type=click.Choice(["sse", "streamable-http", "stdio"], case_sensitive=False),
    default="streamable-http",
    show_default=True,
    help="Transport to use: sse, streamable-http, or stdio",
)
def main(verbose: bool, host: str, port: int, transport: str) -> None:
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

    mcp._selected_transport = transport

    if transport == "stdio":
        mcp.run(transport=transport)
    else:
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()

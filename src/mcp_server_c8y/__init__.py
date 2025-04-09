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
def main(verbose: bool) -> None:
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

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

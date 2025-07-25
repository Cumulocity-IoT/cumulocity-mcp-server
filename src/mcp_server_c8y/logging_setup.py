"""
Logging setup for mcp-openapi-proxy.
"""

import logging
import os

# Initialize logger directly at module level
logger = logging.getLogger("mcp_server_c8y")


def setup_logging(verbose: int) -> logging.Logger:
    """Set up logging with the specified debug level."""

    # Configure logging based on verbosity
    logging_level = (
        logging.DEBUG
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
        else logging.WARN
    )
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    )

    logger.debug("Logging configured")
    return logger

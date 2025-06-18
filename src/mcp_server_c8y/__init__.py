"""
MCP Cumulocity Server - Cumulocity functionality for MCP
"""

import asyncio
import logging
import os
import sys

import click
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Mount, Route

from . import settings
from .logging_setup import setup_logging
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
    type=click.Choice(
        ["sse", "streamable-http", "hybrid", "stdio"], case_sensitive=False
    ),
    default="streamable-http",
    show_default=True,
    help="Transport to use: sse, streamable-http, hybrid, or stdio",
)
@click.option(
    "--root-path",
    default="",
    help="Root path to mount the application (for reverse proxies)",
)
def main(verbose: int, host: str, port: int, transport: str, root_path: str) -> None:
    """MCP Cumulocity Server - Cumulocity functionality for MCP"""

    logger = setup_logging(verbose)
    logger.info("Starting MCP Cumulocity Server")

    settings.init()
    settings.selected_transport = transport

    if transport == "stdio":
        asyncio.run(mcp.run_async(transport=transport))
    else:

        def health(request):
            return JSONResponse({"status": "up"})

        routes: list[BaseRoute] = [Route("/health", health)]
        lifespan = None
        if transport == "sse":
            appSSE = mcp.sse_app(path="/")
            routes.insert(0, Mount("/sse", app=appSSE))
            lifespan = appSSE.lifespan
        elif transport == "streamable-http":
            appHttp = mcp.streamable_http_app(path="/")
            routes.insert(0, Mount("/mcp", app=appHttp))
            lifespan = appHttp.lifespan
        elif transport == "hybrid":
            appHttp = mcp.streamable_http_app(path="/")
            appSSE = mcp.sse_app(path="/")
            routes.insert(0, Mount("/mcp", app=appHttp))
            routes.insert(1, Mount("/sse", app=appSSE))
            lifespan = appHttp.lifespan

        app = Starlette(
            routes=routes,
            lifespan=lifespan,
        )

        uvicorn.run(app, host=host, port=port, root_path=root_path)


if __name__ == "__main__":
    main()

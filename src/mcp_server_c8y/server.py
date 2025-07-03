"""
Server initialization and configuration for MCP Cumulocity Server.
"""

import json
from typing import Annotated

import jsonata
from dotenv import load_dotenv
from fastmcp import FastMCP

from pydantic import Field



from .logging_setup import logger

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("C8Y MCP Server")

@mcp.tool()
async def evaluate_jsonata_expression(
        source_json: Annotated[
            str,
            Field(
                description="JSON string to be used as source for the JSONata expression evaluation"
            ),
        ] = None,
        expression: Annotated[
            str,
            Field(
                description="JSONata expression to be evaluated against the source JSON"
            ),
        ] = None
) -> str:
    """Test a JSONata expression against a JSON string."""
    #Check if sourceJSON is valid JSON
    data = json.loads(source_json)
    #Evaluate the JSONata expression
    expr = jsonata.Jsonata(expression)
    result = expr.evaluate(data)
    return result

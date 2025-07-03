"""
Utility functions for mcp-openapi-proxy.
"""

import json
import os
import re
from typing import Dict, Optional, Tuple

import requests
import yaml
from mcp import types

from . import settings

# Import the configured logger
from .logging_setup import logger


def setup_logging(debug: bool = False):
    """
    Configure logging for the application.
    """
    from .logging_setup import setup_logging as ls

    return ls(debug)

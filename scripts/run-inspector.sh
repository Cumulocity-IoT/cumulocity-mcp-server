#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run the inspector with environment variables from .env
npx @modelcontextprotocol/inspector uv run mcp-server-c8y $("$SCRIPT_DIR/env_to_args.sh" "$PROJECT_ROOT/.env") -v
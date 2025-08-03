# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mcp-server-c8y** is a Python-based MCP (Model Control Protocol) server that provides Cumulocity IoT platform functionality. It enables interaction with Cumulocity's device management, measurements, alarms, and dynamic mapping capabilities through a standardized MCP interface.

## Architecture

### Core Components

- **`src/mcp_server_c8y/server.py`**: Main FastMCP server implementation with all tool definitions
- **`src/mcp_server_c8y/formatters.py`**: Data formatting utilities for devices, measurements, alarms, and events
- **`src/mcp_server_c8y/settings.py`**: Configuration management and environment variable handling
- **`src/mcp_server_c8y/logging_setup.py`**: Logging configuration
- **`src/mcp_server_c8y/__init__.py`**: CLI entry point and server startup logic

### Key Dependencies

- **FastMCP**: MCP server framework
- **c8y-api**: Cumulocity IoT Python SDK
- **httpx**: HTTP client for API calls
- **jsonata-python**: JSONata expression evaluation
- **pydantic**: Data validation and serialization

### Authentication & Configuration

The server requires these environment variables:
- `C8Y_BASEURL`: Cumulocity instance URL
- `C8Y_TENANT`: Tenant ID
- `C8Y_USER`: Username (optional if using Authorization header)
- `C8Y_PASSWORD`: Password (optional if using Authorization header)

Can also authenticate via HTTP Authorization header for microservice deployment.

## Common Development Commands

### Development Setup
```bash
# Install dependencies using uv (recommended)
uv sync

# Run the server locally with stdio transport
uv run mcp-server-c8y --transport stdio

# Run with verbose logging
uv run mcp-server-c8y --transport stdio -v

# Run the MCP inspector for development/debugging
./scripts/run-inspector.sh
```

### Version Management
```bash
# Increment patch version (e.g., 0.1.21 -> 0.1.22)
./scripts/increment-version.sh
```

### Building & Deployment
```bash
# Build Docker container and create deployment package
# Automatically syncs version from pyproject.toml to cumulocity.json
./scripts/buildcontainer.sh

# This creates docker/mcp-server-c8y.zip for Cumulocity microservice deployment
```

### Project Management
```bash
# Update dependencies
uv lock

# Run the server as Python module
python -m mcp_server_c8y

# Alternative entry point
python __main__.py
```

## Release Workflow

1. **Increment Version**: Use `./scripts/increment-version.sh` to bump patch version
2. **Build Package**: Run `./scripts/buildcontainer.sh` (automatically syncs versions)
3. **Commit Changes**: Commit the version bump and any other changes
4. **Deploy**: Upload the generated `docker/mcp-server-c8y.zip` to Cumulocity

## Development Notes

### Adding New Tools
All MCP tools are defined in `server.py` using FastMCP decorators. Each tool includes:
- Pydantic models for parameter validation
- Cumulocity API integration via `c8y-api` package
- Data formatting via formatter classes
- Error handling and logging

### Testing the Server
Use the MCP inspector to test tools during development:
```bash
./scripts/run-inspector.sh
```

This automatically loads environment variables and starts the inspector.

### Deployment Targets
1. **Local/Desktop**: Direct execution with stdio transport for Claude Desktop
2. **Cumulocity Microservice**: Docker-based deployment using `buildcontainer.sh`
3. **HTTP Server**: Standalone server with SSE/HTTP transports

### Code Style
- Uses modern Python features (3.10+)
- Pydantic for data validation
- Type hints throughout
- Structured logging
- Environment-based configuration
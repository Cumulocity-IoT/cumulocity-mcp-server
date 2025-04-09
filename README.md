# MCP Cumulocity Server

A Python-based server that provides Cumulocity IoT platform functionality through the MCP (Model Control Protocol) interface. This server enables seamless interaction with Cumulocity's device management, measurements, and alarm systems.

## Overview

- Device Management
  - List and filter devices
  - Get detailed device information
  - View device hierarchies (child devices)
  - Access device fragments and attributes
- Measurements
  - Retrieve device measurements with time-based filtering
  - View measurement history
- Alarms
  - Monitor active alarms
  - Filter alarms by severity
  - Track alarm status

## Prerequisites

- Python 3.13 or higher
- Access to a Cumulocity IoT platform instance
- Required environment variables configured

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-c8y
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install uv (if not already installed):
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

4. Install dependencies using uv:
```bash
uv pip install -e .
```

For development, install additional development dependencies:
```bash
uv pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
C8Y_BASE_URL=<your-cumulocity-base-url>
C8Y_TENANT_ID=<your-tenant-id>
C8Y_USERNAME=<your-username>
C8Y_PASSWORD=<your-password>
```


## Using with Claude Desktop

This MCP Server can be used with Claude Desktop to enable Claude to interact with your Cumulocity IoT platform. Follow these steps to set it up:

1. Download and install [Claude Desktop](https://modelcontextprotocol.io/quickstart/user#1-download-claude-for-desktop)

2. Configure Claude Desktop to use this MCP Server:
   - Open Claude Desktop
   - Click on the Claude menu and select "Settings..."
   - Navigate to "Developer" in the left-hand bar
   - Click "Edit Config"

3. Add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-c8y": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/mcp-c8y",
        "run",
        "mcp-c8y"
      ],
      "env": {
        "C8Y_BASE_URL": "https://your-cumulocity-instance.com",
        "C8Y_TENANT_ID": "your-tenant-id",
        "C8Y_USERNAME": "your-username",
        "C8Y_PASSWORD": "your-password"
      }
    }
  }
}
```

Replace the following placeholders with your actual values:
- `/path/to/uv`: Path to your uv executable
- `/path/to/mcp-c8y`: Path to your mcp-c8y project directory
- `https://your-cumulocity-instance.com`: Your Cumulocity instance URL
- `your-tenant-id`: Your Cumulocity tenant ID
- `your-username`: Your Cumulocity username
- `your-password`: Your Cumulocity password

4. Restart Claude Desktop

5. You should now see a hammer icon in the bottom right corner of the input box. Click it to see the available Cumulocity tools.

For more detailed information about using MCP Servers with Claude Desktop, visit the [official MCP documentation](https://modelcontextprotocol.io/quickstart/user).

### Options

- `--session, -s`: Specify a Cumulocity session
- `-v, --verbose`: Increase verbosity (can be used multiple times)

## Available Tools

### Device Management

1. **Get Devices**
   - List and filter devices
   - Parameters:
     - `type`: Filter by device type
     - `name`: Filter by device name
     - `page_size`: Results per page (max 2000)
     - `current_page`: Page number

2. **Get Device by ID**
   - Retrieve detailed information for a specific device
   - Parameter:
     - `device_id`: Device identifier

3. **Get Child Devices**
   - View child devices of a specific device
   - Parameter:
     - `device_id`: Parent device identifier

4. **Get Device Fragments**
   - Access device fragments and their values
   - Parameter:
     - `device_id`: Device identifier

### Measurements

**Get Device Measurements**
- Retrieve device measurements with time filtering
- Parameters:
  - `device_id`: Device identifier
  - `date_from`: Start date (ISO 8601 format)
  - `date_to`: End date (ISO 8601 format)
  - `page_size`: Number of measurements to retrieve

### Alarms

**Get Active Alarms**
- Monitor active alarms in the system
- Parameters:
  - `severity`: Filter by severity level
  - `page_size`: Number of results to retrieve

## Contributing

We welcome contributions from everyone! Here's how you can contribute to this project:

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Make your changes following these best practices:
   - Write clear, descriptive commit messages
   - Follow the existing code style and conventions
   - Add tests for new features
   - Update documentation as needed
   - Ensure all tests pass
4. Submit a pull request
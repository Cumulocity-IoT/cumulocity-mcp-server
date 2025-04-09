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
    "cumulocity": {
      "command": "mcp-server-c8y",
      "args": []
    }
  }
}
```

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


## License

This project is licensed under the Apache License 2.0 - see below for details:

```
Copyright 2024 MCP Cumulocity Server Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

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

### Development Guidelines

- Use meaningful variable and function names
- Add comments for complex logic
- Write unit tests for new functionality
- Keep commits focused and atomic
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values

### Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the documentation if you're changing functionality
3. The PR will be merged once you have the sign-off of at least one maintainer

For more detailed contribution guidelines, please refer to our [Contributing Guide](CONTRIBUTING.md).

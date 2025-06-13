# Cumulocity MCP Server

A Python-based server that provides Cumulocity IoT platform functionality through the MCP (Model Control Protocol) interface. This server enables seamless interaction with Cumulocity's device management, measurements, and alarm systems.


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

## Installation & Deployment

### Local Installation

#### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed for this package. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-c8y*.

#### Using PIP

Alternatively you can install `mcp-server-c8y` via pip:

```bash
pip install mcp-server-c8y
```

After installation, you can run it as a script using:

```bash
python -m mcp_server_c8y
```

### Deployment on Cumulocity Tenant

You can deploy this server as a Cumulocity microservice for direct integration with your tenant. This is done by uploading a special deployment package (`mcp-server-c8y.zip`) to your Cumulocity tenant.

#### Building the Microservice Deployment Package

1. Ensure you have Docker and zip installed on your system.
2. Run the provided build script to create the deployment package:

```bash
./scripts/buildcontainer.sh
```

This will:
- Build the Docker image for the microservice
- Save the image as `image.tar` in the `docker/` directory
- Package `image.tar` and `cumulocity.json` into `docker/mcp-server-c8y.zip`

#### Deploying to Cumulocity

1. Log in to your Cumulocity tenant as a user with microservice deployment permissions.
2. Navigate to **Administration > Ecosystem > Microservices**.
3. Click **Add microservice** and upload the `mcp-server-c8y.zip` file from the `docker/` directory.
4. Wait for the microservice to be deployed and started. You should see its status as "Available" once ready.
5. The microservice will be accessible under your tenant's service URL, typically:
   `https://<your-tenant>.cumulocity.com/service/mcp-server-c8y/mcp/`

For more details on Cumulocity microservice deployment, see the [official documentation](https://cumulocity.com/guides/microservice-sdk/concept/).

### Usage with Claude Desktop

This MCP Server can be used with Claude Desktop to enable Claude to interact with your Cumulocity IoT platform. Follow these steps to set it up:

1. Download and install [Claude Desktop](https://modelcontextprotocol.io/quickstart/user#1-download-claude-for-desktop)

2. Configure Claude Desktop to use this MCP Server:
   - Open Claude Desktop
   - Click on the Claude menu and select "Settings..."
   - Navigate to "Developer" in the left-hand bar
   - Click "Edit Config"

3. Add the following configuration to your `claude_desktop_config.json`:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "mcp-c8y": {
    "command": "uvx",
    "args": [
      "mcp-server-c8y",
      "--transport",
      "stdio"
    ],
    "env": {
      "C8Y_BASEURL": "https://your-cumulocity-instance.com",
      "C8Y_TENANT": "your-tenant-id",
      "C8Y_USER": "<your-username>",
      "C8Y_PASSWORD": "<your-password>"
    }
  }
}
```
</details>



Replace the following placeholders with your actual values:
- `https://your-cumulocity-instance.com`: Your Cumulocity instance URL
- `your-tenant-id`: Your Cumulocity tenant ID
- `your-username`: Your Cumulocity username
- `your-password`: Your Cumulocity password

4. Restart Claude Desktop

5. You should now see a hammer icon in the bottom right corner of the input box. Click it to see the available Cumulocity tools.

For more detailed information about using MCP Servers with Claude Desktop, visit the [official MCP documentation](https://modelcontextprotocol.io/quickstart/user).


## Cursor MCP Server Settings Example

If you are using Cursor and have deployed your MCP Server to a Cumulocity tenant, you can configure your MCP server connection with a `.cursor/mcp.json` file. Example (with sensitive data anonymized):

```json
{
  "mcpServers": {
    "Cumulocity": {
      "url": "https://your-cumulocity-instance.com/service/mcp-server-c8y/mcp/",
      "headers": {
        "Authorization": "Basic <YOUR_BASE64_AUTH_TOKEN>"
      }
    }
  }
}
```
- `https://your-cumulocity-instance.com`: Your Cumulocity instance URL
- Replace `<YOUR_BASE64_AUTH_TOKEN>` with your actual Base64-encoded credentials. Never commit real credentials to version control.

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

"""
Server initialization and configuration for MCP Cumulocity Server.
"""

import base64
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from c8y_api import CumulocityApi
from c8y_api._auth import HTTPBearerAuth
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from requests.auth import AuthBase, HTTPBasicAuth
from starlette.requests import Request
from starlette.responses import JSONResponse

# Local imports
from .formatters import (
    AlarmFormatter,
    DeviceFormatter,
    MeasurementFormatter,
    TableFormatter,
)

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cumulocity configuration
C8Y_BASEURL = os.getenv("C8Y_BASEURL", "")
C8Y_TENANT = os.getenv("C8Y_TENANT", "")
C8Y_USER = os.getenv("C8Y_USER", "")
C8Y_PASSWORD = os.getenv("C8Y_PASSWORD", "")

# Validate required environment variables
if not all([C8Y_BASEURL, C8Y_TENANT]):
    raise ValueError(
        "Missing required environment variables. Please set C8Y_BASEURL, " "C8Y_TENANT."
    )

# Initialize Cumulocity API client
logger.info(f"Initializing Cumulocity API client with base URL: {C8Y_BASEURL}")

# Initialize MCP server
mcp = FastMCP("C8Y MCP Server")

# Initialize formatters
device_formatter = DeviceFormatter()
measurement_formatter = MeasurementFormatter(show_source=False)


def get_auth():
    # Get the HTTP request
    request: Request = get_http_request()
    authorization = request.headers.get("Authorization", "Not provided")

    if authorization.startswith("Basic "):
        encoded = authorization.split(" ")[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return HTTPBasicAuth(username, password)
    elif authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        return HTTPBearerAuth(token)
    # Add other auth types as needed
    return AuthBase()


def get_c8y():
    if mcp._selected_transport == "stdio":
        return CumulocityApi(
            base_url=C8Y_BASEURL,
            tenant_id=C8Y_TENANT,
            username=C8Y_USER,
            password=C8Y_PASSWORD,
        )

    return CumulocityApi(base_url=C8Y_BASEURL, tenant_id=C8Y_TENANT, auth=get_auth())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "up"})


@mcp.tool()
async def get_devices(
    type: str | None = None,
    name: str | None = None,
    page_size: int = 5,
    current_page: int = 1,
) -> str:
    """Get a filtered list of devices from Cumulocity.

    Args:
        type: Filter by device type
        name: Filter by device name
        page_size: Number of results per page (max 2000)
        current_page: Page number to retrieve

    Returns:
        TSV formatted string with the following columns:
        - Device ID: Unique identifier of the device
        - Device Name: Name of the device
        - Device Type: Type of the device
        - Device Owner: Owner of the device
        - Device Availability: Current availability status
        - Critical Alarms: Number of critical alarms
        - Major Alarms: Number of major alarms
        - Minor Alarms: Number of minor alarms
        - Warning Alarms: Number of warning alarms
    """
    c8y = get_c8y()

    devices = c8y.device_inventory.get_all(
        page_size=min(page_size, 2000),
        page_number=current_page,
        type=type,
        name=name,
    )
    if len(devices) == 0:
        return "No devices found"

    return device_formatter.devices_to_table(devices)


@mcp.tool()
async def get_child_devices(device_id: str, page_size: int = 10) -> str:
    """Get child devices of a specific device.

    Args:
        device_id: ID of the parent device
        page_size: Number of child devices to retrieve (default: 10, max: 2000)

    Returns:
        TSV formatted string with the following columns:
        - Device ID: Unique identifier of the device
        - Device Name: Name of the device
        - Device Type: Type of the device
        - Device Owner: Owner of the device
        - Device Availability: Current availability status
        - Critical Alarms: Number of critical alarms
        - Major Alarms: Number of major alarms
        - Minor Alarms: Number of minor alarms
        - Warning Alarms: Number of warning alarms
    """
    c8y = get_c8y()
    children = c8y.inventory.get_all(parent=device_id, page_size=min(page_size, 2000))
    if len(children) == 0:
        return "No child devices found"
    return device_formatter.devices_to_table(children)


@mcp.tool()
async def get_device_context(
    device_id: str,
    child_devices_limit: int = 10,
) -> str:
    """Get comprehensive context for a specific device.
    This includes device fragments, supported measurements, supported operations, and child devices.

    Args:
        device_id: ID of the device to retrieve context for
        child_devices_limit: Maximum number of child devices to include in the response (default: 10)

    Returns:
        Formatted string containing device context including:
        - Device fragments and their values
        - List of supported measurements
        - List of supported operations
        - Total number of child devices and details for up to the specified limit
    """
    try:
        c8y = get_c8y()
        device = c8y.inventory.get(device_id)
    except Exception as e:
        raise ValueError(f"Failed to retrieve device {device_id}: {str(e)}")

    # Initialize output sections
    output_sections = []

    output_sections.append(device_formatter.device_to_formatted_string(device))

    # 1. Agent Information
    if hasattr(device, "c8y_Agent") and device.c8y_Agent:
        agent_section = ["## Agent Information"]
        agent_info = device.c8y_Agent
        agent_section.append(f"**Name:** {agent_info.get('name', 'N/A')}")
        agent_section.append(f"**Version:** {agent_info.get('version', 'N/A')}")
        agent_section.append(f"**URL:** {agent_info.get('url', 'N/A')}")
        output_sections.append("\n".join(agent_section))

    # 2. Software List
    if (
        hasattr(device, "c8y_SoftwareList")
        and device.c8y_SoftwareList
        and len(device.c8y_SoftwareList) > 0
    ):
        software_section = ["## Software List"]
        software_list = device.c8y_SoftwareList
        software_section.append(
            f"Total installed software packages: {len(software_list)}"
        )
        software_section.append("\nShowing a sample of installed software:")

        # Use TableFormatter for software list
        headers = ["Name", "Version"]
        rows = []
        for software in software_list[:10]:
            rows.append([software.get("name", "N/A"), software.get("version", "N/A")])

        software_section.append(TableFormatter.print_table(headers, rows))
        software_section.append("")

        output_sections.append("\n".join(software_section))

    # 3. Supported Logs
    if (
        hasattr(device, "c8y_SupportedLogs")
        and device.c8y_SupportedLogs
        and len(device.c8y_SupportedLogs) > 0
    ):
        logs_section = ["## Supported Logs"]
        supported_logs = device.c8y_SupportedLogs
        for log in supported_logs:
            logs_section.append(f"- {log}")
        output_sections.append("\n".join(logs_section))

    # 4. Supported Configurations
    if (
        hasattr(device, "c8y_SupportedConfigurations")
        and device.c8y_SupportedConfigurations
        and len(device.c8y_SupportedConfigurations) > 0
    ):
        configs_section = ["## Supported Configurations"]
        supported_configs = device.c8y_SupportedConfigurations
        for config in supported_configs:
            configs_section.append(f"- {config}")
        output_sections.append("\n".join(configs_section))

    # 5. Supported Measurements
    try:
        supported_measurements = c8y.inventory.get_supported_measurements(device_id)
        if supported_measurements and len(supported_measurements) > 0:
            measurements_section = ["## Supported Measurements"]
            for measurement in supported_measurements:
                measurements_section.append(f"- {measurement}")
            output_sections.append("\n".join(measurements_section))
    except Exception as e:
        # Only log the error but don't include it in the output
        logger.error(f"Error retrieving supported measurements: {str(e)}")

    # 6. Supported Operations
    if (
        hasattr(device, "c8y_SupportedOperations")
        and device.c8y_SupportedOperations
        and len(device.c8y_SupportedOperations) > 0
    ):
        operations_section = ["## Supported Operations"]
        for operation in device.c8y_SupportedOperations:
            operations_section.append(f"- {operation}")
        output_sections.append("\n".join(operations_section))

    # 7. Child Devices
    try:
        children = c8y.inventory.get_all(
            parent=device_id, page_size=child_devices_limit
        )
        total_children = c8y.inventory.get_count(parent=device_id)

        if total_children > 0:
            children_section = ["## Child Devices"]
            children_section.append(f"Total child devices: {total_children}")

            children_section.append(
                "\nShowing up to {} child devices:".format(
                    min(child_devices_limit, total_children)
                )
            )
            children_section.append(device_formatter.devices_to_table(children))
            output_sections.append("\n".join(children_section))
    except Exception as e:
        # Only log the error but don't include it in the output
        logger.error(f"Error retrieving child devices: {str(e)}")

    # 8. Additional Device Fragments
    additional_fragments = {}
    if hasattr(device, "fragments") and device.fragments:
        for key, value in device.fragments.items():
            # Skip internal attributes that start with underscore and specific fragments
            if key not in [
                "c8y_Availability",
                "com_cumulocity_model_Agent",
                "c8y_ActiveAlarmsStatus",
                "c8y_IsDevice",
                "c8y_SupportedOperations",
                "c8y_Agent",
                "c8y_SoftwareList",
                "c8y_SupportedLogs",
                "c8y_SupportedConfigurations",
            ]:
                additional_fragments[key] = value

    if additional_fragments:
        fragments_section = ["## Additional Device Fragments"]
        for key, value in additional_fragments.items():
            fragments_section.append(f"{key}: {value}")
        output_sections.append("\n".join(fragments_section))

    # Return the combined sections or a message if no information is available
    return "\n\n".join(output_sections)


@mcp.tool()
async def get_device_measurements(
    device_id: str,
    date_from: str | None = datetime.today().strftime("%Y-%m-%dT00:00:00.000Z"),
    date_to: str | None = None,
    page_size: int = 10,
) -> str:
    """Get the latest measurements for a specific device.

    This tool helps LLMs understand what measurements are available and their current values.

    Args:
        device_id: ID of the device to retrieve measurements for
        date_from: Start date and time in ISO 8601 format with milliseconds and UTC timezone.
                  Format: YYYY-MM-DDThh:mm:ss.sssZ
                  Defaults to today's date. Examples: "2024-03-20T00:00:00.000Z", "2024-01-01T12:00:00.000Z"
        date_to: End date and time in ISO 8601 format with milliseconds and UTC timezone.
                Format: YYYY-MM-DDThh:mm:ss.sssZ
                Defaults to current time if not specified. Examples: "2024-03-21T23:59:59.999Z", "2024-12-31T00:00:00.000Z"
        page_size: Number of measurements to retrieve (default: 10, max: 2000)

    Returns:
        Formatted string containing measurement data in a table format
    """
    try:
        c8y = get_c8y()
        # Get measurements for the device
        measurements = c8y.measurements.get_all(
            source=device_id,
            page_size=min(page_size, 2000),  # Limit to specified page size, max 2000
            page_number=1,  # Only request first page
            revert=True,  # Get newest measurements first
            date_from=date_from,
            date_to=date_to,
        )

        if len(measurements) == 0:
            return "No measurements found"

        return measurement_formatter.measurements_to_table(measurements)

    except Exception as e:
        logger.error(
            f"Failed to retrieve measurements for device {device_id}: {str(e)}"
        )
        raise ValueError(f"Failed to retrieve measurements: {str(e)}")


@mcp.tool()
async def get_active_alarms(
    severity: str | None = None,
    page_size: int = 10,
) -> List[Dict[str, Any]]:
    """Get active alarms across the platform.

    This tool helps LLMs understand the current state of the platform and any issues.

    Args:
        severity: Filter by alarm severity ('CRITICAL', 'MAJOR', 'MINOR', 'WARNING')
        status: Filter by alarm status ('ACTIVE', 'ACKNOWLEDGED', 'CLEARED')
        page_size: Number of results to retrieve (default: 10, max: 2000)

    Returns:
        List of alarms including device id, last updated, severity, status, and description
    """
    c8y = get_c8y()
    alarms = c8y.alarms.get_all(
        page_size=min(page_size, 2000),
        page_number=1,
        severity=None,
        status="ACTIVE",
    )

    if len(alarms) == 0:
        return "No alarms found"

    # Format the alarms using the AlarmFormatter
    alarm_formatter = AlarmFormatter()
    formatted_alarms = alarm_formatter.alarms_to_table(alarms)

    return formatted_alarms

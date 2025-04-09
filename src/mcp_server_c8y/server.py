"""
Server initialization and configuration for MCP Cumulocity Server.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from c8y_api import CumulocityApi
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Local imports
from .formatters import AlarmFormatter, DeviceFormatter, MeasurementFormatter

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cumulocity configuration
C8Y_BASE_URL = os.getenv("C8Y_BASE_URL", "")
C8Y_TENANT_ID = os.getenv("C8Y_TENANT_ID", "")
C8Y_USERNAME = os.getenv("C8Y_USERNAME", "")
C8Y_PASSWORD = os.getenv("C8Y_PASSWORD", "")

# Validate required environment variables
if not all([C8Y_BASE_URL, C8Y_TENANT_ID, C8Y_USERNAME, C8Y_PASSWORD]):
    raise ValueError(
        "Missing required environment variables. Please set C8Y_BASE_URL, "
        "C8Y_TENANT_ID, C8Y_USERNAME, and C8Y_PASSWORD."
    )

# Initialize Cumulocity API client
logger.info(f"Initializing Cumulocity API client with base URL: {C8Y_BASE_URL}")
c8y: CumulocityApi = CumulocityApi(
    base_url=C8Y_BASE_URL,
    tenant_id=C8Y_TENANT_ID,
    username=C8Y_USERNAME,
    password=C8Y_PASSWORD,
)

# Initialize MCP server
mcp: FastMCP = FastMCP("C8Y MCP Server")

# Initialize formatters
device_formatter = DeviceFormatter()
measurement_formatter = MeasurementFormatter(show_source=False)


@mcp.tool()
def get_devices(
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
def get_device_by_id(device_id: str) -> str:
    """Get a specific device by ID.

    Args:
        device_id: ID of the device to retrieve

    Returns:
        Formatted string containing device data in key-value format
    """
    device = c8y.inventory.get(device_id)
    return device_formatter.device_to_formatted_string(device)


@mcp.tool()
def get_child_devices(device_id: str) -> str:
    """Get child devices of a specific device.

    Args:
        device_id: ID of the parent device

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
    children = c8y.inventory.get_children(device_id)
    if len(children) == 0:
        return "No child devices found"
    return device_formatter.devices_to_table(children)


@mcp.tool()
def get_device_fragments(
    device_id: str,
) -> str:
    """Get fragments and their values for a specific device.
    Fragments are Cumulocity's way of organizing device data into logical groups.

    Args:
        device_id: ID of the device to retrieve attributes for

    Returns:
        All device fragments and their values in the format:
        <FRAGMENT KEY>: <Fragment Value>
    """
    try:
        device = c8y.inventory.get(device_id)
    except Exception as e:
        raise ValueError(f"Failed to retrieve device {device_id}: {str(e)}")

    if len(device.fragments) == 0:
        return "No fragments found"

    # Build formatted string with fragments
    formatted_output = []
    for key, value in device.fragments.items():
        # Skip internal attributes that start with underscore and specific fragments
        if key not in [
            "c8y_Availability",
            "com_cumulocity_model_Agent",
            "c8y_ActiveAlarmsStatus",
            "c8y_IsDevice",
        ]:
            formatted_output.append(f"{key}: {value}")

    return "\n".join(formatted_output)


@mcp.tool()
def get_device_measurements(
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
def get_active_alarms(
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

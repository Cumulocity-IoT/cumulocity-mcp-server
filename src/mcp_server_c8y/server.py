"""
Server initialization and configuration for MCP Cumulocity Server.
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import Annotated, Optional

import requests
from c8y_api import CumulocityApi
from c8y_api._auth import HTTPBearerAuth
from c8y_api.model import Device
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from jsonata import jsonata
from pydantic import Field
from requests.auth import HTTPBasicAuth
from starlette.exceptions import HTTPException

from . import settings

# Local imports
from .formatters import (
    AlarmFormatter,
    DeviceFormatter,
    EventFormatter,
    MeasurementFormatter,
    TableFormatter,
)

logger = logging.getLogger("mcp_server_c8y")

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
        "Missing required environment variables. Please set C8Y_BASEURL, C8Y_TENANT."
    )

# Initialize MCP server
mcp = FastMCP("C8Y MCP Server")
c8y = None

# Initialize formatters
device_formatter = DeviceFormatter()
measurement_formatter = MeasurementFormatter(show_source=False)
event_formatter = EventFormatter()


def get_auth():
    # Get the HTTP request
    headers = get_http_headers()
    authorization = headers.get("authorization")

    if not authorization:
        if settings.selected_transport == "stdio":
            return HTTPBasicAuth(f"{C8Y_TENANT}/{C8Y_USER}", C8Y_PASSWORD)
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    if authorization.startswith("Basic "):
        try:
            encoded = authorization.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
            return HTTPBasicAuth(username, password)
        except Exception:
            raise HTTPException(
                status_code=401, detail="Invalid Basic authentication credentials."
            )
    elif authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            return HTTPBearerAuth(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Bearer token.")
    # Add other auth types as needed
    raise HTTPException(
        status_code=401, detail="Unsupported or missing authentication method."
    )


def get_c8y():
    global c8y
    if c8y is not None:
        return c8y

    # Initialize Cumulocity API client
    logger.info(f"Initializing Cumulocity API client with base URL: {C8Y_BASEURL}")

    c8y = CumulocityApi(base_url=C8Y_BASEURL, tenant_id=C8Y_TENANT, auth=get_auth())
    return c8y


def get_asset_with_parents(asset_id):
    # Get authentication from the existing get_auth function
    auth = get_auth()

    # Get the C8Y API instance
    c8y = get_c8y()

    # Construct the URL
    url = f"{c8y.base_url}/inventory/managedObjects/{asset_id}"

    # Add the withParents parameter
    params = {"withParents": "true"}

    # Make the HTTP request
    response = requests.get(
        url=url, params=params, auth=auth, headers={"Accept": "application/json"}
    )

    # Check if the request was successful
    response.raise_for_status()

    assetWithParents = response.json()
    asset = Device.from_json(assetWithParents)

    try:
        parent_assets = assetWithParents["assetParents"]["references"]
        parent_asset_ids = [asset["managedObject"]["id"] for asset in parent_assets]
        logger.info(
            f"Retrieved {len(parent_asset_ids)} parent assets from asset {asset_id}"
        )
        if len(parent_asset_ids) > 0:
            asset.parent_assets = c8y.inventory.get_all(
                ids=parent_asset_ids,
                with_children=False,
                page_size=len(parent_asset_ids),
            )
    except Exception as e:
        logger.info(f"Could not retrieve parent assets from asset {asset_id}: {str(e)}")

    try:
        parent_devices = assetWithParents["deviceParents"]["references"]
        parent_devices_ids = [asset["managedObject"]["id"] for asset in parent_devices]
        logger.info(
            f"Retrieved {len(parent_devices_ids)} parent assets from asset {asset_id}"
        )
        if len(parent_devices_ids) > 0:
            asset.parent_devices = c8y.inventory.get_all(
                ids=parent_devices_ids,
                with_children=False,
                page_size=len(parent_asset_ids),
            )
    except Exception as e:
        logger.info(
            f"Could not retrieve parent devices from asset {asset_id}: {str(e)}"
        )

    # Return the C8Y Device
    return asset


@mcp.tool()
async def get_assets(
    typeFilter: Annotated[
        Optional[str] | None,
        Field(
            description="If provided, only assets including devices of this type will be returned."
        ),
    ] = None,
    nameFilter: Annotated[
        Optional[str] | None,
        Field(description="Filter assets including devices by name."),
    ] = None,
    page_size: int = 20,
    current_page: int = 1,
) -> str:
    """Get a filtered list of assets including devices from Cumulocity."""
    c8y = get_c8y()
    devices = None

    if typeFilter is not None and nameFilter is not None:
        devices = c8y.device_inventory.get_all(
            page_size=min(page_size, 2000),
            page_number=current_page,
            type=typeFilter,
            text=nameFilter,
        )
    elif typeFilter is not None:
        devices = c8y.device_inventory.get_all(
            page_size=min(page_size, 2000),
            page_number=current_page,
            type=typeFilter,
        )
    elif nameFilter is not None:
        devices = c8y.device_inventory.get_all(
            page_size=min(page_size, 2000),
            page_number=current_page,
            text=nameFilter,
        )
    else:
        devices = c8y.device_inventory.get_all(
            page_size=min(page_size, 2000),
            page_number=current_page,
        )

    if len(devices) == 0:
        return "No assets found"
    return device_formatter.devices_to_table(devices)


@mcp.tool()
async def get_child_devices(parent_device_id: str, page_size: int = 20) -> str:
    """Get child devices of a specific device."""
    c8y = get_c8y()
    children = c8y.inventory.get_all(
        parent=parent_device_id, page_size=min(page_size, 2000)
    )
    if len(children) == 0:
        return "No child devices found"
    return device_formatter.devices_to_table(children)


@mcp.tool()
async def get_device_context(
    device_id: str,
    child_devices_limit: int = 20,
) -> str:
    """Get comprehensive context for a specific device.
    This includes device fragments, supported measurements, supported operations, and child devices.
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
    if hasattr(device, "c8y_Agent") and isinstance(device.c8y_Agent, dict):
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
        raise ValueError(f"Error retrieving supported measurements: {str(e)}")

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
        raise ValueError(f"Error retrieving child devices: {str(e)}")

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
    date_from: Annotated[
        str,
        Field(
            description="Defaults to Today and needs to be provide in ISO 8601 format with milliseconds and UTC timezone: YYYY-MM-DDThh:mm:ss.sssZ"
        ),
    ] = datetime.today().strftime("%Y-%m-%dT00:00:00.000Z"),
    date_to: Annotated[
        str,
        Field(
            description="Needs to be provide in ISO 8601 format with milliseconds and UTC timezone: YYYY-MM-DDThh:mm:ss.sssZ"
        ),
    ] = "",
    page_size: int = 10,
    current_page: int = 1,
) -> str:
    """Get the latest measurements for a specific device.

    This tool helps LLMs understand what measurements are available and their current values.
    """
    try:
        c8y = get_c8y()
        # Get measurements for the device
        measurements = c8y.measurements.get_all(
            source=device_id,
            page_size=min(page_size, 2000),  # Limit to specified page size, max 2000
            page_number=current_page,  # Use the provided page number
            revert=True,  # Get newest measurements first
            date_from=date_from,
            date_to=date_to,
        )

        if len(measurements) == 0:
            return "No measurements found"

        return measurement_formatter.measurements_to_table(measurements)

    except Exception as e:
        raise ValueError(
            f"Failed to retrieve measurements for device {device_id}: {str(e)}"
        )


@mcp.tool()
async def get_alarms(
    severity: Annotated[
        str,
        Field(
            description="Filter by alarm severity ('CRITICAL', 'MAJOR', 'MINOR', 'WARNING')"
        ),
    ] = "",
    status: Annotated[
        str,
        Field(
            description="Filter by alarm status ('ACTIVE', 'ACKNOWLEDGED', 'CLEARED')"
        ),
    ] = "ACTIVE",
    page_size: int = 10,
    device_id: Annotated[
        Optional[str],
        Field(
            description="If provided, only alarms for this device will be retrieved."
        ),
    ] = None,
    include_children: Annotated[
        bool,
        Field(
            description="If set and device_id is provided, include alarms for child assets and devices."
        ),
    ] = False,
    alarm_type: Annotated[
        Optional[str],
        Field(description="If provided, only alarms of this type will be retrieved."),
    ] = None,
) -> str:
    """Get alarms across the platform or for a specific device (optionally including children)."""
    c8y = get_c8y()
    get_all_kwargs = {
        "page_size": min(page_size, 2000),
        "page_number": 1,
        "severity": severity,
        "status": status,
    }
    if device_id:
        get_all_kwargs["source"] = device_id
        if include_children:
            get_all_kwargs["with_source_assets"] = True
            get_all_kwargs["with_source_devices"] = True
    if alarm_type:
        get_all_kwargs["type"] = alarm_type
    alarms = c8y.alarms.get_all(**get_all_kwargs)

    if len(alarms) == 0:
        return "No alarms found"

    # Format the alarms using the AlarmFormatter
    alarm_formatter = AlarmFormatter()
    formatted_alarms = alarm_formatter.alarms_to_table(alarms)

    return formatted_alarms


@mcp.tool()
async def get_events(
    device_id: Annotated[
        str,
        Field(description="Device ID for which to retrieve events. This is required."),
    ],
    include_children: Annotated[
        bool,
        Field(description="If set, include events for child assets and devices."),
    ] = False,
    event_type: Annotated[
        Optional[str],
        Field(description="If provided, only events of this type will be retrieved."),
    ] = None,
    page_size: int = 10,
    current_page: int = 1,
    date_from: Annotated[
        str,
        Field(
            description="Defaults to Today and needs to be provided in ISO 8601 format with milliseconds and UTC timezone: YYYY-MM-DDThh:mm:ss.sssZ"
        ),
    ] = datetime.today().strftime("%Y-%m-%dT00:00:00.000Z"),
    date_to: Annotated[
        str,
        Field(
            description="Needs to be provided in ISO 8601 format with milliseconds and UTC timezone: YYYY-MM-DDThh:mm:ss.sssZ"
        ),
    ] = "",
) -> str:
    """Get events for a specific device (optionally including children). Platform-wide queries are not allowed."""
    c8y = get_c8y()
    get_all_kwargs = {
        "source": device_id,
        "page_size": min(page_size, 2000),
        "page_number": current_page,
        "date_from": date_from,
        "date_to": date_to,
    }
    if include_children:
        get_all_kwargs["with_source_assets"] = True
        get_all_kwargs["with_source_devices"] = True
    if event_type:
        get_all_kwargs["type"] = event_type

    events = c8y.events.get_all(**get_all_kwargs)

    if len(events) == 0:
        return "No events found"

    return event_formatter.events_to_table(events)


@mcp.tool()
async def get_asset_hierarchy(
    asset_id: Annotated[
        str,
        Field(description="Asset ID for which to retrieve the asset hierarchy."),
    ],
) -> str:
    """Get the complete asset hierarchy for a specific asset or device by retrieving all parent managed objects.

    This uses the 'withParents' option to fetch the complete hierarchy chain above the specified asset or device.
    """
    columns = ["Device ID", "Device Name", "Device Type", "Device Owner"]
    try:
        # Get parent objects using the withParents option
        assetWithParents = get_asset_with_parents(asset_id)

        # Format the hierarchy
        hierarchy_section = ["# Asset Hierarchy"]
        if len(assetWithParents.parent_assets) > 0:
            hierarchy_section.append(
                f"Parent assets for '{assetWithParents.name}' ({asset_id}):"
            )
            hierarchy_section.append(
                device_formatter.devices_to_table(
                    assetWithParents.parent_assets, columns=columns
                )
            )
            hierarchy_section.append("")

        if len(assetWithParents.parent_devices) > 0:
            hierarchy_section.append(
                f"Parent devices for '{assetWithParents.name}' ({asset_id}):"
            )
            hierarchy_section.append(
                device_formatter.devices_to_table(
                    assetWithParents.parent_devices, columns=columns
                )
            )
            hierarchy_section.append("")

        if len(assetWithParents.child_assets) > 0:
            hierarchy_section.append(
                f"Child assets for '{assetWithParents.name}' ({asset_id}):"
            )
            hierarchy_section.append(
                device_formatter.devices_to_table(
                    assetWithParents.child_assets, columns=columns
                )
            )
            hierarchy_section.append("")

        columns = ["Device ID", "Device Name"]
        if len(assetWithParents.child_devices) > 0:
            hierarchy_section.append(
                f"Child devices for '{assetWithParents.name}' ({asset_id}):"
            )
            hierarchy_section.append(
                device_formatter.devices_to_table(
                    assetWithParents.child_devices, columns=columns
                )
            )
            hierarchy_section.append("")

        return "\n".join(hierarchy_section)

    except Exception as e:
        raise ValueError(
            f"Failed to retrieve asset hierarchy for asset {asset_id}: {str(e)}"
        )


@mcp.tool()
async def evaluate_jsonata_expression(
    source_json: Annotated[
        str,
        Field(
            description="JSON string to be used as source for the JSONata expression evaluation"
        ),
    ],
    expression: Annotated[
        str,
        Field(description="JSONata expression to be evaluated against the source JSON"),
    ],
) -> str:
    """Test a JSONata expression against a JSON string."""
    # Check if sourceJSON is valid JSON
    data = json.loads(source_json)
    # Evaluate the JSONata expression
    expr = jsonata.Jsonata(expression)
    result = expr.evaluate(data)
    return str(result) if result is not None else ""

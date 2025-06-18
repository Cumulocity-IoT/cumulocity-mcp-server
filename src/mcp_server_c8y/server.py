"""
Server initialization and configuration for MCP Cumulocity Server.
"""

import base64
import json
import os
from datetime import datetime
from typing import Annotated, Dict, Optional

import requests
from c8y_api import CumulocityApi
from c8y_api._auth import HTTPBearerAuth
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field
from requests.auth import HTTPBasicAuth
from starlette.exceptions import HTTPException

from . import settings

# Local imports
from .formatters import (
    AlarmFormatter,
    DeviceFormatter,
    MeasurementFormatter,
    TableFormatter,
)
from .logging_setup import logger
from .openapi import fetch_openapi_spec
from .utils import (
    get_additional_headers,
    is_tool_blacklisted,
    normalize_tool_name,
    strip_parameters,
)

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
spec = None  # Global spec for resources
c8y = None

# Initialize formatters
device_formatter = DeviceFormatter()
measurement_formatter = MeasurementFormatter(show_source=False)


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
    if c8y:
        return c8y

    # Initialize Cumulocity API client
    logger.info(f"Initializing Cumulocity API client with base URL: {C8Y_BASEURL}")

    c8y = CumulocityApi(base_url=C8Y_BASEURL, tenant_id=C8Y_TENANT, auth=get_auth())
    return c8y


@mcp.tool()
def list_functions() -> str:
    """Lists available functions derived from the OpenAPI specification."""
    logger.debug("Executing list_functions tool.")
    spec_url = os.environ.get("OPENAPI_SPEC_URL")
    logger.debug(f"Using spec_url: {spec_url}")
    if not spec_url:
        raise ValueError("No OPENAPI_SPEC_URL configured.")
    global spec
    spec = fetch_openapi_spec(spec_url)
    if isinstance(spec, str):
        spec = json.loads(spec)
    if spec is None:
        raise ValueError("Spec is None after fetch_openapi_spec")

    logger.debug(f"Raw spec loaded: {json.dumps(spec, indent=2, default=str)}")
    paths = spec.get("paths", {})
    logger.debug(f"Paths extracted from spec: {list(paths.keys())}")
    if not paths:
        logger.debug("No paths found in spec.")
        return json.dumps([])
    functions = {}
    for path, path_item in paths.items():
        logger.debug(f"Processing path: {path}")
        if not path_item:
            logger.debug(f"Path item is empty for {path}")
            continue
        blacklist_check = is_tool_blacklisted(path)
        logger.debug(f"Whitelist check for {path}: {blacklist_check}")
        if blacklist_check:
            logger.debug(f"Path {path} is in blacklist - skipping.")
            continue
        for method, operation in path_item.items():
            logger.debug(f"Found method: {method} for path: {path}")
            if not method:
                logger.debug(f"Method is empty for {path}")
                continue
            if method.lower() not in settings.methodWhitelist:
                logger.debug(f"Skipping method that is not whitelisted: {method}")
                continue
            raw_name = f"{method.upper()} {path}"
            function_name = normalize_tool_name(raw_name)
            if function_name in functions:
                logger.debug(f"Skipping duplicate function name: {function_name}")
                continue
            function_description = operation.get(
                "summary", operation.get("description", "No description provided.")
            )
            logger.debug(
                f"Registering function: {function_name} - {function_description}"
            )
            input_schema = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            }
            placeholder_params = [
                part.strip("{}")
                for part in path.split("/")
                if "{" in part and "}" in part
            ]
            for param_name in placeholder_params:
                input_schema["properties"][param_name] = {
                    "type": "string",
                    "description": f"Path parameter {param_name}",
                }
                input_schema["required"].append(param_name)
            for param in operation.get("parameters", []):
                param_name = param.get("name")
                param_type = param.get("type", "string")
                if param_type not in ["string", "integer", "boolean", "number"]:
                    param_type = "string"
                input_schema["properties"][param_name] = {
                    "type": param_type,
                    "description": param.get(
                        "description",
                        f"{param.get('in', 'unknown')} parameter {param_name}",
                    ),
                }
                if (
                    param.get("required", False)
                    and param_name not in input_schema["required"]
                ):
                    input_schema["required"].append(param_name)
            functions[function_name] = {
                "name": function_name,
                "description": function_description,
                "path": path,
                "method": method.upper(),
                "operationId": operation.get("operationId"),
                "original_name": raw_name,
                "inputSchema": input_schema,
            }

    logger.debug(
        f"Discovered {len(functions)} functions from the OpenAPI specification."
    )

    logger.debug(f"Functions list: {list(functions.values())}")
    return json.dumps(list(functions.values()), indent=2)


@mcp.tool()
def call_function(
    *,
    function_name: str,
    parameters: Optional[Dict] = None,
) -> str:
    """Calls a function derived from the OpenAPI specification."""
    logger.debug(
        f"call_function invoked with function_name='{function_name}' and parameters={parameters}"
    )
    if not function_name:
        raise ValueError("function_name is empty or None")
    spec_url = os.environ.get("OPENAPI_SPEC_URL")
    if not spec_url:
        raise ValueError("No OPENAPI_SPEC_URL configured.")
    global spec
    spec = fetch_openapi_spec(spec_url)
    if spec is None:
        raise ValueError("Failed to fetch or parse the OpenAPI specification")
    logger.debug(f"Spec keys for call_function: {list(spec.keys())}")
    function_def = None
    paths = spec.get("paths", {})
    logger.debug(f"Paths for function lookup: {list(paths.keys())}")

    for path, path_item in paths.items():
        logger.debug(f"Checking path: {path}")
        for method, operation in path_item.items():
            logger.debug(f"Checking method: {method} for path: {path}")
            if method.lower() not in settings.methodWhitelist:
                logger.debug(f"Skipping method that is not whitelisted: {method}")
                continue
            raw_name = f"{method.upper()} {path}"
            current_function_name = normalize_tool_name(raw_name)
            logger.debug(f"Comparing {current_function_name} with {function_name}")
            if current_function_name == function_name:
                function_def = {
                    "path": path,
                    "method": method.upper(),
                    "operation": operation,
                }
                logger.debug(
                    f"Matched function definition for '{function_name}': {function_def}"
                )
                break
        if function_def:
            break
    if not function_def:
        raise ValueError(
            f"Function '{function_name}' not found in the OpenAPI specification."
        )
    logger.debug(f"Function def found: {function_def}")

    operation = function_def["operation"]
    operation["method"] = function_def["method"]
    headers = get_additional_headers()
    if parameters is None:
        parameters = {}
    parameters = strip_parameters(parameters)
    logger.debug(f"Parameters after strip: {parameters}")
    if function_def["method"] != "GET":
        headers["Content-Type"] = "application/json"

    if is_tool_blacklisted(function_def["path"]):
        raise ValueError(f"Access to function '{function_name}' is not allowed.")

    base_url = C8Y_BASEURL
    if not base_url:
        raise ValueError("No C8Y_BASEURL provided.")

    path = function_def["path"]
    # Check required path params before substitution
    path_params_in_openapi = [
        param["name"]
        for param in operation.get("parameters", [])
        if param.get("in") == "path"
    ]
    if path_params_in_openapi:
        missing_required = [
            param["name"]
            for param in operation.get("parameters", [])
            if param.get("in") == "path"
            and param.get("required", False)
            and param["name"] not in parameters
        ]
        if missing_required:
            raise ValueError(f"Missing required path parameters: {missing_required}")

    if "{" in path and "}" in path:
        params_to_remove = []
        logger.debug(f"Before substitution - Path: {path}, Parameters: {parameters}")
        for param_name, param_value in parameters.items():
            if f"{{{param_name}}}" in path:
                path = path.replace(f"{{{param_name}}}", str(param_value))
                logger.debug(f"Substituted {param_name}={param_value} in path: {path}")
                params_to_remove.append(param_name)
        for param_name in params_to_remove:
            if param_name in parameters:
                del parameters[param_name]
        logger.debug(f"After substitution - Path: {path}, Parameters: {parameters}")

    api_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    request_params = {}
    request_body = None

    if isinstance(parameters, dict):
        if "stream" in parameters and parameters["stream"]:
            del parameters["stream"]
        if function_def["method"] == "GET":
            request_params = parameters
        else:
            request_body = parameters
    else:
        parameters = {}
        logger.debug("No valid parameters provided, proceeding without params/body")

    logger.debug(
        f"Sending request - Method: {function_def['method']}, URL: {api_url}, Headers: {headers}, Params: {request_params}, Body: {request_body}"
    )
    # Add SSL verification control for API calls using IGNORE_SSL_TOOLS
    ignore_ssl_tools = os.getenv("IGNORE_SSL_TOOLS", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    verify_ssl_tools = not ignore_ssl_tools
    logger.debug(
        f"Sending API request with SSL verification: {verify_ssl_tools} (IGNORE_SSL_TOOLS={ignore_ssl_tools})"
    )
    response = requests.request(
        method=function_def["method"],
        url=api_url,
        headers=headers,
        auth=get_auth(),
        params=request_params if function_def["method"] == "GET" else None,
        json=request_body if function_def["method"] != "GET" else None,
        verify=verify_ssl_tools,
    )
    response.raise_for_status()
    logger.debug(f"API response received: {response.text}")
    return response.text


@mcp.tool()
async def get_devices(
    typeFilter: Optional[str] | None = None,
    nameFilter: str | None = None,
    page_size: int = 5,
    current_page: int = 1,
) -> str:
    """Get a filtered list of devices from Cumulocity."""
    c8y = get_c8y()
    devices = c8y.device_inventory.get_all(
        page_size=min(page_size, 2000),
        page_number=current_page,
        type=typeFilter if typeFilter is not None else "",
        name=nameFilter if nameFilter is not None else "",
    )

    if len(devices) == 0:
        return "No devices found"
    return device_formatter.devices_to_table(devices)


@mcp.tool()
async def get_child_devices(parent_device_id: str, page_size: int = 10) -> str:
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
    child_devices_limit: int = 10,
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
            page_number=1,  # Only request first page
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
async def get_active_alarms(
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
) -> str:
    """Get active alarms across the platform."""
    c8y = get_c8y()
    alarms = c8y.alarms.get_all(
        page_size=min(page_size, 2000),
        page_number=1,
        severity=severity,
        status=status,
    )

    if len(alarms) == 0:
        return "No alarms found"

    # Format the alarms using the AlarmFormatter
    alarm_formatter = AlarmFormatter()
    formatted_alarms = alarm_formatter.alarms_to_table(alarms)

    return formatted_alarms

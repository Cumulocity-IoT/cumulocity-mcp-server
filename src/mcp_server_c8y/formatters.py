"""
Formatters for Cumulocity data types.
"""

import json
import unicodedata
from typing import Any, Dict, List

from c8y_api.model import Alarm, Device, ManagedObject, Measurement
from tabulate import tabulate


def clean_text(text):
    # Normalize Unicode characters
    normalized = unicodedata.normalize("NFKD", text)
    # Remove non-ASCII characters
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text


class DeviceFormatter:
    """Helper class for formatting device data in various table formats."""

    # Standard configuration matching the get_devices tool description
    DEFAULT_CONFIG = {
        "columns": [
            "Device ID",
            "Device Name",
            "Device Type",
            "Device Owner",
            "Device Availability",
            "Critical Alarms",
            "Major Alarms",
            "Minor Alarms",
            "Warning Alarms",
        ],
        "extractors": {
            "Device ID": lambda d: str(d.id),
            "Device Name": lambda d: (
                str(d.name) if hasattr(d, "name") and d.name is not None else "Unknown"
            ),
            "Device Type": lambda d: (
                str(d.type) if hasattr(d, "type") and d.type is not None else "Unknown"
            ),
            "Device Owner": lambda d: (
                str(d.owner)
                if hasattr(d, "owner") and d.owner is not None
                else "Unknown"
            ),
            "Device Availability": lambda d: (
                str(d.c8y_Availability.status)
                if hasattr(d, "c8y_Availability")
                and hasattr(d.c8y_Availability, "status")
                and d.c8y_Availability.status is not None
                else "Unknown"
            ),
            "Critical Alarms": lambda d: (
                str(d.c8y_ActiveAlarmsStatus.critical)
                if hasattr(d, "c8y_ActiveAlarmsStatus")
                and hasattr(d.c8y_ActiveAlarmsStatus, "critical")
                and d.c8y_ActiveAlarmsStatus.critical is not None
                else "0"
            ),
            "Major Alarms": lambda d: (
                str(d.c8y_ActiveAlarmsStatus.major)
                if hasattr(d, "c8y_ActiveAlarmsStatus")
                and hasattr(d.c8y_ActiveAlarmsStatus, "major")
                and d.c8y_ActiveAlarmsStatus.major is not None
                else "0"
            ),
            "Minor Alarms": lambda d: (
                str(d.c8y_ActiveAlarmsStatus.minor)
                if hasattr(d, "c8y_ActiveAlarmsStatus")
                and hasattr(d.c8y_ActiveAlarmsStatus, "minor")
                and d.c8y_ActiveAlarmsStatus.minor is not None
                else "0"
            ),
            "Warning Alarms": lambda d: (
                str(d.c8y_ActiveAlarmsStatus.warning)
                if hasattr(d, "c8y_ActiveAlarmsStatus")
                and hasattr(d.c8y_ActiveAlarmsStatus, "warning")
                and d.c8y_ActiveAlarmsStatus.warning is not None
                else "0"
            ),
        },
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize the formatter with optional configuration.

        Args:
            config: Optional configuration dictionary with 'columns' and 'extractors' keys.
                   If None, uses DEFAULT_CONFIG.
        """
        self.config = config or self.DEFAULT_CONFIG
        self.columns = self.config["columns"]
        self.extractors = self.config["extractors"]

    def device_to_row(self, device: Device | ManagedObject) -> List[str]:
        """Convert a Device object to a list of values.

        Args:
            device: Device object from Cumulocity API

        Returns:
            List of string values representing device data
        """
        return [extractor(device) for extractor in self.extractors.values()]

    def devices_to_table(
        self, devices: List[ManagedObject] | List[Device], tablefmt: str = "tsv"
    ) -> str:
        """Convert a list of Device objects to a formatted table.

        Args:
            devices: List of Device objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        rows = [self.device_to_row(device) for device in devices]
        return tabulate(rows, headers=self.columns, tablefmt=tablefmt)

    def device_to_formatted_string(self, device: Device | ManagedObject) -> str:
        """Convert a Device object to a formatted string with key-value pairs.

        Args:
            device: Device object from Cumulocity API

        Returns:
            Formatted string with key-value pairs, one per line
        """
        data = [
            [column, extractor(device)] for column, extractor in self.extractors.items()
        ]
        return tabulate(data, tablefmt="plain")


class MeasurementFormatter:
    """Helper class for formatting measurement data in various formats."""

    def __init__(self, show_source: bool = False):
        """Initialize the formatter with configuration.

        Args:
            show_source: Whether to include the source device ID in the output
        """
        self.show_source = show_source

    def _format_measurement_data(self, measurement: Measurement) -> str:
        """Format measurement data into a readable string.

        Args:
            measurement: Measurement object from Cumulocity API

        Returns:
            Formatted string with measurement data
        """
        formatted_lines = []
        for fragment_key, fragment_value in measurement.fragments.items():

            if isinstance(fragment_value, dict):
                for series_key, series_value in fragment_value.items():
                    if isinstance(series_value, dict):
                        value = series_value.get("value", "")
                        unit = series_value.get("unit", "")
                        formatted_lines.append(
                            f"{fragment_key}->{series_key}: {value} {unit}"
                        )
                    else:
                        formatted_lines.append(
                            f"{fragment_key}->{series_key}: {series_value}"
                        )
            else:
                formatted_lines.append(f"{fragment_key}: {fragment_value}")
        return "\n".join(formatted_lines)

    def measurement_to_formatted_string(self, measurement: Measurement) -> str:
        """Convert a measurement object to a formatted string.

        Args:
            measurement: Measurement object from Cumulocity API

        Returns:
            Formatted string with measurement information
        """
        lines = []

        # Add source ID if configured
        if (
            self.show_source
            and hasattr(measurement, "source")
            and measurement.source is not None
        ):
            lines.append(f"Source: {measurement.source.id}")

        # Add timestamp
        lines.append(f"Time: {measurement.time}")

        # Add measurement data
        lines.append("\nData:")
        lines.append(self._format_measurement_data(measurement))

        return "\n".join(lines)

    def measurements_to_table(
        self, measurements: List[Measurement], tablefmt: str = "tsv"
    ) -> str:
        """Convert a list of measurements to a formatted table.

        Args:
            measurements: List of Measurement objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        # Define columns based on configuration
        columns = ["Time"]
        if self.show_source:
            columns.append("Source")

        # Collect all unique fragment->series combinations
        fragment_series_columns = set()
        for measurement in measurements:
            for fragment_key, fragment_value in measurement.fragments.items():
                if isinstance(fragment_value, dict):
                    for series_key in fragment_value.keys():
                        fragment_series_columns.add((fragment_key, series_key))

        fragment_series_columns = sorted(fragment_series_columns)
        # Add fragment->series columns
        columns.extend([f"{x[0]}->{x[1]}" for x in fragment_series_columns])

        # Prepare rows
        rows = []
        for measurement in measurements:
            row = [measurement.time]
            if self.show_source:
                row.append(
                    measurement.source.id
                    if hasattr(measurement, "source") and measurement.source is not None
                    else ""
                )

            # Add values for each fragment->series column
            for fragment_key, series_key in fragment_series_columns:
                fragment_value = measurement.fragments.get(fragment_key, {})
                if isinstance(fragment_value, dict):
                    series_value = fragment_value.get(series_key, {})
                    if isinstance(series_value, dict):
                        value = series_value.get("value", "")
                        unit = series_value.get("unit", "")
                        row.append(f"{value} {unit}".strip())
                    else:
                        row.append(str(series_value))
                else:
                    row.append("")

            rows.append(row)

        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=columns, tablefmt=tablefmt)


class AlarmFormatter:
    """Helper class for formatting alarm data in various formats."""

    DEFAULT_CONFIG = {
        "columns": [
            "Alarm ID",
            "Device ID",
            "Type",
            "Severity",
            "Status",
            "Last Updated",
            "Count",
            "First Occurrence",
            "Text",
        ],
        "extractors": {
            "Alarm ID": lambda a: str(a.id),
            "Device ID": lambda a: str(a.source),
            "Type": lambda a: str(a.type),
            "Severity": lambda a: str(a.severity),
            "Status": lambda a: str(a.status),
            "Last Updated": lambda a: (
                str(a.time) if hasattr(a, "time") and a.time is not None else "Unknown"
            ),
            "Count": lambda a: (
                str(a.count) if hasattr(a, "count") and a.count is not None else "1"
            ),
            "Text": lambda a: clean_text(a.text)[:40],
        },
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize the formatter with optional configuration.

        Args:
            config: Optional configuration dictionary with 'columns' and 'extractors' keys.
                   If None, uses DEFAULT_CONFIG.
        """
        self.config = config or self.DEFAULT_CONFIG
        self.columns = self.config["columns"]
        self.extractors = self.config["extractors"]

    def alarm_to_row(self, alarm: Alarm) -> List[str]:
        """Convert an Alarm object to a list of values.

        Args:
            alarm: Alarm object from Cumulocity API

        Returns:
            List of string values representing alarm data
        """
        return [extractor(alarm) for extractor in self.extractors.values()]

    def alarms_to_table(self, alarms: List[Any], tablefmt: str = "tsv") -> str:
        """Convert a list of Alarm objects to a formatted table.

        Args:
            alarms: List of Alarm objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        rows = [self.alarm_to_row(alarm) for alarm in alarms]
        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=self.columns, tablefmt=tablefmt)

    def alarm_to_formatted_string(self, alarm: Any) -> str:
        """Convert an Alarm object to a formatted string with key-value pairs.

        Args:
            alarm: Alarm object from Cumulocity API

        Returns:
            Formatted string with key-value pairs, one per line
        """
        data = [
            [column, extractor(alarm)] for column, extractor in self.extractors.items()
        ]
        return tabulate(data, tablefmt="plain")


class EventFormatter:
    """Helper class for formatting event data in various formats."""

    DEFAULT_CONFIG = {
        "columns": [
            "Event ID",
            "Source",
            "Type",
            "Time",
            "Text",
            "Creation Time",
        ],
        "extractors": {
            "Event ID": lambda e: str(e.id),
            "Source": lambda e: (
                str(e.source.id)
                if hasattr(e, "source") and e.source is not None
                else "Unknown"
            ),
            "Type": lambda e: (
                str(e.type) if hasattr(e, "type") and e.type is not None else "Unknown"
            ),
            "Time": lambda e: (
                str(e.time) if hasattr(e, "time") and e.time is not None else "Unknown"
            ),
            "Text": lambda e: (
                str(e.text) if hasattr(e, "text") and e.text is not None else "Unknown"
            ),
            "Creation Time": lambda e: (
                str(e.creationTime)
                if hasattr(e, "creationTime") and e.creationTime is not None
                else "Unknown"
            ),
        },
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize the formatter with optional configuration.

        Args:
            config: Optional configuration dictionary with 'columns' and 'extractors' keys.
                   If None, uses DEFAULT_CONFIG.
        """
        self.config = config or self.DEFAULT_CONFIG
        self.columns = self.config["columns"]
        self.extractors = self.config["extractors"]

    def event_to_row(self, event: Any) -> List[str]:
        """Convert an Event object to a list of values.

        Args:
            event: Event object from Cumulocity API

        Returns:
            List of string values representing event data
        """
        return [extractor(event) for extractor in self.extractors.values()]

    def events_to_table(self, events: List[Any], tablefmt: str = "tsv") -> str:
        """Convert a list of Event objects to a formatted table.

        Args:
            events: List of Event objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        rows = [self.event_to_row(event) for event in events]
        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=self.columns, tablefmt=tablefmt)

    def event_to_formatted_string(self, event: Any) -> str:
        """Convert an Event object to a formatted string with key-value pairs.

        Args:
            event: Event object from Cumulocity API

        Returns:
            Formatted string with key-value pairs, one per line
        """
        data = [
            [column, extractor(event)] for column, extractor in self.extractors.items()
        ]
        return tabulate(data, tablefmt="plain")


class OperationFormatter:
    """Helper class for formatting operation data in various formats."""

    DEFAULT_CONFIG = {
        "columns": [
            "Operation ID",
            "Device ID",
            "Status",
            "Creation Time",
            "Failure Reason",
            "Description",
        ],
        "extractors": {
            "Operation ID": lambda o: str(o.id),
            "Device ID": lambda o: (
                str(o.deviceId)
                if hasattr(o, "deviceId") and o.deviceId is not None
                else "Unknown"
            ),
            "Status": lambda o: (
                str(o.status)
                if hasattr(o, "status") and o.status is not None
                else "Unknown"
            ),
            "Creation Time": lambda o: (
                str(o.creationTime)
                if hasattr(o, "creationTime") and o.creationTime is not None
                else "Unknown"
            ),
            "Failure Reason": lambda o: (
                str(o.failureReason)
                if hasattr(o, "failureReason") and o.failureReason is not None
                else "N/A"
            ),
            "Description": lambda o: (
                str(o.description)
                if hasattr(o, "description") and o.description is not None
                else "Unknown"
            ),
        },
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize the formatter with optional configuration.

        Args:
            config: Optional configuration dictionary with 'columns' and 'extractors' keys.
                   If None, uses DEFAULT_CONFIG.
        """
        self.config = config or self.DEFAULT_CONFIG
        self.columns = self.config["columns"]
        self.extractors = self.config["extractors"]

    def operation_to_row(self, operation: Any) -> List[str]:
        """Convert an Operation object to a list of values.

        Args:
            operation: Operation object from Cumulocity API

        Returns:
            List of string values representing operation data
        """
        return [extractor(operation) for extractor in self.extractors.values()]

    def operations_to_table(self, operations: List[Any], tablefmt: str = "tsv") -> str:
        """Convert a list of Operation objects to a formatted table.

        Args:
            operations: List of Operation objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        rows = [self.operation_to_row(operation) for operation in operations]
        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=self.columns, tablefmt=tablefmt)

    def operation_to_formatted_string(self, operation: Any) -> str:
        """Convert an Operation object to a formatted string with key-value pairs.

        Args:
            operation: Operation object from Cumulocity API

        Returns:
            Formatted string with key-value pairs, one per line
        """
        data = [
            [column, extractor(operation)]
            for column, extractor in self.extractors.items()
        ]
        return tabulate(data, tablefmt="plain")


class AuditLogFormatter:
    """Helper class for formatting audit log data in various formats."""

    DEFAULT_CONFIG = {
        "columns": [
            "Record ID",
            "User",
            "Activity",
            "Type",
            "Severity",
            "Time",
            "Source",
            "Text",
        ],
        "extractors": {
            "Record ID": lambda a: str(a.id),
            "User": lambda a: (
                str(a.user) if hasattr(a, "user") and a.user is not None else "Unknown"
            ),
            "Activity": lambda a: (
                str(a.activity)
                if hasattr(a, "activity") and a.activity is not None
                else "Unknown"
            ),
            "Type": lambda a: (
                str(a.type) if hasattr(a, "type") and a.type is not None else "Unknown"
            ),
            "Severity": lambda a: (
                str(a.severity)
                if hasattr(a, "severity") and a.severity is not None
                else "Unknown"
            ),
            "Time": lambda a: (
                str(a.time) if hasattr(a, "time") and a.time is not None else "Unknown"
            ),
            "Source": lambda a: (
                str(a.source.id)
                if hasattr(a, "source") and a.source is not None
                else "Unknown"
            ),
            "Text": lambda a: (
                str(a.text) if hasattr(a, "text") and a.text is not None else "Unknown"
            ),
        },
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize the formatter with optional configuration.

        Args:
            config: Optional configuration dictionary with 'columns' and 'extractors' keys.
                   If None, uses DEFAULT_CONFIG.
        """
        self.config = config or self.DEFAULT_CONFIG
        self.columns = self.config["columns"]
        self.extractors = self.config["extractors"]

    def audit_log_to_row(self, audit_log: Any) -> List[str]:
        """Convert an Audit Log object to a list of values.

        Args:
            audit_log: Audit Log object from Cumulocity API

        Returns:
            List of string values representing audit log data
        """
        return [extractor(audit_log) for extractor in self.extractors.values()]

    def audit_logs_to_table(self, audit_logs: List[Any], tablefmt: str = "tsv") -> str:
        """Convert a list of Audit Log objects to a formatted table.

        Args:
            audit_logs: List of Audit Log objects from Cumulocity API
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        rows = [self.audit_log_to_row(audit_log) for audit_log in audit_logs]
        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=self.columns, tablefmt=tablefmt)

    def audit_log_to_formatted_string(self, audit_log: Any) -> str:
        """Convert an Audit Log object to a formatted string with key-value pairs.

        Args:
            audit_log: Audit Log object from Cumulocity API

        Returns:
            Formatted string with key-value pairs, one per line
        """
        data = [
            [column, extractor(audit_log)]
            for column, extractor in self.extractors.items()
        ]
        return tabulate(data, tablefmt="plain")


class TableFormatter:
    """Helper class for formatting generic tables using tabulate."""

    @staticmethod
    def print_table(
        headers: List[str], rows: List[List[str]], tablefmt: str = "tsv"
    ) -> str:
        """Convert headers and rows to a formatted table.

        Args:
            headers: List of column headers
            rows: List of rows, where each row is a list of values
            tablefmt: Table format to use (default: 'tsv').
                     See tabulate documentation for available formats.

        Returns:
            Formatted string containing the complete table with header and data rows
        """
        if tablefmt == "json":
            return json.dumps(rows)
        return tabulate(rows, headers=headers, tablefmt=tablefmt)

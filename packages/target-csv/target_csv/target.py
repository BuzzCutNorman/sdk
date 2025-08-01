"""Sample target test for target-csv."""

from __future__ import annotations

from singer_sdk import typing as th
from singer_sdk.target_base import Target
from target_csv.sink import CSVSink


class TargetCSV(Target):
    """Sample target for CSV."""

    name = "target-csv"
    config_jsonschema = th.PropertiesList(
        th.Property(
            "target_folder",
            th.StringType,
            default="output",
            required=False,  # Default value will be used if not provided
            title="Target Folder",
        ),
        th.Property("file_naming_scheme", th.StringType, title="File Naming Scheme"),
    ).to_dict()
    default_sink_class = CSVSink

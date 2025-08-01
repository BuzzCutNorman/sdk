"""SDK for building Singer taps."""

from __future__ import annotations

from singer_sdk import streams
from singer_sdk.connectors import SQLConnector
from singer_sdk.mapper_base import InlineMapper
from singer_sdk.plugin_base import PluginBase
from singer_sdk.schema.source import (
    OpenAPISchema,
    SchemaDirectory,
    SchemaSource,
    StreamSchema,
)
from singer_sdk.sinks import BatchSink, RecordSink, Sink, SQLSink
from singer_sdk.streams import GraphQLStream, RESTStream, SQLStream, Stream
from singer_sdk.tap_base import SQLTap, Tap
from singer_sdk.target_base import SQLTarget, Target

__all__ = [
    "BatchSink",
    "GraphQLStream",
    "InlineMapper",
    "OpenAPISchema",
    "PluginBase",
    "RESTStream",
    "RecordSink",
    "SQLConnector",
    "SQLSink",
    "SQLStream",
    "SQLTap",
    "SQLTarget",
    "SchemaDirectory",
    "SchemaSource",
    "Sink",
    "Stream",
    "StreamSchema",
    "Tap",
    "Target",
    "streams",
]

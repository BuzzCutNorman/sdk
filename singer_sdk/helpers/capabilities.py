"""Module with helpers to declare capabilities and plugin behavior."""

from __future__ import annotations

import typing as t
from enum import Enum, EnumMeta
from warnings import warn

from singer_sdk.typing import (
    AnyOf,
    ArrayType,
    BooleanType,
    Constant,
    IntegerType,
    NullType,
    NumberType,
    ObjectType,
    OneOf,
    PropertiesList,
    Property,
    StringType,
)

_EnumMemberT = t.TypeVar("_EnumMemberT")

# Default JSON Schema to support config for built-in capabilities:

STREAM_MAPS_CONFIG = PropertiesList(
    Property(
        "stream_maps",
        ObjectType(
            Property(
                "__else__",
                AnyOf(Constant("__NULL__"), NullType()),
                nullable=True,
                required=False,
                title="Other streams",
                description=(
                    "Currently, only setting this to `__NULL__` is supported. "
                    "This will remove all other streams."
                ),
            ),
            # Stream names → Stream map config
            additional_properties=AnyOf(
                Constant("__NULL__"),  # Remove the stream.
                NullType(),  # Remove the stream.
                ObjectType(  # Map the stream using this configuration.
                    Property(
                        "__alias__",
                        StringType,
                        title="Stream Alias",
                        description="Alias to use for the stream.",
                        nullable=False,
                        required=False,
                    ),
                    Property(
                        "__else__",
                        AnyOf(Constant("__NULL__"), NullType()),
                        title="Other properties",
                        description=(
                            "Currently, only setting this to `__NULL__` is supported. "
                            "This will remove all other properties from the stream."
                        ),
                        required=False,
                        nullable=False,
                    ),
                    Property(
                        "__filter__",
                        StringType(pattern=r"^bool\((.*)\)$"),
                        title="Filter",
                        description=(
                            "Filter out records from a stream. A string expression "
                            "which must evaluate to `true` to include the record, or "
                            "`false` to exclude it. Filter expressions should be "
                            "wrapped in `bool()` to ensure proper type conversion."
                        ),
                        nullable=False,
                        required=False,
                    ),
                    Property(
                        "__key_properties__",
                        ArrayType(StringType),
                        title="Key Properties",
                        description="Primary key properties for the stream.",
                        nullable=False,
                        required=False,
                    ),
                    Property(
                        "__source__",
                        StringType,
                        description="Create a new stream from this source stream.",
                        nullable=False,
                        required=False,
                    ),
                    # Property names → Property map config
                    additional_properties=AnyOf(
                        Constant("__NULL__"),  # Remove the property from the stream.
                        NullType(),  # Remove the property from the stream.
                        StringType(),  # Compute the property using this expression.
                    ),
                ),
            ),
        ),
        title="Stream Maps",
        description=(
            "Config object for stream maps capability. "
            "For more information check out "
            "[Stream Maps](https://sdk.meltano.com/en/latest/stream_maps.html)."
        ),
    ),
    Property(
        "stream_map_config",
        ObjectType(),
        title="User Stream Map Configuration",
        description="User-defined config values to be used within map expressions.",
    ),
    Property(
        "faker_config",
        ObjectType(
            Property(
                "seed",
                OneOf(NumberType, StringType, BooleanType),
                title="Faker Seed",
                description=(
                    "Value to seed the Faker generator for deterministic output: "
                    "https://faker.readthedocs.io/en/master/#seeding-the-generator"
                ),
            ),
            Property(
                "locale",
                OneOf(StringType, ArrayType(StringType)),
                title="Faker Locale",
                description=(
                    "One or more LCID locale strings to produce localized output for: "
                    "https://faker.readthedocs.io/en/master/#localization"
                ),
            ),
        ),
        title="Faker Configuration",
        description=(
            "Config for the [`Faker`](https://faker.readthedocs.io/en/master/) "
            "instance variable `fake` used within map expressions. Only applicable if "
            "the plugin specifies `faker` as an additional dependency (through the "
            "`singer-sdk` `faker` extra or directly)."
        ),
    ),
).to_dict()
FLATTENING_CONFIG = PropertiesList(
    Property(
        "flattening_enabled",
        BooleanType(),
        title="Enable Schema Flattening",
        description=(
            "'True' to enable schema flattening and automatically expand nested "
            "properties."
        ),
    ),
    Property(
        "flattening_max_depth",
        IntegerType(),
        title="Max Flattening Depth",
        description="The max depth to flatten schemas.",
    ),
).to_dict()
BATCH_CONFIG = PropertiesList(
    Property(
        "batch_config",
        title="Batch Configuration",
        description="Configuration for BATCH message capabilities.",
        wrapped=ObjectType(
            Property(
                "encoding",
                title="Batch Encoding Configuration",
                description="Specifies the format and compression of the batch files.",
                wrapped=ObjectType(
                    Property(
                        "format",
                        StringType,
                        allowed_values=["jsonl", "parquet"],
                        title="Batch Encoding Format",
                        description="Format to use for batch files.",
                    ),
                    Property(
                        "compression",
                        StringType,
                        allowed_values=["gzip", "none"],
                        title="Batch Compression Format",
                        description="Compression format to use for batch files.",
                    ),
                ),
            ),
            Property(
                "storage",
                title="Batch Storage Configuration",
                description="Defines the storage layer to use when writing batch files",
                wrapped=ObjectType(
                    Property(
                        "root",
                        StringType,
                        title="Batch Storage Root",
                        description="Root path to use when writing batch files.",
                    ),
                    Property(
                        "prefix",
                        StringType,
                        title="Batch Storage Prefix",
                        description="Prefix to use when writing batch files.",
                    ),
                ),
            ),
        ),
    ),
).to_dict()
SQL_TAP_USE_SINGER_DECIMAL = PropertiesList(
    Property(
        "use_singer_decimal",
        BooleanType(),
        title="Use Singer Decimal",
        description=(
            "Whether to use use strings with `x-singer.decimal` format for "
            "decimals in the discovered schema. "
            "This is useful to avoid precision loss when working with large numbers."
        ),
    ),
).to_dict()
TARGET_SCHEMA_CONFIG = PropertiesList(
    Property(
        "default_target_schema",
        StringType(),
        title="Default Target Schema",
        description="The default target database schema name to use for all streams.",
    ),
).to_dict()
EMIT_ACTIVATE_VERSION_CONFIG = PropertiesList(
    Property(
        "emit_activate_version_messages",
        BooleanType,
        default=False,
        title="Emit `ACTIVATE_VERSION` messages",
        description=(
            "Whether to emit `ACTIVATE_VERSION` messages. If set to `True`, "
            "the tap will emit `ACTIVATE_VERSION` messages for each stream."
        ),
    ),
).to_dict()
ACTIVATE_VERSION_CONFIG = PropertiesList(
    Property(
        "process_activate_version_messages",
        BooleanType,
        default=True,
        title="Process `ACTIVATE_VERSION` messages",
        description="Whether to process `ACTIVATE_VERSION` messages.",
    ),
).to_dict()
ADD_RECORD_METADATA_CONFIG = PropertiesList(
    Property(
        "add_record_metadata",
        BooleanType(),
        title="Add Record Metadata",
        description="Whether to add metadata fields to records.",
    ),
).to_dict()
TARGET_HARD_DELETE_CONFIG = PropertiesList(
    Property(
        "hard_delete",
        BooleanType(),
        title="Hard Delete",
        description="Hard delete records.",
        default=False,
    ),
).to_dict()
TARGET_VALIDATE_RECORDS_CONFIG = PropertiesList(
    Property(
        "validate_records",
        BooleanType(),
        title="Validate Records",
        description="Whether to validate the schema of the incoming streams.",
        default=True,
    ),
).to_dict()
TARGET_BATCH_SIZE_ROWS_CONFIG = PropertiesList(
    Property(
        "batch_size_rows",
        IntegerType,
        title="Batch Size Rows",
        description="Maximum number of rows in each batch.",
    ),
).to_dict()


class TargetLoadMethods(str, Enum):
    """Target-specific capabilities."""

    # always write all input records whether that records already exists or not
    APPEND_ONLY = "append-only"

    # update existing records and insert new records
    UPSERT = "upsert"

    # delete all existing records and insert all input records
    OVERWRITE = "overwrite"


TARGET_LOAD_METHOD_CONFIG = PropertiesList(
    Property(
        "load_method",
        StringType(),
        description=(
            "The method to use when loading data into the destination. "
            "`append-only` will always write all input records whether that records "
            "already exists or not. `upsert` will update existing records and insert "
            "new records. `overwrite` will delete all existing records and insert all "
            "input records."
        ),
        allowed_values=[
            TargetLoadMethods.APPEND_ONLY,
            TargetLoadMethods.UPSERT,
            TargetLoadMethods.OVERWRITE,
        ],
        default=TargetLoadMethods.APPEND_ONLY,
    ),
).to_dict()


class DeprecatedEnum(Enum):
    """Base class for capabilities enumeration."""

    deprecation: str | None

    def __new__(  # noqa: PYI034
        cls,
        value: _EnumMemberT,
        deprecation: str | None = None,
    ) -> DeprecatedEnum:
        """Create a new enum member.

        Args:
            value: Enum member value.
            deprecation: Deprecation message.

        Returns:
            An enum member value.
        """
        member: DeprecatedEnum = object.__new__(cls)
        member._value_ = value
        member.deprecation = deprecation
        return member

    @property
    def deprecation_message(self) -> str | None:
        """Get deprecation message.

        Returns:
            Deprecation message.
        """
        return self.deprecation

    def emit_warning(self) -> None:
        """Emit deprecation warning."""
        warn(
            f"{self.name} is deprecated. {self.deprecation_message}",
            DeprecationWarning,
            stacklevel=3,
        )


class DeprecatedEnumMeta(EnumMeta):
    """Metaclass for enumeration with deprecation support."""

    def __getitem__(cls, name: str) -> t.Any:  # noqa: ANN401
        """Retrieve mapping item.

        Args:
            name: Item name.

        Returns:
            Enum member.
        """
        obj: Enum = super().__getitem__(name)
        if isinstance(obj, DeprecatedEnum) and obj.deprecation_message:
            obj.emit_warning()
        return obj

    def __getattribute__(cls, name: str) -> t.Any:  # noqa: ANN401
        """Retrieve enum attribute.

        Args:
            name: Attribute name.

        Returns:
            Attribute.
        """
        obj = super().__getattribute__(name)
        if isinstance(obj, DeprecatedEnum) and obj.deprecation_message:
            obj.emit_warning()
        return obj

    def __call__(cls, *args: t.Any, **kwargs: t.Any) -> t.Any:  # noqa: ANN401
        """Call enum member.

        Args:
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            Enum member.
        """
        obj = super().__call__(*args, **kwargs)
        if isinstance(obj, DeprecatedEnum) and obj.deprecation_message:
            obj.emit_warning()
        return obj


class CapabilitiesEnum(DeprecatedEnum, metaclass=DeprecatedEnumMeta):
    """Base capabilities enumeration."""

    def __str__(self) -> str:
        """String representation.

        Returns:
            Stringified enum value.
        """
        return str(self.value)

    def __repr__(self) -> str:
        """String representation.

        Returns:
            Stringified enum value.
        """
        return str(self.value)


class PluginCapabilities(CapabilitiesEnum):
    """Core capabilities which can be supported by taps and targets."""

    #: Support plugin capability and setting discovery.
    ABOUT = "about"

    #: Support :doc:`inline stream map transforms</stream_maps>`.
    STREAM_MAPS = "stream-maps"

    #: Support schema flattening, aka unnesting of complex properties.
    FLATTENING = "schema-flattening"

    #: Support the
    #: `ACTIVATE_VERSION <https://hub.meltano.com/singer/docs#activate-version>`_
    #: extension.
    ACTIVATE_VERSION = "activate-version"

    #: Input and output from
    #: `batched files <https://hub.meltano.com/singer/docs#batch>`_.
    #: A.K.A ``FAST_SYNC``.
    BATCH = "batch"


class TapCapabilities(CapabilitiesEnum):
    """Tap-specific capabilities."""

    #: Generate a catalog with `--discover`.
    DISCOVER = "discover"

    #: Accept input catalog, apply metadata and selection rules.
    CATALOG = "catalog"

    #: Incremental refresh by means of state tracking.
    STATE = "state"

    #: Automatic connectivity and stream init test via :ref:`--test<Test connectivity>`.
    TEST = "test"

    #: Support for ``replication_method: LOG_BASED``. You can read more about this
    #: feature in `MeltanoHub <https://hub.meltano.com/singer/docs#log-based>`_.
    LOG_BASED = "log-based"

    #: Deprecated. Please use :attr:`~TapCapabilities.CATALOG` instead.
    PROPERTIES = "properties", "Please use CATALOG instead."

    #: Support for ``ACTIVATE_VERSION`` messages.
    ACTIVATE_VERSION = "activate-version"


class TargetCapabilities(CapabilitiesEnum):
    """Target-specific capabilities."""

    #: Allows a ``soft_delete=True`` config option.
    #: Requires a tap stream supporting :attr:`PluginCapabilities.ACTIVATE_VERSION`
    #: and/or :attr:`TapCapabilities.LOG_BASED`.
    SOFT_DELETE = "soft-delete"

    #: Allows a ``hard_delete=True`` config option.
    #: Requires a tap stream supporting :attr:`PluginCapabilities.ACTIVATE_VERSION`
    #: and/or :attr:`TapCapabilities.LOG_BASED`.
    HARD_DELETE = "hard-delete"

    #: Fail safe for unknown JSON Schema types.
    DATATYPE_FAILSAFE = "datatype-failsafe"

    #: Allow setting the target schema.
    TARGET_SCHEMA = "target-schema"

    #: Validate the schema of the incoming records.
    VALIDATE_RECORDS = "validate-records"

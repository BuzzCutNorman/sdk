"""Tap abstract class."""

from __future__ import annotations

import abc
import contextlib
import typing as t
import warnings
from enum import Enum

import click

from singer_sdk.configuration._dict_config import merge_missing_config_jsonschema
from singer_sdk.exceptions import (
    AbortedSyncFailedException,
    AbortedSyncPausedException,
    ConfigValidationError,
)
from singer_sdk.helpers import _state
from singer_sdk.helpers._compat import SingerSDKDeprecationWarning
from singer_sdk.helpers._state import StateWriter, write_stream_state
from singer_sdk.helpers._util import dump_json, load_json, read_json_file
from singer_sdk.helpers.capabilities import (
    BATCH_CONFIG,
    SQL_TAP_USE_SINGER_DECIMAL,
    CapabilitiesEnum,
    PluginCapabilities,
    TapCapabilities,
)
from singer_sdk.io_base import SingerWriter
from singer_sdk.plugin_base import BaseSingerWriter, PluginBase, _ConfigInput
from singer_sdk.singerlib import Catalog

if t.TYPE_CHECKING:
    from pathlib import PurePath
    from types import FrameType

    from singer_sdk.connectors import SQLConnector
    from singer_sdk.helpers import types
    from singer_sdk.mapper import PluginMapper
    from singer_sdk.singerlib.encoding.base import GenericSingerWriter
    from singer_sdk.streams import SQLStream, Stream

STREAM_MAPS_CONFIG = "stream_maps"


class CliTestOptionValue(Enum):
    """Values for CLI option --test."""

    All = "all"
    Schema = "schema"
    Disabled = "disabled"


class Tap(BaseSingerWriter, metaclass=abc.ABCMeta):  # noqa: PLR0904
    """Abstract base class for taps.

    The Tap class governs configuration, validation, and stream discovery for tap
    plugins.
    """

    dynamic_catalog: bool = False
    """Whether the tap's catalog is dynamic. Set to True if the catalog is
    generated dynamically (e.g. by querying a database's system tables)."""

    message_writer_class: type[GenericSingerWriter] = SingerWriter
    """The message writer class to use for writing messages."""

    #: A list of capabilities supported by this tap.
    capabilities: t.ClassVar[list[CapabilitiesEnum]] = [
        TapCapabilities.CATALOG,
        TapCapabilities.STATE,
        TapCapabilities.DISCOVER,
        TapCapabilities.ACTIVATE_VERSION,
        PluginCapabilities.ABOUT,
        PluginCapabilities.STREAM_MAPS,
        PluginCapabilities.FLATTENING,
        PluginCapabilities.BATCH,
    ]

    # Constructor

    def __init__(
        self,
        *,
        config: dict | PurePath | str | list[PurePath | str] | None = None,
        catalog: PurePath | str | dict | Catalog | None = None,
        state: PurePath | str | dict | None = None,
        parse_env_config: bool = False,
        validate_config: bool = True,
        setup_mapper: bool = True,
        message_writer: GenericSingerWriter | None = None,
    ) -> None:
        """Initialize the tap.

        Args:
            config: Tap configuration. Can be a dictionary, a single path to a
                configuration file, or a list of paths to multiple configuration
                files.
            catalog: Tap catalog. Can be a dictionary or a path to the catalog file.
            state: Tap state. Can be dictionary or a path to the state file.
            parse_env_config: Whether to look for configuration values in environment
                variables.
            validate_config: True to require validation of config settings.
            setup_mapper: True to initialize the plugin mapper.
            message_writer: The class class to use for writing Singer messages.
        """
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
            message_writer=message_writer,
        )

        # Declare private members
        self._streams: dict[str, Stream] | None = None
        self._input_catalog: Catalog | None = None
        self._state: types.TapState = {}
        self._catalog: Catalog | None = None  # Tap's working catalog
        self._state_writer: StateWriter = StateWriter(self.message_writer)

        # Process input catalog
        if isinstance(catalog, Catalog):
            self._input_catalog = catalog
        elif isinstance(catalog, dict):
            self._input_catalog = Catalog.from_dict(catalog)  # type: ignore[arg-type]
        elif catalog is not None:
            self._input_catalog = Catalog.from_dict(read_json_file(catalog))
            warnings.warn(
                "Passing a catalog file path is deprecated. Please pass the catalog "
                "as a dictionary or Catalog object instead.",
                SingerSDKDeprecationWarning,
                stacklevel=2,
            )

        self._mapper: PluginMapper | None = None

        if setup_mapper:
            self.setup_mapper()

        # Process state
        state_dict: dict = {}
        if isinstance(state, dict):
            state_dict = state
        elif state:
            state_dict = read_json_file(state)
            warnings.warn(
                "Passing a state file path is deprecated. Please pass the state "
                "as a dictionary instead.",
                SingerSDKDeprecationWarning,
                stacklevel=2,
            )
        self.load_state(state_dict)

    # Class properties

    @property
    def streams(self) -> dict[str, Stream]:
        """Get streams discovered or catalogued for this tap.

        Results will be cached after first execution.

        Returns:
            A mapping of names to streams, using discovery or a provided catalog.
        """
        if self._streams is None:
            self._streams = {}
            input_catalog = self.input_catalog

            for stream in self.load_streams():
                if input_catalog is not None:
                    stream.apply_catalog(input_catalog)
                self._streams[stream.name] = stream
        return self._streams

    @property
    def state(self) -> types.TapState:
        """Get tap state.

        Returns:
            The tap's state dictionary

        Raises:
            RuntimeError: If state has not been initialized.
        """
        if self._state is None:
            msg = "Could not read from uninitialized state."  # type: ignore[unreachable]
            raise RuntimeError(msg)
        return self._state

    @property
    def input_catalog(self) -> Catalog | None:
        """Get the catalog passed to the tap.

        Returns:
            Catalog dictionary input, or None if not provided.
        """
        return self._input_catalog

    @property
    def state_writer(self) -> StateWriter:
        """Get the centralized state writer for this tap.

        Returns:
            The StateWriter instance for coordinated state message writing.
        """
        return self._state_writer

    @property
    def catalog(self) -> Catalog:
        """Get the tap's working catalog.

        Returns:
            A Singer catalog object.
        """
        if self._catalog is None:
            self._catalog = self.input_catalog or self._singer_catalog

        return self._catalog

    def setup_mapper(self) -> None:
        """Initialize the plugin mapper for this tap."""
        super().setup_mapper()
        self.mapper.register_raw_streams_from_catalog(self.catalog)

    @classmethod
    def append_builtin_config(cls: type[PluginBase], config_jsonschema: dict) -> None:
        """Appends built-in config to `config_jsonschema` if not already set.

        To customize or disable this behavior, developers may either override this class
        method or override the `capabilities` property to disabled any unwanted
        built-in capabilities.

        For all except very advanced use cases, we recommend leaving these
        implementations "as-is", since this provides the most choice to users and is
        the most "future proof" in terms of taking advantage of built-in capabilities
        which may be added in the future.

        Args:
            config_jsonschema: [description]
        """
        PluginBase.append_builtin_config(config_jsonschema)

        capabilities = cls.capabilities
        if PluginCapabilities.BATCH in capabilities:
            merge_missing_config_jsonschema(BATCH_CONFIG, config_jsonschema)

    # Connection and sync tests:

    @t.final
    def run_connection_test(self) -> bool:
        """Run connection test, aborting each stream after 1 record.

        Returns:
            True if the test succeeded.
        """
        return self.run_sync_dry_run(
            dry_run_record_limit=1,
            streams=self.streams.values(),
        )

    @t.final
    def run_sync_dry_run(
        self,
        dry_run_record_limit: int | None = 1,
        streams: t.Iterable[Stream] | None = None,
    ) -> bool:
        """Run connection test.

        Exceptions of type `MaxRecordsLimitException` and
        `PartialSyncSuccessException` will be ignored.

        Args:
            dry_run_record_limit: The max number of records to sync per stream object.
            streams: The streams to test. If omitted, all streams will be tested.

        Returns:
            True if the test succeeded.
        """
        if streams is None:
            streams = self.streams.values()

        for stream in streams:
            if not stream.child_streams:  # pragma: no branch
                # Initialize streams' record limits before beginning the sync test.
                stream.ABORT_AT_RECORD_COUNT = dry_run_record_limit

            # Force selection of streams.
            stream.selected = True

        for stream in streams:
            if stream.parent_stream_type:
                self.logger.debug(
                    "Child stream '%s' should be called by "
                    "parent stream '%s'. "
                    "Skipping direct invocation.",
                    type(stream).__name__,
                    stream.parent_stream_type.__name__,
                )
                continue
            with contextlib.suppress(
                AbortedSyncFailedException,
                AbortedSyncPausedException,
            ):
                stream.sync()
        return True

    @t.final
    def write_schemas(self) -> None:
        """Write a SCHEMA message for all known streams to STDOUT."""
        for stream in self.streams.values():
            stream.selected = True
            stream._write_schema_message()  # noqa: SLF001

    # Stream detection:

    def run_discovery(self) -> str:
        """Write the catalog json to STDOUT and return as a string.

        Returns:
            The catalog as a string of JSON.
        """
        catalog_text = self.catalog_json_text
        print(catalog_text)  # noqa: T201
        return catalog_text

    @property
    def catalog_dict(self) -> dict:
        """Get catalog dictionary.

        Returns:
            The tap's catalog as a dict
        """
        return t.cast("dict", self._singer_catalog.to_dict())

    @property
    def catalog_json_text(self) -> str:
        """Get catalog JSON.

        Returns:
            The tap's catalog as formatted JSON text.
        """
        return dump_json(self.catalog_dict, indent=2)

    @property
    def _singer_catalog(self) -> Catalog:
        """Return a Catalog object.

        Returns:
            :class:`singer_sdk.singerlib.Catalog`.
        """
        return Catalog(
            (stream.tap_stream_id, stream._singer_catalog_entry)  # noqa: SLF001
            for stream in self.streams.values()
        )

    def discover_streams(self) -> t.Sequence[Stream]:
        """Initialize all available streams and return them as a list.

        Return:
            List of discovered Stream objects.

        Raises:
            NotImplementedError: If the tap implementation does not override this
                method.
        """
        msg = (
            f"Tap '{self.name}' does not support discovery. Please set the '--catalog' "
            "command line argument and try again."
        )
        raise NotImplementedError(msg)

    @t.final
    def load_streams(self) -> list[Stream]:
        """Load streams from discovery and initialize DAG.

        Return the output of `self.discover_streams()` to enumerate
        discovered streams.

        Returns:
            A list of discovered streams, ordered by name.
        """
        # Build the parent-child dependency DAG

        # Index streams by type
        streams_by_type: dict[type[Stream], list[Stream]] = {}
        for stream in self.discover_streams():
            stream_type = type(stream)
            if stream_type not in streams_by_type:
                streams_by_type[stream_type] = []
            streams_by_type[stream_type].append(stream)

        # Initialize child streams list for parents
        for stream_type, streams in streams_by_type.items():
            if stream_type.parent_stream_type:
                parents = streams_by_type[stream_type.parent_stream_type]
                for parent in parents:
                    for stream in streams:
                        parent.child_streams.append(stream)
                        self.logger.info(
                            "Added '%s' as child stream to '%s'",
                            stream.name,
                            parent.name,
                        )

        streams = [stream for streams in streams_by_type.values() for stream in streams]
        return sorted(
            streams,
            key=lambda x: x.name,
            reverse=False,
        )

    # Bookmarks and state management

    def load_state(self, state: dict[str, t.Any]) -> None:
        """Merge or initialize stream state with the provided state dictionary input.

        Override this method to perform validation and backwards-compatibility patches
        on self.state. If overriding, we recommend first running
        `super().load_state(state)` to ensure compatibility with the SDK.

        Args:
            state: Initialize the tap's state with this value.

        Raises:
            ValueError: If the tap's own state is None, meaning it has not been
                initialized.
        """
        if self.state is None:
            msg = "Cannot write to uninitialized state dictionary."  # type: ignore[unreachable]
            raise ValueError(msg)

        for stream_name, stream_state in state.get("bookmarks", {}).items():
            for key, val in stream_state.items():
                write_stream_state(
                    self.state,
                    stream_name,
                    key,
                    val,
                )

    # State handling

    def _reset_state_progress_markers(self) -> None:
        """Clear prior jobs' progress markers at beginning of sync."""
        for state in self.state.get("bookmarks", {}).values():
            _state.reset_state_progress_markers(state)
            for partition_state in state.get("partitions", []):
                _state.reset_state_progress_markers(partition_state)

    # Fix sync replication method incompatibilities

    def _set_compatible_replication_methods(self) -> None:
        stream: Stream
        for stream in self.streams.values():
            for descendent in stream.descendent_streams:
                if descendent.selected and descendent.ignore_parent_replication_key:
                    self.logger.warning(
                        "Stream descendent '%s' is selected and "
                        "its parent '%s' does not use inclusive "
                        "replication keys. "
                        "Forcing full table replication for '%s'.",
                        descendent.name,
                        stream.name,
                        stream.name,
                    )
                    stream.replication_key = None
                    stream.forced_replication_method = "FULL_TABLE"

    # Sync methods

    @t.final
    def sync_all(self) -> None:
        """Sync all streams."""
        self._reset_state_progress_markers()
        self._set_compatible_replication_methods()
        if self.state:
            self._state_writer.write_state(self.state)

        stream: Stream
        for stream in self.streams.values():
            if not stream.selected and not stream.has_selected_descendents:
                self.logger.info("Skipping deselected stream '%s'.", stream.name)
                continue

            if stream.parent_stream_type:
                self.logger.debug(
                    "Child stream '%s' is expected to be called "
                    "by parent stream '%s'. "
                    "Skipping direct invocation.",
                    type(stream).__name__,
                    stream.parent_stream_type.__name__,
                )
                continue

            stream.sync()
            stream.finalize_state_progress_markers()

        # this second loop is needed for all streams to print out their costs
        # including child streams which are otherwise skipped in the loop above
        for stream in self.streams.values():
            stream.log_sync_costs()

    # Command Line Execution

    def _handle_termination(  # pragma: no cover
        self,
        signum: int,
        frame: FrameType | None,
    ) -> None:
        """Handle termination signal.

        Args:
            signum: Signal number.
            frame: Frame.
        """
        # Emit a final state message to ensure the state is written to the output
        # even if the process is terminated by a signal.
        try:
            self._state_writer.write_state(self.state)
        finally:
            super()._handle_termination(signum, frame)

    @classmethod
    def invoke(  # type: ignore[override]
        cls: type[Tap],
        *,
        about: bool = False,
        about_format: str | None = None,
        config: _ConfigInput | None = None,
        state: t.IO[str] | None = None,
        catalog: t.IO[str] | None = None,
    ) -> None:
        """Invoke the tap's command line interface.

        Args:
            about: Display package metadata and settings.
            about_format: Specify output style for `--about`.
            config: Configuration file location or 'ENV' to use environment
                variables. Accepts multiple inputs as a tuple.
            catalog: Use a Singer catalog file with the tap.",
            state: Use a bookmarks file for incremental replication.
        """
        super().invoke(about=about, about_format=about_format)
        cls.print_version(print_fn=cls.logger.info)
        config = config or _ConfigInput()

        tap = cls(
            config=config.config,
            state=None if state is None else load_json(state.read()),
            catalog=None if catalog is None else load_json(catalog.read()),
            parse_env_config=config.parse_env,
            validate_config=True,
        )
        tap.sync_all()

    @classmethod
    def cb_discover(
        cls: type[Tap],
        ctx: click.Context,
        param: click.Option,  # noqa: ARG003
        value: bool,  # noqa: FBT001
    ) -> None:
        """CLI callback to run the tap in discovery mode.

        Args:
            ctx: Click context.
            param: Click option.
            value: Whether to run in discovery mode.
        """
        if not value:
            return

        config: _ConfigInput = ctx.params.get("config", _ConfigInput())
        try:
            tap = cls(
                config=config.config,
                parse_env_config=config.parse_env,
                validate_config=cls.dynamic_catalog,
                setup_mapper=False,
            )
        except ConfigValidationError as exc:  # pragma: no cover
            for error in exc.errors:
                cls.logger.error("Config validation error: %s", error)  # noqa: TRY400
            ctx.exit(1)
        tap.run_discovery()
        ctx.exit()

    @classmethod
    def cb_test(
        cls: type[Tap],
        ctx: click.Context,
        param: click.Option,  # noqa: ARG003
        value: bool,  # noqa: FBT001
    ) -> None:
        """CLI callback to run the tap in test mode.

        Args:
            ctx: Click context.
            param: Click option.
            value: Whether to run in test mode.
        """
        if value == CliTestOptionValue.Disabled.value:
            return

        config: _ConfigInput = ctx.params.get("config", _ConfigInput())
        tap = cls(
            config=config.config,
            parse_env_config=config.parse_env,
            validate_config=True,
        )

        if value == CliTestOptionValue.Schema.value:
            tap.write_schemas()
        else:
            tap.run_connection_test()

        ctx.exit()

    @classmethod
    def get_singer_command(cls: type[Tap]) -> click.Command:
        """Execute standard CLI handler for taps.

        Returns:
            A click.Command object.
        """
        command = super().get_singer_command()
        command.help = "Execute the Singer tap."
        command.params.extend(
            [
                click.Option(
                    ["--discover"],
                    is_flag=True,
                    help="Run the tap in discovery mode.",
                    callback=cls.cb_discover,
                    expose_value=False,
                ),
                click.Option(
                    ["--test"],
                    is_flag=False,
                    flag_value=CliTestOptionValue.All.value,
                    default=CliTestOptionValue.Disabled.value,
                    help=(
                        "Use --test to sync a single record for each stream. "
                        "Use --test=schema to test schema output without syncing "
                        "records."
                    ),
                    callback=cls.cb_test,
                    expose_value=False,
                ),
                click.Option(
                    ["--catalog"],
                    help="Use a Singer catalog file with the tap.",
                    type=click.File(),
                ),
                click.Option(
                    ["--state"],
                    help="Use a bookmarks file for incremental replication.",
                    type=click.File(),
                ),
            ],
        )

        return command


class SQLTap(Tap):
    """A specialized Tap for extracting from SQL streams."""

    default_stream_class: type[SQLStream]
    """
    The default stream class used to initialize new SQL streams from their catalog
    entries.
    """

    dynamic_catalog: bool = True
    """
    Whether the tap's catalog is dynamic, enabling configuration validation in
    discovery mode. Set to True if the catalog is generated dynamically (e.g. by
    querying a database's system tables).
    """

    exclude_schemas: t.Sequence[str] = []
    """Hard-coded list of stream names to skip when discovering the catalog."""

    _tap_connector: SQLConnector | None = None

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Initialize the SQL tap.

        The SQLTap initializer additionally creates a cache variable for _catalog_dict.

        Args:
            *args: Positional arguments for the Tap initializer.
            **kwargs: Keyword arguments for the Tap initializer.
        """
        self._catalog_dict: dict[str, list[dict]] | None = None
        super().__init__(*args, **kwargs)

    @classmethod
    def append_builtin_config(cls: type[SQLTap], config_jsonschema: dict) -> None:
        """Appends built-in config to `config_jsonschema` if not already set.

        Args:
            config_jsonschema: [description]
        """
        merge_missing_config_jsonschema(SQL_TAP_USE_SINGER_DECIMAL, config_jsonschema)
        super().append_builtin_config(config_jsonschema)

    @property
    def tap_connector(self) -> SQLConnector:
        """The connector object.

        Returns:
            The connector object.
        """
        if self._tap_connector is None:
            self._tap_connector = self.default_stream_class.connector_class(
                dict(self.config),
            )
        return self._tap_connector

    @property
    def catalog_dict(self) -> dict:
        """Get catalog dictionary.

        Returns:
            The tap's catalog as a dict
        """
        if self._catalog_dict is not None:
            return self._catalog_dict

        if self.input_catalog:
            return self.input_catalog.to_dict()

        connector = self.tap_connector

        self._catalog_dict = {
            "streams": connector.discover_catalog_entries(
                exclude_schemas=self.exclude_schemas
            )
        }
        return self._catalog_dict

    def discover_streams(self) -> t.Sequence[Stream]:
        """Initialize all available streams and return them as a sequence.

        Returns:
            A sequence of discovered Stream objects.
        """
        return [
            self.default_stream_class(
                tap=self,
                catalog_entry=catalog_entry,
                connector=self.tap_connector,
            )
            for catalog_entry in self.catalog_dict["streams"]
        ]

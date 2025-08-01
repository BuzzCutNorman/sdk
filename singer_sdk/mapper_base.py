"""Abstract base class for stream mapper plugins."""

from __future__ import annotations

import abc
import typing as t

import click

from singer_sdk.helpers.capabilities import CapabilitiesEnum, PluginCapabilities
from singer_sdk.plugin_base import BaseSingerReader, BaseSingerWriter, _ConfigInput

if t.TYPE_CHECKING:
    from pathlib import PurePath

    import singer_sdk.singerlib as singer
    from singer_sdk.singerlib.encoding.base import (
        GenericSingerReader,
        GenericSingerWriter,
    )


class InlineMapper(BaseSingerReader, BaseSingerWriter, metaclass=abc.ABCMeta):
    """Abstract base class for inline mappers."""

    #: A list of plugin capabilities.
    capabilities: t.ClassVar[list[CapabilitiesEnum]] = [
        PluginCapabilities.ABOUT,
        PluginCapabilities.STREAM_MAPS,
        PluginCapabilities.FLATTENING,
    ]

    def __init__(
        self,
        *,
        config: dict | PurePath | str | list[PurePath | str] | None = None,
        parse_env_config: bool = False,
        validate_config: bool = True,
        message_reader: GenericSingerReader | None = None,
        message_writer: GenericSingerWriter | None = None,
    ) -> None:
        """Initialize the inline mapper."""
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
        )
        self.message_reader = message_reader or self.message_reader_class()
        self.message_writer = message_writer or self.message_writer_class()

    def _write_messages(self, messages: t.Iterable[singer.Message]) -> None:
        for message in messages:
            self.write_message(message)

    def _process_schema_message(self, message_dict: dict) -> None:
        self._write_messages(self.map_schema_message(message_dict))

    def _process_record_message(self, message_dict: dict) -> None:
        self._write_messages(self.map_record_message(message_dict))

    def _process_state_message(self, message_dict: dict) -> None:
        self._write_messages(self.map_state_message(message_dict))

    def _process_activate_version_message(self, message_dict: dict) -> None:
        self._write_messages(self.map_activate_version_message(message_dict))

    def _process_batch_message(self, message_dict: dict) -> None:
        self._write_messages(self.map_batch_message(message_dict))

    @abc.abstractmethod
    def map_schema_message(self, message_dict: dict) -> t.Iterable[singer.Message]:
        """Map a schema message to zero or more new messages.

        Args:
            message_dict: A SCHEMA message JSON dictionary.
        """
        ...

    @abc.abstractmethod
    def map_record_message(self, message_dict: dict) -> t.Iterable[singer.Message]:
        """Map a record message to zero or more new messages.

        Args:
            message_dict: A RECORD message JSON dictionary.
        """
        ...

    @abc.abstractmethod
    def map_state_message(self, message_dict: dict) -> t.Iterable[singer.Message]:
        """Map a state message to zero or more new messages.

        Args:
            message_dict: A STATE message JSON dictionary.
        """
        ...

    @abc.abstractmethod
    def map_activate_version_message(
        self,
        message_dict: dict,
    ) -> t.Iterable[singer.Message]:
        """Map a version message to zero or more new messages.

        Args:
            message_dict: An ACTIVATE_VERSION message JSON dictionary.
        """
        ...

    def map_batch_message(
        self,
        message_dict: dict,
    ) -> t.Iterable[singer.Message]:
        """Map a batch message to zero or more new messages.

        Args:
            message_dict: A BATCH message JSON dictionary.

        Raises:
            NotImplementedError: if not implemented by subclass.
        """
        msg = "BATCH messages are not supported by mappers."
        raise NotImplementedError(msg)

    # CLI handler

    @classmethod
    def invoke(  # type: ignore[override]
        cls: type[InlineMapper],
        *,
        about: bool = False,
        about_format: str | None = None,
        config: _ConfigInput | None = None,
        file_input: t.IO[str] | None = None,
    ) -> None:
        """Invoke the mapper.

        Args:
            about: Display package metadata and settings.
            about_format: Specify output style for `--about`.
            config: Configuration file location or 'ENV' to use environment
                variables. Accepts multiple inputs as a tuple.
            file_input: Optional file to read input from.
        """
        super().invoke(about=about, about_format=about_format)
        cls.print_version(print_fn=cls.logger.info)
        config = config or _ConfigInput()

        mapper = cls(
            config=config.config,
            validate_config=True,
            parse_env_config=config.parse_env,
        )
        mapper.listen(file_input)

    @classmethod
    def get_singer_command(cls: type[InlineMapper]) -> click.Command:
        """Execute standard CLI handler for inline mappers.

        Returns:
            A click.Command object.
        """
        command = super().get_singer_command()
        command.help = "Execute the Singer mapper."
        command.params.extend(
            [
                click.Option(
                    ["--input", "file_input"],
                    help="A path to read messages from instead of from standard in.",
                    type=click.File("r"),
                ),
            ],
        )

        return command

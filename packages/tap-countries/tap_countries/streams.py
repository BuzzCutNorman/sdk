"""Sample tap stream test for tap-countries.

This uses a free "Countries API" which does not require authentication.

See the online explorer and query builder here:
  - https://countries.trevorblades.com/
"""

from __future__ import annotations

import abc
import sys
import typing as t

from requests_cache.session import CachedSession

from singer_sdk import SchemaDirectory, StreamSchema
from singer_sdk import typing as th
from singer_sdk.streams.graphql import GraphQLStream
from tap_countries import schemas

if sys.version_info >= (3, 12):
    from typing import override  # noqa: ICN003
else:
    from typing_extensions import override


SCHEMAS_DIR = SchemaDirectory(schemas)


class CountriesAPIStream(GraphQLStream, metaclass=abc.ABCMeta):
    """Sample tap test for countries.

    NOTE: This API does not require authentication.
    """

    url_base = "https://countries.trevorblades.com/"

    @property
    @override
    def requests_session(self) -> CachedSession:
        return CachedSession(
            ".http_cache",
            backend="filesystem",
            serializer="json",
            allowable_methods=("POST", "HEAD"),
        )


class CountriesStream(CountriesAPIStream):
    """Countries API stream."""

    name = "countries"
    primary_keys = ("code",)
    query = """
        countries {
            code
            name
            native
            phone
            continent {
                code
                name
            }
            capital
            currency
            languages {
                code
                name
            }
            emoji
        }
        """
    schema = th.PropertiesList(
        th.Property("code", th.StringType),
        th.Property("name", th.StringType),
        th.Property("native", th.StringType),
        th.Property("phone", th.StringType),
        th.Property("capital", th.StringType),
        th.Property("currency", th.StringType),
        th.Property("emoji", th.StringType),
        th.Property(
            "continent",
            th.ObjectType(
                th.Property("code", th.StringType),
                th.Property("name", th.StringType),
            ),
        ),
        th.Property(
            "languages",
            th.ArrayType(
                th.ObjectType(
                    th.Property("code", th.StringType),
                    th.Property("name", th.StringType),
                ),
            ),
        ),
    ).to_dict()


class ContinentsStream(CountriesAPIStream):
    """Continents stream from the Countries API."""

    name = "continents"
    primary_keys = ("code",)
    schema: t.ClassVar[StreamSchema] = StreamSchema(SCHEMAS_DIR)
    query = """
        continents {
            code
            name
        }
        """

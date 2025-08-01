"""Sample tap stream test for tap-gitlab.

# See the interactive GraphQL query builder for GitLab data models here:
#  - https://gitlab.com/-/graphql-explorer
"""

from __future__ import annotations

import sys
import typing as t

from singer_sdk import SchemaDirectory, StreamSchema
from singer_sdk.streams import GraphQLStream
from tap_gitlab import schemas

if sys.version_info >= (3, 12):
    from typing import override  # noqa: ICN003
else:
    from typing_extensions import override

SITE_URL = "https://gitlab.com/graphql"

SCHEMAS_DIR = SchemaDirectory(schemas)


class GitlabGraphQLStream(GraphQLStream):
    """Sample tap test for gitlab."""

    url_base = SITE_URL
    schema: t.ClassVar[StreamSchema] = StreamSchema(SCHEMAS_DIR)

    @property
    @override
    def http_headers(self) -> dict:
        """Return headers dict to be used for HTTP requests.

        Note: This sample implementation bypasses the SimpleAuthenticator class and
        simply returns the http_headers directly, with the auth_token.
        """
        return {"Authorization": f"token {self.config.get('auth_token')}"}


class GraphQLCurrentUserStream(GitlabGraphQLStream):
    """Gitlab Current User stream."""

    name = "currentuser"
    primary_keys = ("id",)
    replication_key = None
    query = """
        currentUser {
            name
        }
        """  # noqa: RUF027


class GraphQLProjectsStream(GitlabGraphQLStream):
    """Gitlab Projects stream."""

    name = "projects"
    primary_keys = ("id",)
    replication_key = None

    @property
    @override
    def query(self) -> str:
        """Return dynamic GraphQL query."""
        return f"project(fullPath: {self.config['project_id']} {{ name }}"

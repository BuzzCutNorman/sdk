"""Sample tap stream test for tap-gitlab."""

from __future__ import annotations

import sys
import typing as t

from requests_cache import CachedSession

from singer_sdk import RESTStream, SchemaDirectory, StreamSchema
from singer_sdk.authenticators import SimpleAuthenticator
from singer_sdk.pagination import SimpleHeaderPaginator
from singer_sdk.typing import (
    ArrayType,
    DateTimeType,
    DateType,
    IntegerType,
    ObjectType,
    PropertiesList,
    Property,
    StringType,
)
from tap_gitlab import schemas

if sys.version_info >= (3, 12):
    from typing import override  # noqa: ICN003
else:
    from typing_extensions import override

if t.TYPE_CHECKING:
    from singer_sdk.helpers.types import Context


SCHEMAS_DIR = SchemaDirectory(schemas)


class GitlabStream(RESTStream[str]):
    """Sample tap test for gitlab."""

    _LOG_REQUEST_METRIC_URLS = True
    schema: t.ClassVar[StreamSchema] = StreamSchema(SCHEMAS_DIR)

    @property
    @override
    def url_base(self) -> str:
        """Return the base GitLab URL."""
        return self.config["url_base"]  # type: ignore[no-any-return]

    @property
    @override
    def requests_session(self) -> CachedSession:
        return CachedSession(
            ".http_cache",
            backend="filesystem",
            serializer="json",
            ignored_parameters=["Private-Token", "User-Agent"],
            match_headers=True,
        )

    @property
    @override
    def authenticator(self) -> SimpleAuthenticator:
        """Return an authenticator for REST API requests."""
        return SimpleAuthenticator(
            stream=self,
            auth_headers={"Private-Token": self.config["auth_token"]},
        )

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: str | None,
    ) -> dict[str, t.Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        return params

    @override
    def get_new_paginator(self) -> SimpleHeaderPaginator:
        """Return a new paginator for GitLab API endpoints.

        Returns:
            A new paginator.
        """
        return SimpleHeaderPaginator("X-Next-Page")


class ProjectBasedStream(GitlabStream):
    """Base class for streams that are keys based on project ID."""

    @property
    @override
    def partitions(self) -> list[dict]:
        """Return a list of partition key dicts (if applicable), otherwise None."""
        if "{project_id}" in self.path:
            return [
                {"project_id": pid}
                for pid in t.cast("list", self.config["project_ids"])
            ]
        if "{group_id}" in self.path:
            if group_ids := self.config["group_ids"]:
                return [{"group_id": gid} for gid in group_ids]

            msg = (
                "Missing `group_ids` setting which is required for the "
                f"'{self.name}' stream."
            )
            raise ValueError(msg)

        msg = (
            f"Could not detect partition type for Gitlab stream '{self.name}' "
            f"({self.path}). Expected a URL path containing '{{project_id}}' or "
            "'{{group_id}}'."
        )
        raise ValueError(msg)


class ProjectsStream(ProjectBasedStream):
    """Gitlab Projects stream."""

    name = "projects"
    path = "/projects/{project_id}?statistics=1"
    primary_keys = ("id",)
    replication_key = "last_activity_at"
    is_sorted = True


class ReleasesStream(ProjectBasedStream):
    """Gitlab Releases stream."""

    name = "releases"
    path = "/projects/{project_id}/releases"
    primary_keys = ("project_id", "tag_name")
    replication_key = None


class IssuesStream(ProjectBasedStream):
    """Gitlab Issues stream."""

    name = "issues"
    path = "/projects/{project_id}/issues?scope=all&updated_after={start_date}"
    primary_keys = ("id",)
    replication_key = "updated_at"
    is_sorted = False


class CommitsStream(ProjectBasedStream):
    """Gitlab Commits stream."""

    name = "commits"
    path = (
        "/projects/{project_id}/repository/commits?since={start_date}&with_stats=true"
    )
    primary_keys = ("id",)
    replication_key = "created_at"
    is_sorted = False


class EpicsStream(ProjectBasedStream):
    """Gitlab Epics stream.

    This class shows an example of inline `schema` declaration rather than referencing
    a raw json input file.
    """

    name = "epics"
    path = "/groups/{group_id}/epics?updated_after={start_date}"
    primary_keys = ("id",)
    replication_key = "updated_at"
    is_sorted = True
    schema = PropertiesList(
        Property("id", IntegerType, required=True),
        Property("iid", IntegerType, required=True),
        Property("group_id", IntegerType, required=True),
        Property("parent_id", IntegerType),
        Property("title", StringType),
        Property("description", StringType),
        Property("state", StringType),
        Property("start_date", DateType),
        Property("end_date", DateType),
        Property("due_date", DateType),
        Property("created_at", DateTimeType),
        Property("updated_at", DateTimeType),
        Property("labels", ArrayType(StringType)),
        Property("upvotes", IntegerType),
        Property("downvotes", IntegerType),
        Property(
            "author",
            ObjectType(
                Property("id", IntegerType),
                Property("name", StringType),
                Property("username", StringType),
                Property("state", StringType),
                Property("avatar_url", StringType),
                Property("web_url", StringType),
            ),
        ),
    ).to_dict()

    @override
    def get_child_context(
        self,
        record: dict,
        context: Context | None,
    ) -> dict:
        """Perform post processing, including queuing up any child stream types."""
        # Ensure child state record(s) are created
        return {
            "group_id": record["group_id"],
            "epic_id": record["id"],
            "epic_iid": record["iid"],
        }


class EpicIssuesStream(GitlabStream):
    """EpicIssues stream class."""

    name = "epic_issues"
    path = "/groups/{group_id}/epics/{epic_iid}/issues"
    primary_keys = ("id",)
    replication_key = None
    parent_stream_type = EpicsStream  # Stream should wait for parents to complete.

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: str | None,
    ) -> dict[str, t.Any]:
        """Return a dictionary of values to be used in parameterization."""
        result = super().get_url_params(context, next_page_token)
        if not context or "epic_id" not in context:
            msg = "Cannot sync epic issues without already known epic IDs."
            raise ValueError(msg)
        return result

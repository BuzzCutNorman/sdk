"""General helper functions, helper classes, and decorators."""

from __future__ import annotations

import json
import typing as t
from pathlib import Path, PurePath

import pendulum

if t.TYPE_CHECKING:
    import datetime


def read_json_file(path: PurePath | str) -> dict[str, t.Any]:
    """Read json file, throwing an error if missing."""
    if not path:
        msg = "Could not open file. Filepath not provided."
        raise RuntimeError(msg)

    if not Path(path).exists():
        msg = f"File at '{path}' was not found."
        for template in [f"{path}.template"]:
            if Path(template).exists():
                msg += f"\nFor more info, please see the sample template at: {template}"
        raise FileExistsError(msg)

    return t.cast(dict, json.loads(Path(path).read_text(encoding="utf-8")))


def utc_now() -> datetime.datetime:
    """Return current time in UTC."""
    # TODO: replace with datetime.datetime.now(tz=datetime.timezone.utc)
    return pendulum.now(tz="UTC")

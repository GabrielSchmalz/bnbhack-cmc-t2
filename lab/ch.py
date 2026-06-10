"""Read-only ClickHouse HTTP client.

`readonly=1` is hardcoded in the URL, not optional — the read-only
constraint is structural. This client is re-export plumbing only (PR-9);
the lab itself runs from committed CSVs in data/lab/.
"""

import os
from urllib.parse import urlsplit, urlunsplit

import requests


def base_url() -> str:
    return os.environ.get("CLICKHOUSE_URL", "http://localhost:8123").rstrip("/")


def _strip_credentials(url: str) -> str:
    """Drop any user:password@ userinfo from a URL (urllib.parse).

    The default localhost URL carries none — this is belt-and-braces so an
    HTTPError can never echo credentials embedded in CLICKHOUSE_URL."""
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    netloc = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query,
                       parts.fragment))


def query(sql: str, url: str | None = None, timeout: int = 120) -> list[tuple[str, ...]]:
    """Run a SELECT against ClickHouse over HTTP; return rows as tuples of strings.

    The query URL always carries readonly=1 — writes are structurally impossible.
    """
    url = (url or base_url()).rstrip("/")
    resp = requests.post(
        f"{url}/?readonly=1&default_format=TSV",
        data=sql.encode("utf-8"),
        timeout=timeout,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # re-raise with the URL's credentials stripped (never echo userinfo)
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason} from ClickHouse at "
            f"{_strip_credentials(url)}/?readonly=1&default_format=TSV",
            response=e.response,
        ) from None
    text = resp.text
    if not text:
        return []
    return [tuple(line.split("\t")) for line in text.splitlines()]

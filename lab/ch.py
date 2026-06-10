"""Read-only ClickHouse HTTP client.

`readonly=1` is hardcoded in the URL, not optional — the read-only
constraint is structural. This client is re-export plumbing only (PR-9);
the lab itself runs from committed CSVs in data/lab/.
"""

import os

import requests


def base_url() -> str:
    return os.environ.get("CLICKHOUSE_URL", "http://localhost:8123").rstrip("/")


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
    resp.raise_for_status()
    text = resp.text
    if not text:
        return []
    return [tuple(line.split("\t")) for line in text.splitlines()]

# scripts/gate0_dump.py — Gate 0: dump all 12 CMC MCP tools with BTC-centric args.
# Raw JSON-RPC responses are saved verbatim to docs/gate0/<tool>.json (evidence,
# including error payloads). tools/list goes to docs/gate0/tools_list.json.
# Run: uv run --env-file .env python scripts/gate0_dump.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import McpClient

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "gate0"

# BTC-centric arguments per tool (BTC CMC id = "1").
# Each entry: (primary_args, simplified_retry_args)
TOOL_ARGS: dict[str, tuple[dict, dict]] = {
    "get_crypto_quotes_latest": ({"id": "1"}, {"id": "1"}),
    "trending_crypto_narratives": ({}, {}),
    "search_crypto_info": ({"prompt": "funding rate", "id": "1"},
                           {"prompt": "bitcoin", "id": "1"}),
    "get_crypto_latest_news": ({"id": "1", "limit": 5}, {"id": "1"}),
    "get_crypto_technical_analysis": ({"id": "1"}, {"id": "1"}),
    "get_crypto_metrics": ({"id": "1"}, {"id": "1"}),
    "get_global_crypto_derivatives_metrics": ({}, {}),
    "search_cryptos": ({"query": "bitcoin", "limit": 5}, {"query": "bitcoin"}),
    "get_global_metrics_latest": ({}, {}),
    "get_upcoming_macro_events": ({}, {}),
    "get_crypto_info": ({"id": "1"}, {"id": "1"}),
    "get_crypto_marketcap_technical_analysis": ({}, {}),
}


def is_error(resp: dict | None) -> bool:
    if resp is None:
        return True
    if "error" in resp:
        return True
    result = resp.get("result", {})
    if isinstance(result, dict) and result.get("isError"):
        return True
    return False


def flatten(obj, prefix="", out=None):
    """Flatten JSON into {path: example_value}; lists indexed as [0] (first element only)."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(obj, list):
        if obj:
            flatten(obj[0], f"{prefix}[0]", out)
        else:
            out[prefix] = []
    else:
        out[prefix] = obj
    return out


def extract_payload(resp: dict):
    """MCP tool results carry JSON-as-string in result.content[*].text — parse if possible."""
    try:
        content = resp["result"]["content"]
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except (json.JSONDecodeError, ValueError):
            return joined
    except (KeyError, TypeError):
        return resp


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = McpClient()
    init = client.initialize()
    print("initialize:", json.dumps(init.get("result", {}).get("serverInfo", {})))

    tools = client.tools_list()
    (OUT_DIR / "tools_list.json").write_text(json.dumps(tools, indent=2))
    print(f"tools/list: {len(tools)} tools -> {OUT_DIR / 'tools_list.json'}")

    listed = {t["name"] for t in tools}
    missing = listed.symmetric_difference(TOOL_ARGS)
    if missing:
        print(f"WARNING: tool set mismatch vs expected 12: {sorted(missing)}")

    inventory: dict[str, dict] = {}
    for name in (t["name"] for t in tools):
        primary, simplified = TOOL_ARGS.get(name, ({}, {}))
        resp = client.call(name, primary)
        if is_error(resp):
            print(f"  {name}: error on primary args {primary}; retrying with {simplified}")
            retry = client.call(name, simplified)
            # keep the retry if it succeeded, else record the error payload as the dump
            resp = retry if not is_error(retry) else (retry or resp or {"error": "no response"})
        (OUT_DIR / f"{name}.json").write_text(json.dumps(resp, indent=2))
        status = "ERROR" if is_error(resp) else "ok"
        print(f"  {name}: {status} -> docs/gate0/{name}.json")
        inventory[name] = flatten(extract_payload(resp))

    # Field-inventory table
    print("\n# Field inventory (flattened paths, first-element examples)")
    for name, fields in inventory.items():
        print(f"\n## {name} ({len(fields)} leaf paths)")
        for path, val in fields.items():
            ex = json.dumps(val, ensure_ascii=False)
            if len(ex) > 100:
                ex = ex[:97] + "..."
            print(f"  {path} = {ex}  ({type(val).__name__})")


if __name__ == "__main__":
    main()

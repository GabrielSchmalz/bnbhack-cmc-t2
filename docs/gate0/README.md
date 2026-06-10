# Gate 0 — live CMC MCP tool dumps (captured 2026-06-10)

Raw JSON-RPC responses from all 12 CoinMarketCap MCP tools, saved as Gate-0
evidence of the live API's field shape; they freeze the distilled classifier's
inputs to live-verified fields (`GATE0-FREEZE.md`). In the five long-form dumps
(news, macro events, search, narratives, crypto info), third-party string
values are truncated to 200 chars + "… [truncated for redistribution hygiene]";
every JSON key and path is preserved exactly. The six dumps the classifier and
`demo/validate_skill.py` cite are byte-for-byte as captured. Regenerate all:
`uv run --env-file .env python scripts/gate0_dump.py`.

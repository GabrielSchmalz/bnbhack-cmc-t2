# scripts/mcp_client.py
import itertools
import json
import os

import requests

URL = "https://mcp.coinmarketcap.com/mcp"

class McpClient:
    def __init__(self, url: str = URL, key: str | None = None):
        self.url = url
        self.key = key or os.environ["CMC_MCP_API_KEY"]
        self.sess = requests.Session()
        self.sess.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-CMC-MCP-API-KEY": self.key,
        })
        self._id = itertools.count(1)
        self._session_id = None

    def _post(self, payload: dict) -> dict | None:
        headers = {}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        r = self.sess.post(self.url, json=payload, headers=headers, timeout=60)
        if sid := r.headers.get("Mcp-Session-Id"):
            self._session_id = sid
        if r.status_code == 202 or not r.text.strip():
            return None
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    msg = json.loads(line[5:].strip())
                    if msg.get("id") is not None:
                        return msg
            return None
        return r.json()

    def initialize(self):
        out = self._post({"jsonrpc": "2.0", "id": next(self._id), "method": "initialize",
                          "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                     "clientInfo": {"name": "bnbhack-t2", "version": "0.1"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return out

    def tools_list(self) -> list[dict]:
        return self._post({"jsonrpc": "2.0", "id": next(self._id),
                           "method": "tools/list"})["result"]["tools"]

    def call(self, name: str, arguments: dict) -> dict:
        return self._post({"jsonrpc": "2.0", "id": next(self._id), "method": "tools/call",
                           "params": {"name": name, "arguments": arguments}})

"""
Integration tests for the Flyk MCP server declared in
plugins/flyk-mcp-plugin/.mcp.json.

These make real HTTP calls to a live server (whatever `.mcp.json` currently
points at — staging or prod) and speak actual MCP JSON-RPC over it: no
mocking. They do NOT need a Claude/Anthropic API key, just network access to
that host.

Run with:

    python3 -m unittest discover -s tests/integration -v

Set FLYK_MCP_SKIP_NETWORK=1 to skip these in an offline/CI environment
instead of failing.
"""
import json
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_CONFIG_PATH = REPO_ROOT / "plugins" / "flyk-mcp-plugin" / ".mcp.json"
TIMEOUT_SECONDS = 10

# Tools the sample commands/skill are written against (plugins/flyk-mcp-plugin/
# skills/flyk-quickstart/SKILL.md). If the live server's tool list drops one
# of these, that plugin content is now describing tools that don't exist.
EXPECTED_TOOL_NAMES = {
    "search_businesses",
    "get_business_detail",
    "get_agent_card",
    "chat_with_business",
    "assess_fit",
    "check_availability",
    "get_quote",
    "book_appointment",
    "switch_business",
}


def _load_server_url() -> str:
    with open(MCP_CONFIG_PATH, encoding="utf-8") as f:
        servers = json.load(f)
    flyk = servers["flyk"]
    assert flyk.get("type") in ("http", "sse"), "expected the flyk server to be HTTP/SSE"
    return flyk["url"]


def _mcp_call(url: str, method: str, params: dict, request_id: int = 1) -> dict:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        content_type = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")

    if "text/event-stream" in content_type:
        # Streamable-HTTP MCP servers may frame the JSON-RPC response as an
        # SSE event instead of a bare body — pull the JSON out of its
        # "data:" line(s) rather than handing the raw SSE frame to
        # json.loads(), which would raise JSONDecodeError on it.
        body = "".join(
            line[len("data:"):].strip()
            for line in body.splitlines()
            if line.startswith("data:")
        )
    return json.loads(body)


@unittest.skipIf(
    os.environ.get("FLYK_MCP_SKIP_NETWORK") == "1",
    "FLYK_MCP_SKIP_NETWORK=1 set — skipping live network calls",
)
class FlykMcpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = _load_server_url()
        try:
            cls.init_response = _mcp_call(
                cls.url,
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "flyk-plugin-tests", "version": "0.0.1"},
                },
            )
        except urllib.error.HTTPError as exc:
            # HTTPError is a subclass of URLError, so it must be caught
            # first and treated as a real failure, not a connectivity skip
            # — an auth requirement (401/403) appearing here is exactly the
            # "open access" regression this suite exists to catch.
            raise AssertionError(
                f"{cls.url} returned HTTP {exc.code} on a request sent with no "
                "auth — this plugin is meant to be open access. If a real auth "
                "requirement was added, that's a deliberate design change, not "
                "a connectivity problem; update this test and the plugin's docs."
            ) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise unittest.SkipTest(f"{cls.url} unreachable: {exc}")

    def test_initialize_handshake_succeeds(self):
        self.assertNotIn("error", self.init_response, self.init_response.get("error"))
        result = self.init_response["result"]
        self.assertIn("protocolVersion", result)
        self.assertIn("serverInfo", result)
        self.assertEqual(result["serverInfo"].get("name"), "flyk")

    def test_no_auth_required(self):
        """This plugin is meant to be open access — the handshake above
        already ran with no Authorization header, so getting a clean result
        (not a 401/403) is itself the assertion."""
        self.assertIn("result", self.init_response)

    def test_tools_list_matches_what_the_plugin_documents(self):
        response = _mcp_call(self.url, "tools/list", {}, request_id=2)
        self.assertNotIn("error", response, response.get("error"))
        tools = response["result"]["tools"]
        self.assertGreater(len(tools), 0)
        names = {t["name"] for t in tools}
        missing = EXPECTED_TOOL_NAMES - names
        self.assertFalse(
            missing,
            f"tools referenced by commands/skill are missing from the live server: {missing}",
        )
        for tool in tools:
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)

    def test_search_businesses_read_call_succeeds(self):
        """A single safe, read-only end-to-end call through the real tool,
        not just the tool listing."""
        response = _mcp_call(
            self.url,
            "tools/call",
            {"name": "search_businesses", "arguments": {"query": "coaching"}},
            request_id=3,
        )
        self.assertNotIn("error", response, response.get("error"))
        self.assertIn("result", response)


if __name__ == "__main__":
    unittest.main()

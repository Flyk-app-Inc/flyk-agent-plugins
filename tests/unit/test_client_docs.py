"""
Unit tests that keep the repo's client-facing install docs in sync with the
things they describe. No network access.

Two kinds of drift are guarded here:

1. **The MCP endpoint URL.** plugins/flyk-mcp-plugin/.mcp.json is the single
   source of truth. Any Markdown that names an MCP endpoint must name that
   one, so an install doc cannot rot when the host flips to production.
   Markdown under docs/superpowers/ is exempt: specs and plans are
   point-in-time records of what was true when they were written.

2. **The ChatGPT instructions blob.** (Added in Task 2 of the plan.)

Run with:

    python3 -m unittest discover -s tests/unit -v
"""
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "flyk-mcp-plugin"
MCP_CONFIG_PATH = PLUGIN_DIR / ".mcp.json"

# Directories whose Markdown is not customer-facing install copy.
EXEMPT_DIRS = (
    REPO_ROOT / "docs" / "superpowers",
    REPO_ROOT / ".git",
    REPO_ROOT / "node_modules",
    REPO_ROOT / ".claude",
    REPO_ROOT / ".superpowers",  # git-ignored scratch, not repo content
)

# An MCP endpoint URL as it appears in prose: inside backticks, inside a
# fenced block, or as a bare/linked URL. The character class stops the match
# at the punctuation Markdown wraps URLs in, so "[x](https://h/mcp)" does not
# swallow the closing paren.
MCP_URL_RE = re.compile(r"""https?://[^\s)\]`"'>]+/mcp\b""")


def find_mcp_urls(text: str) -> list:
    """Every MCP endpoint URL mentioned in a chunk of Markdown, in order."""
    return MCP_URL_RE.findall(text)


class McpUrlHelperTests(unittest.TestCase):
    """The detection helper itself, on synthetic input — so a bug in the
    regex shows up here rather than as a silently-passing repo scan."""

    def test_finds_backticked_and_bare_urls(self):
        text = (
            "Paste `https://example.test/mcp` into the box.\n"
            "Or use https://other.test/mcp instead.\n"
        )
        self.assertEqual(
            find_mcp_urls(text),
            ["https://example.test/mcp", "https://other.test/mcp"],
        )

    def test_does_not_swallow_markdown_punctuation(self):
        self.assertEqual(
            find_mcp_urls("[endpoint](https://example.test/mcp)"),
            ["https://example.test/mcp"],
        )

    def test_ignores_urls_that_are_not_mcp_endpoints(self):
        text = "See https://flyk.app/docs/claude and https://github.com/Flyk-app-Inc/flyk-agent-plugins"
        self.assertEqual(find_mcp_urls(text), [])


def canonical_mcp_url() -> str:
    """The one true endpoint: whatever .mcp.json says today."""
    with open(MCP_CONFIG_PATH, encoding="utf-8") as f:
        servers = json.load(f)
    return servers["flyk"]["url"]


def iter_markdown_files() -> list:
    """Every Markdown file whose URLs are expected to be current."""
    out = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if any(exempt in path.parents for exempt in EXEMPT_DIRS):
            continue
        out.append(path)
    return out


class McpUrlConsistencyTests(unittest.TestCase):
    def test_every_documented_mcp_url_matches_the_manifest(self):
        canonical = canonical_mcp_url()
        for md_path in iter_markdown_files():
            rel = md_path.relative_to(REPO_ROOT)
            for url in find_mcp_urls(md_path.read_text(encoding="utf-8")):
                with self.subTest(doc=str(rel), url=url):
                    self.assertEqual(
                        url,
                        canonical,
                        f"{rel} names {url}, but .mcp.json says {canonical}. "
                        "Update the doc, or update .mcp.json if the host moved.",
                    )

    def test_the_scan_actually_finds_something(self):
        """Without this, renaming the endpoint path would make every check
        above vacuously pass."""
        found = [
            url
            for md_path in iter_markdown_files()
            for url in find_mcp_urls(md_path.read_text(encoding="utf-8"))
        ]
        self.assertTrue(
            found,
            "no Markdown names the MCP endpoint — the URL scan is checking nothing",
        )


if __name__ == "__main__":
    unittest.main()

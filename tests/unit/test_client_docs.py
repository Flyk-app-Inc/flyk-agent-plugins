"""
Unit tests that keep the repo's client-facing install docs in sync with the
things they describe. No network access.

Two kinds of drift are guarded here:

1. **The MCP endpoint URL.** plugins/flyk-mcp-plugin/.mcp.json is the single
   source of truth. Any Markdown that names an MCP endpoint must name that
   one, so an install doc cannot rot when the host flips to production.
   Two kinds of directory are exempt: docs/superpowers/, because specs and
   plans are point-in-time records of what was true when they were written,
   and git-ignored scratch such as .superpowers/, which never ships.

2. **The ChatGPT instructions blob.** ChatGPT has no skill mechanism, so
   plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md carries by hand
   the guidance skills/flyk-quickstart/SKILL.md gives Claude. If SKILL.md
   gains a tool, or moves one between its safe and confirm-required groups,
   the blob has to follow.

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
SKILL_PATH = PLUGIN_DIR / "skills" / "flyk-quickstart" / "SKILL.md"
CHATGPT_DOC_PATH = PLUGIN_DIR / "clients" / "chatgpt-instructions.md"

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


# SKILL.md's "## Tools" section is two top-level bullets, each followed by
# indented per-tool bullets. These substrings identify the two groups.
SAFE_GROUP_MARKER = "Discovery (read, safe to call freely)"
CONFIRM_GROUP_MARKER = "Reaches a real business"

# The line in the ChatGPT blob that opens its confirm-required list.
CONFIRM_MARKER = "Confirm before these"

TOOL_IN_BACKTICKS = re.compile(r"`([a-z][a-z0-9_]*)`")


def parse_skill_tool_groups(text: str) -> tuple:
    """Split SKILL.md's tool list into (safe_to_call, needs_confirmation).

    Derived from the file rather than hardcoded, so adding a tool to
    SKILL.md forces the ChatGPT blob to keep up.
    """
    groups = {"safe": set(), "confirm": set()}
    current = None
    for line in text.splitlines():
        if line.startswith("#"):
            current = None
            continue
        if line.startswith("- "):  # a top-level bullet starts a new group
            if SAFE_GROUP_MARKER in line:
                current = "safe"
            elif CONFIRM_GROUP_MARKER in line:
                current = "confirm"
            else:
                current = None
            continue
        if current and line.strip().startswith("- "):  # indented tool bullet
            match = TOOL_IN_BACKTICKS.search(line)
            if match:
                groups[current].add(match.group(1))
    return groups["safe"], groups["confirm"]


def confirm_section(text: str) -> str:
    """The ChatGPT blob's confirm-required list, from its marker line to the
    end of the fenced block it lives in."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if CONFIRM_MARKER in line:
            start = i
            break
    if start is None:
        return ""
    out = []
    for line in lines[start + 1:]:
        if line.strip().startswith("```") or line.startswith("#"):
            break
        out.append(line)
    return "\n".join(out)


class SkillToolParserTests(unittest.TestCase):
    """The parser, on synthetic input — so a restructured SKILL.md fails
    loudly here instead of silently parsing to empty sets."""

    SAMPLE = (
        "## Tools\n"
        "\n"
        "- **Discovery (read, safe to call freely):**\n"
        "  - `search_businesses` — find providers by query.\n"
        "  - `get_quote` — itemized price estimate.\n"
        "- **Reaches a real business — confirm with the user first:**\n"
        "  - `book_appointment` — sends an actual booking request.\n"
        "\n"
        "## Good practice\n"
        "\n"
        "- Prefer the narrowest tool call, e.g. `get_quote`.\n"
    )

    def test_splits_the_two_groups(self):
        safe, confirm = parse_skill_tool_groups(self.SAMPLE)
        self.assertEqual(safe, {"search_businesses", "get_quote"})
        self.assertEqual(confirm, {"book_appointment"})

    def test_ignores_tools_named_outside_the_tools_section(self):
        """`get_quote` is also mentioned under "Good practice"; that must not
        add a phantom group member."""
        safe, confirm = parse_skill_tool_groups(self.SAMPLE)
        self.assertNotIn("Good", safe | confirm)
        self.assertEqual(len(safe | confirm), 3)


class SkillIsParseableTests(unittest.TestCase):
    def test_real_skill_yields_both_groups(self):
        safe, confirm = parse_skill_tool_groups(SKILL_PATH.read_text(encoding="utf-8"))
        self.assertTrue(safe, "SKILL.md parsed to zero safe tools")
        self.assertTrue(confirm, "SKILL.md parsed to zero confirm-required tools")
        self.assertEqual(
            confirm,
            {"chat_with_business", "book_appointment"},
            "the set of tools that reach a real business changed — the ChatGPT "
            "blob and the plugin docs both need reviewing",
        )
        self.assertFalse(safe & confirm, "a tool is in both groups")


class ChatGptInstructionsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            CHATGPT_DOC_PATH.is_file(), f"missing {CHATGPT_DOC_PATH}"
        )
        self.doc = CHATGPT_DOC_PATH.read_text(encoding="utf-8")
        self.safe, self.confirm = parse_skill_tool_groups(
            SKILL_PATH.read_text(encoding="utf-8")
        )

    def test_mentions_every_tool_the_skill_teaches(self):
        for tool in sorted(self.safe | self.confirm):
            with self.subTest(tool=tool):
                self.assertIn(
                    tool,
                    self.doc,
                    f"SKILL.md teaches {tool} but the ChatGPT instructions never name it",
                )

    def test_has_a_confirm_section(self):
        self.assertTrue(
            confirm_section(self.doc).strip(),
            f"no '{CONFIRM_MARKER}' block found — ChatGPT users would get no "
            "confirm-before-booking guidance at all",
        )

    def test_every_confirm_required_tool_is_in_the_confirm_section(self):
        section = confirm_section(self.doc)
        for tool in sorted(self.confirm):
            with self.subTest(tool=tool):
                self.assertIn(
                    tool,
                    section,
                    f"{tool} reaches a real business but is not listed under "
                    f"'{CONFIRM_MARKER}'",
                )

    def test_no_safe_tool_is_listed_as_confirm_required(self):
        section = confirm_section(self.doc)
        for tool in sorted(self.safe):
            with self.subTest(tool=tool):
                self.assertNotIn(
                    tool,
                    section,
                    f"{tool} is read-only in SKILL.md but the ChatGPT "
                    "instructions put it behind a confirmation prompt",
                )


if __name__ == "__main__":
    unittest.main()

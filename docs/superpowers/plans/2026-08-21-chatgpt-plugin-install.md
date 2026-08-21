# ChatGPT Install Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let ChatGPT users install and safely use the Flyk MCP server, with install docs that cannot drift from the server config or from the plugin's skill.

**Architecture:** ChatGPT has no repo-based marketplace, so this is documentation plus two anti-drift unit tests. `plugins/flyk-mcp-plugin/.mcp.json` stays the single source of truth for the endpoint URL; a new `tests/unit/test_client_docs.py` asserts every Markdown mention of an MCP endpoint matches it, and that a new pasteable ChatGPT instructions file still names every tool `skills/flyk-quickstart/SKILL.md` names — including keeping `chat_with_business` and `book_appointment` in its confirm-required section.

**Tech Stack:** Python 3 standard library only (`unittest`, `re`, `json`, `pathlib`) — this repo has no package manager and no third-party test dependencies. Markdown and JSON for everything else.

**Spec:** [`docs/superpowers/specs/2026-08-21-chatgpt-plugin-install-design.md`](../specs/2026-08-21-chatgpt-plugin-install-design.md)

## Global Constraints

- **Python standard library only.** No `pip install`, no new dependencies. Follow the style of `tests/unit/test_manifests.py`: module-level helpers, `unittest.TestCase` classes, `subTest` for loops.
- **`plugins/flyk-mcp-plugin/.mcp.json` is not modified.** It stays canonical and stays pointed at `https://staging-api.flyk.app/mcp`. Flipping to production is out of scope.
- **The new `clients/` directory stays outside `commands/` and `skills/`.** It must NOT be referenced from `plugin.json` — it is a paste target for humans, not a plugin component. The existing tests glob `commands/*.md` and `skills/*/SKILL.md`; `clients/` must remain invisible to them.
- **No `.github/workflows/` edits.** `discover -s tests/unit` finds new test files automatically, and the ≥95% coverage gate measures only `.github/scripts`, so tests added outside that directory do not affect it.
- **Version goes `1.0.1` → `1.1.0`** in exactly two places: `plugins/flyk-mcp-plugin/.claude-plugin/plugin.json` and the `flyk-mcp-plugin` entry in `.claude-plugin/marketplace.json`. Both must match.
- **Markdown under `docs/superpowers/` is exempt from the URL scan.** Specs and plans are point-in-time records; they must not need rewriting when the host moves.
- **Open access is a hard invariant.** No auth headers, tokens, or `userConfig` anywhere. `tests/unit/test_manifests.py` already enforces this — do not weaken it.
- **Verification commands** (run from the repo root):

  ```bash
  python3 -m unittest discover -s tests/unit -v
  npx --yes markdownlint-cli2 "**/*.md"
  ```

---

### Task 1: MCP URL drift guard

Creates the new test module with its URL helpers, proves the helpers work on synthetic text, then turns them on the whole repo. Pure addition: no docs change, so the suite is green at both ends.

**Files:**

- Create: `tests/unit/test_client_docs.py`

`README.md` is deliberately NOT touched here — every README edit lands together in Task 3, so this task's tests go green and stay green.

**Interfaces:**

- Consumes: nothing from earlier tasks — this is the first task.
- Produces, all in `tests/unit/test_client_docs.py`, relied on by Task 2:
  - Constants `REPO_ROOT: Path`, `PLUGIN_DIR: Path`, `MCP_CONFIG_PATH: Path`
  - `find_mcp_urls(text: str) -> list[str]`
  - `canonical_mcp_url() -> str`
  - `iter_markdown_files() -> list[Path]`

- [ ] **Step 1: Write the URL detection helper and its tests**

Create `tests/unit/test_client_docs.py` with exactly this content. Note it references `find_mcp_urls`, which does not exist yet — that is the failure we want.

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `python3 -m unittest tests.unit.test_client_docs -v`

Expected: 3 tests PASS. (The helper and its tests were written together in Step 1 because this repo keeps helpers in the test module itself — see `load_json` and `parse_frontmatter` in `tests/unit/test_manifests.py`. Step 3 is where the genuinely-failing test comes in.)

- [ ] **Step 3: Add the repo-wide consistency test**

Append to `tests/unit/test_client_docs.py`, immediately before the `if __name__ == "__main__":` block:

```python
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
```

- [ ] **Step 4: Run the tests to verify they still pass**

Run: `python3 -m unittest tests.unit.test_client_docs -v`

Expected: all 5 tests PASS. Three files already name the staging endpoint and all three match `.mcp.json`, so you should see three `subTest` entries under `test_every_documented_mcp_url_matches_the_manifest`:

- `CLAUDE.md`
- `README.md` (the publishing checklist)
- `plugins/flyk-mcp-plugin/README.md`

That is the invariant being locked in before Tasks 3 and 4 rewrite two of those files.

To see the guard actually bite, temporarily change the URL in `plugins/flyk-mcp-plugin/.mcp.json` to `https://example.test/mcp` and re-run: `test_every_documented_mcp_url_matches_the_manifest` should FAIL naming `README.md`. Revert the file afterwards — `.mcp.json` must stay on staging (see Global Constraints).

- [ ] **Step 5: Run the full unit suite and the linter**

Run:

```bash
python3 -m unittest discover -s tests/unit -v
npx --yes markdownlint-cli2 "**/*.md"
```

Expected: all unit tests PASS; `0 error(s)` from the linter.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_client_docs.py
git commit -m "Add a test pinning documented MCP endpoint URLs to .mcp.json"
```

---

### Task 2: ChatGPT instructions blob, kept in sync with the skill

ChatGPT has no skill mechanism, so the confirm-before-booking guidance has to be carried by hand. This task adds the pasteable file and the test that stops it drifting from `SKILL.md`.

**Files:**

- Create: `plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md`
- Modify: `tests/unit/test_client_docs.py` (append)

**Interfaces:**

- Consumes from Task 1: `REPO_ROOT`, `PLUGIN_DIR`, and the module's existing imports (`json`, `re`, `unittest`, `Path`) — all already at the top of `tests/unit/test_client_docs.py`.
- Produces: `parse_skill_tool_groups(text) -> tuple[set, set]` returning `(safe_tools, confirm_tools)`; `confirm_section(text) -> str`. Nothing later depends on these.

- [ ] **Step 1: Write the failing parser and blob tests**

Append to `tests/unit/test_client_docs.py`, immediately before the `if __name__ == "__main__":` block. Also add these two constants next to `MCP_CONFIG_PATH` at the top of the file:

```python
SKILL_PATH = PLUGIN_DIR / "skills" / "flyk-quickstart" / "SKILL.md"
CHATGPT_DOC_PATH = PLUGIN_DIR / "clients" / "chatgpt-instructions.md"
```

Then append:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.unit.test_client_docs -v`

Expected: the four `ChatGptInstructionsTests` FAIL in `setUp` with "missing .../clients/chatgpt-instructions.md". `SkillToolParserTests` and `SkillIsParseableTests` PASS — they only need `SKILL.md`, which already exists.

- [ ] **Step 3: Create the ChatGPT instructions file**

Create `plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md` with exactly this content:

````markdown
# Using Flyk with ChatGPT

ChatGPT connects to the Flyk MCP server as a custom connector — see the [repo README](../../../README.md#chatgpt) for the install steps.

What ChatGPT does **not** get is the `flyk-quickstart` skill that ships with the Claude plugin. That skill is what makes Claude stop and ask before it messages or books with a real business. ChatGPT has no equivalent mechanism, so ChatGPT will happily call those tools on its own.

Pasting the block below into a ChatGPT **Project → Instructions** (or your Custom Instructions) restores that guidance. It is worth doing before you use Flyk for anything that reaches a provider.

## The block to paste

```text
When I ask you to find, compare, or book a service provider, use the Flyk MCP tools rather than guessing at names, prices, or availability. If the tools are unavailable, say so plainly — never invent Flyk data. When summarizing results, keep it scannable: provider name, price or fit score, and modality, as bullets rather than raw JSON.

Safe to call freely — these only read:
- search_businesses — find providers by query, category, city, state, budget, or modality. Start here.
- get_business_detail — full profile for one provider: services, pricing, credentials, hours.
- get_agent_card — structured profile for one provider: identity, matchability, reputation and trust tier.
- assess_fit — score a provider against my stated needs, budget, and preferences.
- check_availability — open time slots for a provider.
- get_quote — itemized price estimate for a provider's service.
- switch_business — pivot to alternatives when a provider isn't a fit; pass a reason instead of re-searching blind.

Confirm before these — they reach a real business:
- chat_with_business — sends a message to the provider's AI agent. Tell me afterwards whether the provider's own agent or Flyk's fallback replied.
- book_appointment — sends an actual booking request.
Before calling either one, show me the provider, the service, the time, and any contact details you are about to send, and wait for a clear yes from me. Do not chain them off a previous approval — ask each time.
```
````

Ordering matters: everything after the `Confirm before these` line is what `confirm_section()` reads, and `test_no_safe_tool_is_listed_as_confirm_required` asserts no read-only tool is named in it. Keep general guidance above the confirm list, not below it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.unit.test_client_docs -v`

Expected: everything PASSES except `test_the_scan_actually_finds_something` from Task 1, which still fails until Task 3 puts the endpoint in the README.

- [ ] **Step 5: Confirm the new directory stays invisible to the plugin-component tests**

Run: `python3 -m unittest tests.unit.test_manifests -v`

Expected: all PASS. `clients/` is not `commands/` or `skills/`, so the frontmatter tests must not pick it up. If any of them now fail, the file landed in the wrong directory.

Run: `npx --yes markdownlint-cli2 "**/*.md"` — expected `0 error(s)`.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_client_docs.py plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md
git commit -m "Add pasteable ChatGPT instructions, kept in sync with flyk-quickstart"
```

---

### Task 3: Restructure the root README install section

Turns the Claude-only install instructions into a Claude path plus a generic "any MCP client" path, with ChatGPT as the worked example. This is what makes Task 1's `test_the_scan_actually_finds_something` pass.

**Files:**

- Modify: `README.md:36-54` (the whole `## Installing (customer instructions)` section)
- Modify: `README.md:73` (the publishing checklist's first bullet)

**Interfaces:**

- Consumes: the file created in Task 2, linked from the ChatGPT subsection.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Replace the install section**

In `README.md`, replace the whole `## Installing (customer instructions)` section — from that heading down to (and including) the last line before the `## Pull request checks` heading — with:

````markdown
## Installing (customer instructions)

No account, sign-up, or API key is needed on any client — the Flyk MCP server is open access.

### Claude — through this marketplace

**Claude Desktop:**

1. Open Claude Desktop and click the **+** button next to the message box.
2. Select **Plugins** → **Add marketplace**.
3. Paste this repo's URL: `https://github.com/Flyk-app-Inc/flyk-agent-plugins`
4. Find **Flyk** in the marketplace list and click **Install**.

That's it — it works right away. Open a new chat and ask Claude to find or book a provider to try it out.

**Claude Code:**

```bash
/plugin marketplace add Flyk-app-Inc/flyk-agent-plugins
/plugin install flyk-mcp-plugin@flyk-marketplace
```

Then run `/flyk-mcp-plugin:setup` any time to confirm the connection.

Installing this way also brings the plugin's commands and the `flyk-quickstart` skill, which is what makes Claude confirm with you before it messages or books with a real business.

### Any other MCP client — paste the URL

Other clients have no marketplace to install from; they take the server URL directly. The Flyk MCP endpoint is:

```text
https://staging-api.flyk.app/mcp
```

It speaks Streamable HTTP and needs no authentication headers.

#### ChatGPT

ChatGPT calls these custom connectors, and they live behind developer mode:

1. In ChatGPT on the web, open **Settings → Apps → Advanced settings** and turn on **Developer mode**.
2. Go to the **Plugins** page, click **+**, and paste the URL above.

Two things worth knowing before you start:

- Custom connectors require a paid plan — Plus, Pro, Business, Enterprise, or Education.
- ChatGPT shows a warning that custom connectors run third-party code on your behalf. That warning is standard for every custom connector and is not specific to Flyk.

OpenAI moves these settings around from time to time. If the steps don't match what you see, [OpenAI's developer mode article](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt) is the current authority.

**One important difference from Claude:** ChatGPT has no way to install the `flyk-quickstart` skill, so it will not automatically ask before messaging or booking with a real provider. [`plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md`](plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md) has a short block to paste into a ChatGPT Project's instructions that restores that guidance. Do that before you use Flyk to contact anyone.

#### Other clients

Any other MCP client — Cursor, VS Code, and similar — takes the same URL wherever it registers remote MCP servers. The same caveat applies: only the Claude plugin ships the skill, so on other clients the ChatGPT instructions block above is worth adapting.
````

- [ ] **Step 2: Reword the publishing checklist so it stops duplicating the URL**

Still in `README.md`, replace this line:

```markdown
- [ ] Point `.mcp.json`'s `url` at the production MCP endpoint before shipping (currently `https://staging-api.flyk.app/mcp`, staging).
```

with these two lines:

```markdown
- [ ] Point [`plugins/flyk-mcp-plugin/.mcp.json`](plugins/flyk-mcp-plugin/.mcp.json)'s `url` at the production MCP endpoint before shipping — it is still on staging. Every install doc is checked against that file by [`tests/unit/test_client_docs.py`](tests/unit/test_client_docs.py), so the docs have to move in the same commit.
- [ ] Tell ChatGPT users to remove and re-add their custom connector after that switch. They pasted the URL into their own ChatGPT settings, so unlike a Claude plugin update we cannot move it for them — it needs a customer-facing announcement, not a silent change.
```

Two reasons this belongs here: the checklist must describe the file rather than repeat the URL, or it becomes a second drift source that fails the test at the production flip; and the new second bullet records the risk the spec flagged, that a pasted ChatGPT connector is frozen in each user's own settings.

- [ ] **Step 3: Run the unit suite to verify the URL tests now pass**

Run: `python3 -m unittest discover -s tests/unit -v`

Expected: **all tests PASS**, including both of Task 1's URL tests. The README now names the endpoint exactly once, and it matches `.mcp.json`.

If `test_every_documented_mcp_url_matches_the_manifest` fails, the URL typed into the README does not byte-match `.mcp.json` — copy it from that file rather than retyping it.

- [ ] **Step 4: Lint the Markdown**

Run: `npx --yes markdownlint-cli2 "**/*.md"`

Expected: `0 error(s)`.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "Restructure install docs: Claude marketplace vs. any MCP client, with ChatGPT worked through"
```

---

### Task 4: Plugin README pointer, version bump, and full verification

Finishes the change: the plugin's own README learns about `clients/`, the version moves so CI's release-discipline check passes, and every gate a PR would face gets run.

**Files:**

- Modify: `plugins/flyk-mcp-plugin/README.md` (components table and Install section)
- Modify: `plugins/flyk-mcp-plugin/.claude-plugin/plugin.json` (`version`)
- Modify: `.claude-plugin/marketplace.json` (the `flyk-mcp-plugin` entry's `version`)

**Interfaces:**

- Consumes: the file created in Task 2.
- Produces: nothing — this is the last task.

- [ ] **Step 1: Add a row to the plugin README's components table**

In `plugins/flyk-mcp-plugin/README.md`, add this row to the end of the `What's included` table, after the `flyk-quickstart` skill row:

```markdown
| ChatGPT instructions | [`clients/chatgpt-instructions.md`](clients/chatgpt-instructions.md) | Not a plugin component — a block ChatGPT users paste into a Project's instructions, since ChatGPT can't install the skill. Carries the same confirm-before-booking guidance. |
```

- [ ] **Step 2: Add a section on using the server outside Claude**

In the same file, append this section at the end:

```markdown
## Using the Flyk server outside Claude

The MCP server itself is client-agnostic — any MCP client can connect to the URL in [`.mcp.json`](.mcp.json). What doesn't travel is everything else in this directory: `commands/` and `skills/` are Claude plugin features with no equivalent elsewhere.

That matters most for the guardrail. `flyk-quickstart` is what makes Claude confirm before `chat_with_business` or `book_appointment` reaches a real business; a client without it calls those tools unprompted. [`clients/chatgpt-instructions.md`](clients/chatgpt-instructions.md) is the hand-carried substitute for ChatGPT, and `tests/unit/test_client_docs.py` fails if it drifts from the skill.

See the [repo README](../../README.md#any-other-mcp-client--paste-the-url) for per-client install steps.
```

- [ ] **Step 3: Bump both version fields to 1.1.0**

In `plugins/flyk-mcp-plugin/.claude-plugin/plugin.json`, change `"version": "1.0.1"` to `"version": "1.1.0"`.

In `.claude-plugin/marketplace.json`, change the `flyk-mcp-plugin` entry's `"version": "1.0.1"` to `"version": "1.1.0"`.

- [ ] **Step 4: Run every check a PR would face**

Run each and confirm the expected result:

```bash
python3 -m unittest discover -s tests/unit -v
```

Expected: all PASS, zero failures, zero errors.

```bash
npx --yes markdownlint-cli2 "**/*.md"
```

Expected: `0 error(s)`.

```bash
bad=0; while IFS= read -r -d '' f; do python3 -m json.tool "$f" > /dev/null || bad=1; done < <(find . -name "*.json" -not -path "./.git/*" -print0); echo "bad JSON found: $bad"
```

Expected: `bad JSON found: 0`.

```bash
python3 .github/scripts/check_version_bump.py main HEAD
```

Expected: passes — plugin files changed and `plugin.json`'s version went up.

```bash
FLYK_MCP_SKIP_NETWORK=1 python3 -m unittest discover -s tests/integration -v
```

Expected: skipped, not failed. Drop the env var to actually hit the live staging server if you have network access; the tool list it returns is what both `SKILL.md` and the new ChatGPT block describe.

- [ ] **Step 5: Verify the two version fields agree**

Run:

```bash
python3 -c "import json; p=json.load(open('plugins/flyk-mcp-plugin/.claude-plugin/plugin.json'))['version']; m=[e for e in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if e['name']=='flyk-mcp-plugin'][0]['version']; print(p, m); assert p==m, 'version mismatch'"
```

Expected: prints `1.1.0 1.1.0` with no assertion error.

- [ ] **Step 6: Commit**

```bash
git add plugins/flyk-mcp-plugin/README.md plugins/flyk-mcp-plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "Document the ChatGPT client path in the plugin README; bump to 1.1.0"
```

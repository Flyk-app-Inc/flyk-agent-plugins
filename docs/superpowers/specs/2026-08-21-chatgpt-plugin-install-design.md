# ChatGPT install support for the Flyk MCP plugin

**Date:** 2026-08-21
**Status:** Approved, ready for implementation planning

## Context

This repo is a Claude plugin marketplace: `.claude-plugin/marketplace.json`
lists `plugins/flyk-mcp-plugin`, which bundles the Flyk MCP server plus two
slash commands and the `flyk-quickstart` skill. Customers install it with
`/plugin marketplace add` (Claude Code) or the Plugins UI (Claude Desktop).

The repo has already been renamed from a Claude-specific name to
`flyk-agent-plugins`, but its contents and docs are still Claude-shaped. The
request is to let ChatGPT users install the same Flyk MCP server.

### What ChatGPT actually supports

There is **no repo-based marketplace for ChatGPT** — nothing analogous to
`/plugin marketplace add <github-repo>`. The old ChatGPT plugin format
(`ai-plugin.json` + an OpenAPI manifest) is long deprecated. Two paths exist:

1. **Custom connector via developer mode.** The user enables developer mode in
   ChatGPT settings and pastes a remote MCP endpoint URL. Works today against
   the Flyk server exactly as it stands — Streamable HTTP, no auth. Requires a
   paid plan (Plus, Pro, Business, Enterprise, or Edu). **No repo artifact is
   involved; this is purely a documentation problem.**
2. **App directory submission (Apps SDK).** A reviewed public listing. Requires
   identity verification in the OpenAI Platform dashboard, a domain-verification
   token hosted at `/.well-known/openai-apps` on the same domain that serves the
   MCP endpoint, a content security policy, polished tool definitions, and a
   demo account if auth is ever added.

Path 2 is largely work in the Flyk API repo (which serves the MCP endpoint and
would host the verification token), not this one. It is explicitly out of scope
here — see [Non-goals](#non-goals).

References:

- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
- [App submission guidelines — Apps SDK](https://developers.openai.com/apps-sdk/app-submission-guidelines)

### The parity gap

The plugin's companion components have **no ChatGPT equivalent**. ChatGPT has
no skill mechanism and no slash commands; the MCP server's own tool
descriptions do all the teaching.

This matters for more than convenience. `skills/flyk-quickstart/SKILL.md` is
what makes Claude confirm with the user before calling `chat_with_business` or
`book_appointment` — both of which reach a real business. A ChatGPT user gets
the raw tool surface with that guardrail absent.

## Goals

1. A ChatGPT user can install and use the Flyk MCP server, with instructions
   that are accurate and easy to follow.
2. The MCP endpoint URL has exactly one source of truth, enforced by a test, so
   a new install doc cannot rot when the host changes.
3. The confirm-before-side-effect guidance reaches ChatGPT users in the only
   form this repo can deliver, and cannot silently drift from `SKILL.md`.
4. The repo's install docs stop being Claude-shaped, so the next MCP client
   costs a paragraph rather than a restructure.

## Non-goals

- **Apps SDK / app directory submission.** Needs OpenAI account verification and
  a `/.well-known/openai-apps` token on the MCP host — the Flyk API repo's job.
- **Server-side changes.** Folding confirmation language into the MCP server's
  own tool descriptions (which every client sees) is the durable fix for the
  parity gap, but the server lives in another repo.
- **Switching the endpoint to production.** `.mcp.json` continues to point at
  staging; the existing publishing checklist governs that flip.
- **Per-client documentation pages.** A `docs/install/` directory is more
  structure than a few paragraphs justify today.

## Design

### 1. Canonical URL and drift enforcement

`plugins/flyk-mcp-plugin/.mcp.json`'s `flyk.url` remains the single source of
truth. It already is one in practice: `tests/integration/test_mcp_server.py`
reads the URL from that file rather than hardcoding it.

A new unit test scans the repo's Markdown for MCP endpoint URLs and asserts
every occurrence equals that value.

- **Detection:** this regex over each file's text:

  ```text
  https?://[^\s)\]`"'>]+/mcp\b
  ```

- **Scope:** every `*.md` in the repo, **excluding `docs/superpowers/`**.
  Design specs — including this one — are point-in-time records of what was
  true when written, and must not be rewritten when the host flips.
- **Assertion:** each match equals `.mcp.json`'s `flyk.url`.

This has one immediate consequence: the root README's publishing checklist
currently hardcodes the staging URL in prose. That line gets reworded to point
at the file instead of repeating the URL, so the checklist is not itself a
drift source.

### 2. Restructured install docs (root `README.md`)

The `Installing (customer instructions)` section becomes two paths:

**Claude Desktop / Claude Code** — the existing marketplace instructions,
unchanged in substance.

**Any MCP client — paste the URL** — the endpoint stated once, with its
transport (Streamable HTTP) and the fact that it needs no auth. ChatGPT is the
worked example:

1. Settings → Apps → Advanced settings → enable **Developer mode**.
2. On the Plugins page, click **+** and paste the Flyk MCP URL.

Two caveats belong in the text because they are what actually trips people up:

- Custom connectors need a paid plan (Plus, Pro, Business, Enterprise, or Edu).
- ChatGPT shows a warning that custom connectors run third-party code. That is
  expected and not a problem specific to Flyk.

OpenAI's settings labels shift over time, so the steps link to OpenAI's own
help article rather than standing alone as the authority.

Other clients get one sentence — same URL, added wherever that client registers
remote MCP servers — rather than a table of UI paths this repo cannot verify or
keep current.

### 3. Pasteable ChatGPT instructions

New file: `plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md`.

It is a paste target, not a plugin component. `clients/` deliberately sits
outside `commands/` and `skills/`, so the existing frontmatter tests
(which glob `commands/*.md` and `skills/*/SKILL.md`) correctly ignore it, and
`plugin.json` does not reference it.

The file contains a short explanation plus one fenced block the user copies
into a ChatGPT Project's custom instructions. The block is condensed from
`SKILL.md` and covers:

- The discovery tools, safe to call freely: `search_businesses`,
  `get_business_detail`, `get_agent_card`, `assess_fit`, `check_availability`,
  `get_quote`, `switch_business`.
- The two tools that reach a real business and require an explicit yes first:
  `chat_with_business` and `book_appointment` — with the same instruction
  `SKILL.md` gives Claude, to summarize provider, service, time, and contact
  details before calling.
- Never fabricate Flyk data if the tools are unavailable.

This is opt-in and a user can skip it. It is nonetheless the only lever this
repo has; the durable fix is server-side and is recorded under Non-goals.

### 4. Anti-drift between the blob and `SKILL.md`

The same new test file derives the expected tool sets from `SKILL.md` rather
than hardcoding them.

`SKILL.md`'s `## Tools` section has exactly two top-level bullets, each
followed by indented tool bullets:

- `- **Discovery (read, safe to call freely):**`
- `- **Reaches a real business — confirm with the user first:**`

**Parsing rule:** locate each top-level bullet by its leading text, then collect
the `` `tool_name` `` from each indented list item that follows, stopping at the
next top-level list item or the next heading.

**Assertions:**

1. Both groups parse to non-empty sets (guards against `SKILL.md` being
   restructured such that the parser silently matches nothing).
2. Every tool in either group is mentioned somewhere in
   `chatgpt-instructions.md`.
3. Each confirm-required tool appears in the blob's confirmation section
   specifically, not merely somewhere in the file.

If `SKILL.md` gains a tool or moves one between groups, the blob must follow.

### 5. Version bump

`plugins/flyk-mcp-plugin/.claude-plugin/plugin.json` and the matching entry in
`.claude-plugin/marketplace.json` both go `1.0.1` → `1.1.0`. Plugin files change
in this work, so `.github/scripts/check_version_bump.py` requires it; the two
files are bumped together to keep them consistent.

## Files touched

| File | Change |
| --- | --- |
| `plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md` | New — pasteable ChatGPT project instructions |
| `tests/unit/test_client_docs.py` | New — URL drift test + blob/`SKILL.md` drift test |
| `README.md` | Restructured install section; publishing checklist reworded and extended |
| `plugins/flyk-mcp-plugin/README.md` | Pointer to `clients/chatgpt-instructions.md`; row in the components table |
| `plugins/flyk-mcp-plugin/.claude-plugin/plugin.json` | `version` → `1.1.0` |
| `.claude-plugin/marketplace.json` | Entry `version` → `1.1.0` |

Explicitly **not** touched:

- `plugins/flyk-mcp-plugin/.mcp.json` — stays canonical, stays on staging.
- `.github/workflows/*` — `discover -s tests/unit` picks up the new test file
  automatically, and the ≥95% coverage gate measures only `.github/scripts`, so
  new tests outside that directory do not affect it.

## Testing

The new tests are static and offline, so they belong in the unit layer.

```bash
python3 -m unittest discover -s tests/unit -v
npx --yes markdownlint-cli2 "**/*.md"
bad=0; while IFS= read -r -d '' f; do python3 -m json.tool "$f" > /dev/null || bad=1; done < <(find . -name "*.json" -not -path "./.git/*" -print0); echo "bad JSON found: $bad"
python3 .github/scripts/check_version_bump.py main HEAD
```

The integration layer is unchanged: the ChatGPT path uses the same endpoint and
the same tools, so `tests/integration/test_mcp_server.py` already covers whether
the server ChatGPT connects to is alive and exposes the expected tools.

No new eval cases. Evals run Claude against the plugin; the ChatGPT blob is
never in Claude's context, so an eval cannot exercise it.

## Risks and open items

**Customers will paste a staging URL.** The docs will hand ChatGPT users
`https://staging-api.flyk.app/mcp`. The Claude path has the same exposure today,
but the failure mode is worse for ChatGPT: a plugin version bump can move the
URL for every Claude user at once, whereas a pasted ChatGPT connector is frozen
in each user's own settings and will simply stop working at the production flip,
with no update path we control.

Mitigation: add a line to the publishing checklist stating that ChatGPT users
must remove and re-add the connector after the production switch, and that this
needs a customer-facing announcement rather than a silent change. Pointing
ChatGPT at production ahead of Claude was considered and rejected — two
different endpoints in one repo is a worse drift problem than the one being
solved.

**OpenAI's UI labels drift.** Developer mode's location in settings has moved
before. Mitigated by linking OpenAI's help article as the authority and keeping
our step list short.

**The blob is opt-in.** A ChatGPT user who ignores it gets the tool surface with
no confirmation guidance. Genuinely unfixable from this repo; the server-side
fix under Non-goals is the real answer and should be raised with whoever owns
the Flyk MCP server.

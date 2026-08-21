# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude plugin marketplace for Flyk: `.claude-plugin/marketplace.json` lists a single plugin, `plugins/flyk-mcp-plugin`, which bundles the Flyk MCP server plus companion slash commands and a skill so customers can install it into Claude Desktop or Claude Code without hand-editing `claude_desktop_config.json`. There is no build step, package manager, or application code here — everything is declarative JSON/Markdown consumed by Claude's plugin system, tested with dependency-free Python (stdlib only).

## Commands

```bash
# Unit tests — manifests/frontmatter well-formed, no network, no API key
python3 -m unittest discover -s tests/unit -v

# Integration tests — real calls to the live MCP server in .mcp.json
python3 -m unittest discover -s tests/integration -v
# ...or skip them offline instead of failing:
FLYK_MCP_SKIP_NETWORK=1 python3 -m unittest discover -s tests/integration -v

# Run a single test
python3 -m unittest tests.unit.test_manifests.PluginManifestTests.test_plugin_is_open_access_no_user_config -v

# Eval — Claude actually driving the plugin's commands/skill against the live server.
# Needs the `claude` CLI with `plugin eval` enabled (early access, org-level flag) and ANTHROPIC_API_KEY.
claude plugin eval ./plugins/flyk-mcp-plugin --allow-tools mcp__flyk__search_businesses mcp__flyk__get_business_detail mcp__flyk__get_agent_card mcp__flyk__chat_with_business mcp__flyk__assess_fit mcp__flyk__check_availability mcp__flyk__get_quote mcp__flyk__book_appointment mcp__flyk__switch_business --verbose --json tests-results.json

# JSON validity (mirrors pr-checks.yml's json-validate job — note plain
# `find -exec` doesn't propagate a failing exec's exit status, so this loop
# tracks it explicitly instead)
bad=0; while IFS= read -r -d '' f; do python3 -m json.tool "$f" > /dev/null || bad=1; done < <(find . -name "*.json" -not -path "./.git/*" -print0); echo "bad JSON found: $bad"

# Markdown lint (config: .markdownlint-cli2.jsonc)
npx --yes markdownlint-cli2 "**/*.md"

# Version-bump enforcement a PR would face (compares a plugin's version between two refs)
python3 .github/scripts/check_version_bump.py <base-ref> <head-ref>
```

## Architecture

**Manifest chain:** `.claude-plugin/marketplace.json` lists plugins by `name` + local `source` path. Each entry's `name` must match the `name` in that plugin's own `.claude-plugin/plugin.json` (checked by `tests/unit/test_manifests.py`). `plugin.json` in turn declares where its components live — `commands`, `skills`, `mcpServers` — as paths relative to the plugin directory; nothing is auto-discovered by convention here, so adding a component means wiring its path into `plugin.json` too.

**MCP server:** `plugins/flyk-mcp-plugin/.mcp.json` declares one remote HTTP server (`flyk`), currently pointed at `https://staging-api.flyk.app/mcp`. It is **deliberately open access — no `userConfig`, no auth header**. This is enforced as a regression test (`test_plugin_is_open_access_no_user_config`) and echoed in an eval case (`evals/setup-open-access`) — if you're tempted to add an API key requirement back, both will need deliberate updates, not just the manifest.

**Commands and skill:** `commands/setup.md` and `commands/find.md` are slash-command prompts (YAML frontmatter with `description`, optional `argument-hint`; body is the prompt sent to Claude). `skills/flyk-quickstart/SKILL.md` teaches Claude the full Flyk tool surface (search/detail/fit/availability/quote — safe to call freely — vs. `chat_with_business`/`book_appointment`, which reach a real business and require explicit user confirmation first). The skill's frontmatter `name` must equal its parent directory name (also unit-tested).

**Three-layer testing**, deliberately separate because each catches something the others can't (see `tests/README.md` for the full rationale):

1. **Unit** (`tests/unit/`) — static correctness of manifests/frontmatter against this repo alone.
2. **Integration** (`tests/integration/`) — the *real* live MCP server still answers and still exposes the tools the commands/skill assume exist; drift here means the plugin's docs/skill are describing tools that no longer match reality.
3. **Eval** (`plugins/flyk-mcp-plugin/evals/`) — whether Claude, actually running the skill/commands against the real server, *behaves* correctly (searches before recommending, confirms before booking/messaging, never claims an API key is needed). Each case is a directory with `prompt.md` (the scenario) plus one or more `graders/*.md` (pass/fail criteria: `type: tool_used`, `type: regex`, or `type: llm`). This is Claude Code's `plugin eval` feature — early access, undocumented publicly as of this writing, so treat its exact file schema as best-effort and cross-check `claude plugin eval --help` before extending it.

**CI (`.github/workflows/`):** `test.yml` runs the unit layer on every push/PR and the integration layer only on manual `workflow_dispatch` (kept off automatic PR runs so a flaky third-party staging host can't block merges). `pr-checks.yml` is separate — repo/release hygiene rather than test coverage — and gates JSON validity, markdown lint, a `.github/scripts/check_version_bump.py` check (fails if a plugin's files changed but its `plugin.json` `version` wasn't bumped or was lowered), and a gitleaks secret scan. Neither workflow is wired up as a *required* GitHub branch-protection check yet — see the "Pull request checks" section of the root README.

**Naming rules enforced by tests:** marketplace and plugin `name` fields must be kebab-case and must match across `marketplace.json` and `plugin.json`.

**Before shipping to real customers:** `.mcp.json`'s `url` still points at the staging host (`staging-api.flyk.app`), not production — see the "Publishing checklist" in the root `README.md`.

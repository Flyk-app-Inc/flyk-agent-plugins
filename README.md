# flyk-ai-tool-skills

Claude plugin marketplace for Flyk. Lets customers install the **Flyk MCP server** (plus companion commands and a skill) straight into Claude Desktop or Claude Code — no manual `claude_desktop_config.json` editing required.

## Repo layout

```text
.claude-plugin/
  marketplace.json          # marketplace manifest — lists the plugins below
plugins/
  flyk-mcp-plugin/
    .claude-plugin/
      plugin.json            # plugin manifest — declares mcp server, commands, skill, settings
    .mcp.json                # the Flyk MCP server config (remote HTTP, open — no auth)
    commands/
      setup.md               # /flyk-mcp-plugin:setup — check connection, fix instructions
      find.md                # /flyk-mcp-plugin:find  — search, evaluate, and book a provider
    skills/
      flyk-quickstart/
        SKILL.md              # tells Claude when/how to use the Flyk tools
    README.md                 # plugin-specific docs
```

See [`plugins/flyk-mcp-plugin/README.md`](plugins/flyk-mcp-plugin/README.md) for what the plugin does.

## Testing

Three layers — see [`tests/README.md`](tests/README.md) for the full breakdown:

- **Unit** (`tests/unit/`) — manifests/frontmatter are well-formed, no network. `python3 -m unittest discover -s tests/unit -v`
- **Integration** (`tests/integration/`) — the real MCP server actually answers and still has the tools the plugin assumes. `python3 -m unittest discover -s tests/integration -v`
- **Eval** (`plugins/flyk-mcp-plugin/evals/`) — Claude, given the real plugin, behaves correctly (searches before recommending, confirms before booking, never mentions an API key). `claude plugin eval ./plugins/flyk-mcp-plugin`

CI runs on every PR: [`test.yml`](.github/workflows/test.yml) runs the unit layer, and [`pr-checks.yml`](.github/workflows/pr-checks.yml) gates JSON validity, markdown lint, a bumped plugin version, and a secret scan — see [Pull request checks](#pull-request-checks) below.

## Installing (customer instructions)

**Claude Desktop:** click **+** → **Plugins** → **Add marketplace**, paste this repo's URL, then install **Flyk** from the list. That's it — no account or API key needed, it works right away.

**Claude Code:**

```bash
/plugin marketplace add Flyk-app-Inc/flyk-ai-tool-skills
/plugin install flyk-mcp-plugin@flyk-marketplace
```

Then run `/flyk-mcp-plugin:setup` any time to confirm the connection.

## Pull request checks

[`.github/workflows/pr-checks.yml`](.github/workflows/pr-checks.yml) runs on every PR and reports on:

| Check | What it catches |
| --- | --- |
| `json-validate` | Any `.json` file that doesn't parse |
| `markdown-lint` | Malformed markdown in commands/skills/docs ([`.markdownlint-cli2.jsonc`](.markdownlint-cli2.jsonc) config) |
| `version-bump-check` | A plugin's files changed but `plugin.json`'s `version` wasn't bumped (or was lowered) — see [`.github/scripts/check_version_bump.py`](.github/scripts/check_version_bump.py) |
| `secret-scan` | Accidentally committed credentials, via [gitleaks](https://github.com/gitleaks/gitleaks) |

These are recommendations, not automatically enforced — turn them into required checks under **Settings → Branches → Branch protection rules** for `main` if you want PRs blocked from merging until they pass.

## Publishing checklist (for us)

- [ ] Point `.mcp.json`'s `url` at the production MCP endpoint before shipping (currently `https://staging-api.flyk.app/mcp`, staging).
- [ ] Keep `version` in `plugin.json` bumped on every release — customers on a pinned version won't get updates otherwise.
- [ ] Repo must stay public (or customers need repo access) since `/plugin marketplace add` clones it directly.
- [ ] Consider a `renames` entry in `marketplace.json` if we ever rename `flyk-mcp-plugin`, so existing installs migrate cleanly.

## Reference

- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- [`plugins/flyk-mcp-plugin/.claude-plugin/plugin.json`](plugins/flyk-mcp-plugin/.claude-plugin/plugin.json)

# flyk-agent-plugins

Claude plugin marketplace for Flyk. Lets customers install the **Flyk MCP server** (plus companion commands and a skill) into Claude Desktop or Claude Code via this marketplace, or point any other MCP client straight at the server URL — no manual `claude_desktop_config.json` editing required.

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
    clients/
      chatgpt-instructions.md # paste-in guidance for ChatGPT, which can't install the skill
    README.md                 # plugin-specific docs
```

See [`plugins/flyk-mcp-plugin/README.md`](plugins/flyk-mcp-plugin/README.md) for what the plugin does.

## Testing

Three layers — see [`tests/README.md`](tests/README.md) for the full breakdown:

- **Unit** (`tests/unit/`) — manifests/frontmatter are well-formed, no network. `python3 -m unittest discover -s tests/unit -v`
- **Integration** (`tests/integration/`) — the real MCP server actually answers and still has the tools the plugin assumes. `python3 -m unittest discover -s tests/integration -v`
- **Eval** (`plugins/flyk-mcp-plugin/evals/`) — Claude, given the real plugin, behaves correctly (searches before recommending, confirms before booking, never mentions an API key). `claude plugin eval ./plugins/flyk-mcp-plugin`

CI runs on every PR: [`test.yml`](.github/workflows/test.yml) runs the unit layer and a coverage gate (unit tests must cover ≥95% of [`.github/scripts`](.github/scripts), the repo's only actual application code — the report is posted as a PR comment and in the job summary), and [`pr-checks.yml`](.github/workflows/pr-checks.yml) gates JSON validity, markdown lint, a bumped plugin version, and a secret scan — see [Pull request checks](#pull-request-checks) below.

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

This is currently a staging host and will change before general availability; if you've added it as a custom connector, you'll need to remove and re-add it once that happens.

It speaks Streamable HTTP and needs no authentication headers.

#### ChatGPT

ChatGPT calls these custom connectors, and they live behind developer mode:

1. In ChatGPT on the web, open **Settings → Apps → Advanced settings** and turn on **Developer mode**.
2. Go to the **Plugins** page, click **+**, and paste the URL above.

Two things worth knowing before you start:

- Custom connectors require a paid plan — Plus, Pro, Business, Enterprise, or Education.
- ChatGPT shows a warning about connecting unverified third-party connectors. That warning is standard for every custom connector and is not specific to Flyk.

OpenAI moves these settings around from time to time. If the steps don't match what you see, [OpenAI's developer mode article](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt) is the current authority.

**One important difference from Claude:** ChatGPT has no way to install the `flyk-quickstart` skill, so it will not automatically ask before messaging or booking with a real provider. [`plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md`](plugins/flyk-mcp-plugin/clients/chatgpt-instructions.md) has a short block to paste into a ChatGPT Project's instructions that restores that guidance. Do that before you use Flyk to contact anyone.

#### Other clients

Any other MCP client — Cursor, VS Code, and similar — takes the same URL wherever it registers remote MCP servers. The same caveat applies: only the Claude plugin ships the skill, so on other clients the ChatGPT instructions block above is worth adapting.

## Pull request checks

[`.github/workflows/pr-checks.yml`](.github/workflows/pr-checks.yml) runs on every PR and reports on:

| Check | What it catches |
| --- | --- |
| `json-validate` | Any `.json` file that doesn't parse |
| `markdown-lint` | Malformed markdown in commands/skills/docs ([`.markdownlint-cli2.jsonc`](.markdownlint-cli2.jsonc) config) |
| `version-bump-check` | A plugin's files changed but `plugin.json`'s `version` wasn't bumped (or was lowered) — see [`.github/scripts/check_version_bump.py`](.github/scripts/check_version_bump.py) |
| `secret-scan` | Accidentally committed credentials, via [gitleaks](https://github.com/gitleaks/gitleaks) |

[`.github/workflows/test.yml`](.github/workflows/test.yml)'s `coverage` job adds one more: unit-test coverage of [`.github/scripts`](.github/scripts) must stay ≥95% (`coverage report --fail-under=95`), with the report posted as a sticky PR comment and in the job summary — see [`tests/README.md`](tests/README.md#coverage-gate).

These are recommendations, not automatically enforced — turn them into required checks under **Settings → Branches → Branch protection rules** for `main` if you want PRs blocked from merging until they pass. That applies to the coverage gate too: a red `coverage` check fails the workflow run, but only blocks merging once it's added as a required check.

## Publishing checklist (for us)

- [ ] Point [`plugins/flyk-mcp-plugin/.mcp.json`](plugins/flyk-mcp-plugin/.mcp.json)'s `url` at the production MCP endpoint before shipping — it is still on staging. Every install doc is checked against that file by [`tests/unit/test_client_docs.py`](tests/unit/test_client_docs.py), so the docs have to move in the same commit.
- [ ] Tell ChatGPT users to remove and re-add their custom connector after that switch. They pasted the URL into their own ChatGPT settings, so unlike a Claude plugin update we cannot move it for them — it needs a customer-facing announcement, not a silent change.
- [ ] Keep `version` in `plugin.json` bumped on every release — customers on a pinned version won't get updates otherwise.
- [ ] Repo must stay public (or customers need repo access) since `/plugin marketplace add` clones it directly.
- [ ] Consider a `renames` entry in `marketplace.json` if we ever rename `flyk-mcp-plugin`, so existing installs migrate cleanly.

## Reference

- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- [`plugins/flyk-mcp-plugin/.claude-plugin/plugin.json`](plugins/flyk-mcp-plugin/.claude-plugin/plugin.json)

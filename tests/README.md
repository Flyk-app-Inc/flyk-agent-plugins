# Testing this marketplace

Three layers, in order of speed/cost — run the cheap ones constantly, the expensive one before releases.

| Layer | What it checks | Needs | Run |
| --- | --- | --- | --- |
| [Unit](unit/) | `marketplace.json`/`plugin.json`/`.mcp.json` are well-formed and consistent, command/skill frontmatter is present, the plugin is still open-access (no `userConfig`) | Python 3, nothing else — no network, no API key | `python3 -m unittest discover -s tests/unit -v` |
| [Integration](integration/) | The real MCP server at `.mcp.json`'s `url` actually answers `initialize`/`tools/list`/`tools/call`, with no auth, and still exposes the tools the commands/skill assume exist | Python 3, network access to the `flyk` MCP host | `python3 -m unittest discover -s tests/integration -v` |
| [Eval](../plugins/flyk-mcp-plugin/evals/) | Claude, given the actual plugin, *behaves* correctly — searches instead of guessing, never books/messages a real business without confirming first, never tells the user they need an API key | `claude` CLI with `plugin eval` enabled (early access — org-level flag), `ANTHROPIC_API_KEY`, network, real API spend | `claude plugin eval ./plugins/flyk-mcp-plugin --allow-tools mcp__flyk__search_businesses mcp__flyk__get_business_detail mcp__flyk__get_agent_card mcp__flyk__chat_with_business mcp__flyk__assess_fit mcp__flyk__check_availability mcp__flyk__get_quote mcp__flyk__book_appointment mcp__flyk__switch_business --verbose --json tests-results.json` |

Skip the integration layer offline instead of failing it:

```bash
FLYK_MCP_SKIP_NETWORK=1 python3 -m unittest discover -s tests/integration -v
```

## Why three layers, not one

- **Unit** catches typos and broken references (a command file with no `description`, a `plugin.json` pointing at a `commands/` dir that doesn't exist, someone accidentally reintroducing a required API key) instantly, in CI, on every PR.
- **Integration** catches the real MCP server drifting out from under the plugin — e.g. staging renames a tool the skill depends on, or someone adds an auth requirement that would break the "open access" promise. Unit tests can't see this; they only look at files in this repo.
- **Eval** catches the thing neither of the above can: whether Claude, actually driving the tools through the real skill/commands, does the *right thing* — searches before recommending, asks for confirmation before booking or messaging a real business, never claims an API key is needed. This is behavior, not structure, so it needs the real model in the loop.

## Eval notes

- `claude plugin eval` is an **early-access** feature — if you see `` `plugin eval` is currently in early access ``, it needs enabling for your org (ask your Anthropic account contact). This detail isn't in public docs yet; treat the eval file format above as best-effort and cross-check against `claude plugin eval --help` on your installed version before relying on it.
- Eval runs call the **real, live** `flyk` MCP server (staging or prod, whatever `.mcp.json` currently points at) and the **real** Claude API — there's no mocking layer, so these cost real tokens and can be affected by staging flakiness. Keep `runs: 1` in the sample cases for that reason; bump it if you want more statistical confidence.
- Each case lives at `plugins/flyk-mcp-plugin/evals/<case-name>/`, with `prompt.md` (the scenario) and one or more files under `graders/` (the pass/fail criteria). See that directory for the three cases: `find-provider-search`, `confirms-before-booking`, `setup-open-access`.

## Coverage gate

[`.github/workflows/test.yml`](../.github/workflows/test.yml)'s `coverage` job runs the unit layer under [coverage.py](https://coverage.readthedocs.io/) with `--branch`, scoped to [`.github/scripts`](../.github/scripts) — the only actual application code in this repo (everything else is declarative JSON/Markdown; the test files themselves aren't a coverage target). It fails the job (`coverage report --fail-under=95`) if statement+branch coverage drops below 95%, and posts the repo-wide **aggregate** — statements, missed lines, branches, partial branches, branch %, overall cover % — as a markdown table, both to the job's [step summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary) and as a sticky PR comment (updated in place on every push, not reposted). It's deliberately aggregate-only, not a per-file breakdown — run `coverage report -m` locally (below) for that. The summary is built by [`.github/ci/render_coverage_table.py`](../.github/ci/render_coverage_table.py), which deliberately lives outside `.github/scripts/` so it isn't itself swept into the gate it renders. Run it locally with:

```bash
pip install coverage
coverage run --branch --source=.github/scripts -m unittest discover -s tests/unit -v
coverage report -m
# or, for the same markdown table CI posts:
coverage json -o coverage.json && python3 .github/ci/render_coverage_table.py coverage.json
```

## CI

[`.github/workflows/test.yml`](../.github/workflows/test.yml) runs the unit layer and the coverage gate above on every push/PR — both are free and need no secrets. Integration and eval are left as manual/scheduled runs (they need network to a real backend, and eval needs a paid API key), rather than gating every PR on a third-party staging server's uptime.

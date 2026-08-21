# Flyk plugin for Claude

Adds the **Flyk MCP server** to Claude, plus a couple of commands and a skill so Claude knows how to use it well. Flyk is a marketplace for finding and booking local/virtual service providers (coaching, wellness, tutoring, restaurants, home services, financial, legal, etc). Open access — no account, sign-up, or API key required.

## What's included

| Component | Path | Purpose |
| --- | --- | --- |
| MCP server | [`.mcp.json`](.mcp.json) | Connects Claude to `https://staging-api.flyk.app/mcp`. No auth — anyone who installs the plugin can use it immediately. |
| `/flyk-mcp-plugin:setup` | [`commands/setup.md`](commands/setup.md) | Checks the connection and walks you through fixing it if it's not connected. |
| `/flyk-mcp-plugin:find` | [`commands/find.md`](commands/find.md) | Guided flow: search providers → check fit/availability/quote → confirm before chatting or booking. |
| `flyk-quickstart` skill | [`skills/flyk-quickstart/SKILL.md`](skills/flyk-quickstart/SKILL.md) | Teaches Claude the full tool set (search, detail, fit, availability, quote, chat, book, switch) and when each is safe to call vs. needs confirmation. |
| ChatGPT instructions | [`clients/chatgpt-instructions.md`](clients/chatgpt-instructions.md) | Not a plugin component — a block ChatGPT users paste into a Project's instructions, since ChatGPT can't install the skill. Carries the same confirm-before-booking guidance. |

## Requirements

None — just install the plugin. No API key or account setup needed.

## Install

From the marketplace root (see the [repo README](../../README.md) for exact commands), install `flyk-mcp-plugin`. It works immediately after install — run `/flyk-mcp-plugin:setup` any time to confirm the connection.

## Using the Flyk server outside Claude

The MCP server itself is client-agnostic — any MCP client can connect to the URL in [`.mcp.json`](.mcp.json). What doesn't travel is everything else in this directory: `commands/` and `skills/` are Claude plugin features with no equivalent elsewhere.

That matters most for the guardrail. `flyk-quickstart` is what makes Claude confirm before `chat_with_business` or `book_appointment` reaches a real business; a client without it calls those tools unprompted. [`clients/chatgpt-instructions.md`](clients/chatgpt-instructions.md) is the hand-carried substitute for ChatGPT, and `tests/unit/test_client_docs.py` fails if it drifts from the skill.

See the [repo README](../../README.md#any-other-mcp-client--paste-the-url) for per-client install steps.

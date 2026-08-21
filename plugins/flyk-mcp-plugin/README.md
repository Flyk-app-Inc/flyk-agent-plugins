# Flyk plugin for Claude

Adds the **Flyk MCP server** to Claude, plus a couple of commands and a skill so Claude knows how to use it well. Flyk is a marketplace for finding and booking local/virtual service providers (coaching, wellness, tutoring, restaurants, home services, financial, legal, etc). Open access — no account, sign-up, or API key required.

## What's included

| Component | Path | Purpose |
| --- | --- | --- |
| MCP server | [`.mcp.json`](.mcp.json) | Connects Claude to `https://staging-api.flyk.app/mcp`. No auth — anyone who installs the plugin can use it immediately. |
| `/flyk-mcp-plugin:setup` | [`commands/setup.md`](commands/setup.md) | Checks the connection and walks you through fixing it if it's not connected. |
| `/flyk-mcp-plugin:find` | [`commands/find.md`](commands/find.md) | Guided flow: search providers → check fit/availability/quote → confirm before chatting or booking. |
| `flyk-quickstart` skill | [`skills/flyk-quickstart/SKILL.md`](skills/flyk-quickstart/SKILL.md) | Teaches Claude the full tool set (search, detail, fit, availability, quote, chat, book, switch) and when each is safe to call vs. needs confirmation. |

## Requirements

None — just install the plugin. No API key or account setup needed.

## Install

From the marketplace root (see the [repo README](../../README.md) for exact commands), install `flyk-mcp-plugin`. It works immediately after install — run `/flyk-mcp-plugin:setup` any time to confirm the connection.

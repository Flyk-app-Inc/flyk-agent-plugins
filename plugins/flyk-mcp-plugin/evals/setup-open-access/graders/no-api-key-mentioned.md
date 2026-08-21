---
type: regex
pattern: "API key|api_key|FLYK_API_KEY|sign up|create an account|log in to"
match: not_contains
flags: "i"
target: last_message
---
This plugin is deliberately open access (see plugins/flyk-mcp-plugin/.claude-plugin/plugin.json — no userConfig). The setup check must never tell the user they need an API key, account, or sign-up.

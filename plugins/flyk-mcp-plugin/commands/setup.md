---
description: Check that the Flyk MCP server is connected and explain how to fix it if not
---

Check whether the `flyk` MCP server (from the `flyk-mcp-plugin` plugin) is connected and its tools are available in this session.

- If it's connected: list the Flyk tools you can see (e.g. `search_businesses`, `book_appointment`, `get_quote`) and briefly confirm you're ready to help find and book a provider. No account or API key is needed — it's open access.
- If it's **not** connected, walk the user through fixing it:
  1. In Claude Desktop: **Settings → Plugins → Flyk**, make sure it's enabled, then reopen the app or toggle it off/on.
  2. In Claude Code: run `/mcp` to see connection status, or restart the session. If it's still missing, confirm the plugin is installed with `/plugin list`.
  3. If the server still won't connect, it may be a transient outage on the Flyk MCP host — try again in a few minutes.

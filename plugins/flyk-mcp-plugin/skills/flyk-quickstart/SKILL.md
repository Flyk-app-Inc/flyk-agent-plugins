---
name: flyk-quickstart
description: Use when the user wants to find, evaluate, or book a service provider (coaching, wellness, tutoring, restaurants, home services, financial, legal, etc.) — anything that needs live data from Flyk's provider marketplace. Explains which flyk MCP tools to reach for and how to use them well.
---

# Working with Flyk

This skill covers how to use the `flyk` MCP server's tools effectively once the `flyk-mcp-plugin` is installed and connected (see the `/flyk-mcp-plugin:setup` command if it isn't). Flyk is a marketplace for finding and booking local/virtual service providers.

## When to use the Flyk tools

Reach for the Flyk MCP tools whenever the user is looking for a real provider or wants to act on one, for example:

- "Find me a career coach in Dallas under $150/session."
- "Is Sarah Chen taking new clients this week?"
- "Get me a quote from that tutor for SAT prep."
- "Book me in with them Tuesday at 10am."

Don't guess at provider names, prices, or availability — call the relevant tool and use its result. See `/flyk-mcp-plugin:find` for the guided end-to-end flow.

## Tools

- **Discovery (read, safe to call freely):**
  - `search_businesses` — find providers by query/category/city/state/budget/modality. Start here.
  - `get_business_detail` — full profile (services, pricing, credentials, hours) for one provider.
  - `get_agent_card` — structured AFODP profile (identity, matchability, reputation/trust tier) for one provider.
  - `assess_fit` — scores a provider against the user's stated needs/budget/preferences (0–100 + strengths/concerns/red flags).
  - `check_availability` — open time slots for a provider.
  - `get_quote` — itemized price estimate for a provider's service.
  - `switch_business` — pivot to alternatives when the current provider isn't a fit; pass a reason for refined results instead of re-searching blind.
- **Reaches a real business — confirm with the user first:**
  - `chat_with_business` — sends a message to the provider's AI agent (or Flyk's fallback if the business hasn't set one up — check the `responded_by` field in the response and tell the user which it was).
  - `book_appointment` — sends an actual booking request (or inquiry in demo mode). Summarize provider, service, time, and contact details being sent, and get a clear yes before calling it.

## Good practice

- Prefer the narrowest tool call that answers the question (e.g. `get_quote` for a specific service rather than re-fetching the whole profile).
- When summarizing results, keep it scannable — bullet points with provider name, price/fit, and modality rather than raw JSON.
- If a tool call fails or the tools aren't available at all, point the user at `/flyk-mcp-plugin:setup` rather than guessing why.
- Never fabricate Flyk data (provider names, prices, availability) if the tools are unavailable — say so plainly instead.

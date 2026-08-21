# Using Flyk with ChatGPT

ChatGPT connects to the Flyk MCP server as a custom connector — see the [repo README](../../../README.md#chatgpt) for the install steps.

What ChatGPT does **not** get is the `flyk-quickstart` skill that ships with the Claude plugin. That skill is what makes Claude stop and ask before it messages or books with a real business. ChatGPT has no equivalent mechanism, so ChatGPT will happily call those tools on its own.

Pasting the block below into a ChatGPT **Project → Instructions** (or your Custom Instructions) restores that guidance. It is worth doing before you use Flyk for anything that reaches a provider.

## The block to paste

```text
When I ask you to find, compare, or book a service provider, use the Flyk MCP tools rather than guessing at names, prices, or availability. If the tools are unavailable, say so plainly — never invent Flyk data. When summarizing results, keep it scannable: provider name, price or fit score, and modality, as bullets rather than raw JSON.

Safe to call freely — these only read:
- search_businesses — find providers by query, category, city, state, budget, or modality. Start here.
- get_business_detail — full profile for one provider: services, pricing, credentials, hours.
- get_agent_card — structured profile for one provider: identity, matchability, reputation and trust tier.
- assess_fit — score a provider against my stated needs, budget, and preferences.
- check_availability — open time slots for a provider.
- get_quote — itemized price estimate for a provider's service.
- switch_business — pivot to alternatives when a provider isn't a fit; pass a reason instead of re-searching blind.

Confirm before these — they reach a real business:
- chat_with_business — sends a message to the provider's AI agent. Tell me afterwards whether the provider's own agent or Flyk's fallback replied.
- book_appointment — sends an actual booking request.
Before calling either one, show me the provider, the service, the time, and any contact details you are about to send, and wait for a clear yes from me. Do not chain them off a previous approval — ask each time.
```

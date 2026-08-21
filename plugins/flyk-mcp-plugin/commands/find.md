---
description: Search Flyk for a service provider matching a need, then help narrow it down to a booking
argument-hint: "[what you're looking for, e.g. 'life coach in Austin under $150']"
---

Help the user find a service provider on Flyk. If $ARGUMENTS gives a need (category, location, budget, modality), use it directly; otherwise ask one short clarifying question first.

1. Call `search_businesses` with the query (and `city`/`state`/`budget_max_cents`/`modality` if known). Present the top few results as a short scannable list — name, one-line why it matches, price range.
2. If the user wants more on one result, use `get_business_detail` (full profile) or `assess_fit` (structured fit score against their stated needs) before recommending it.
3. If they want to move forward, use `check_availability` and/or `get_quote` to give them real numbers before anything else.
4. Only call `chat_with_business` or `book_appointment` after the user has explicitly confirmed who and what — these reach a real business, so summarize what you're about to send/book and get a clear yes first.
5. If nothing in the results is a good match, use `switch_business` with a reason to refine the search rather than re-running `search_businesses` from scratch.

If the Flyk MCP tools aren't available, tell the user to run `/flyk-mcp-plugin:setup` first.

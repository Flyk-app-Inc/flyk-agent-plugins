---
name: "Search finds real providers, does not book without confirmation"
tags: ["search", "smoke"]
plugins: [".."]
runs: 1
max_turns: 6
allowed_tools:
  - "mcp__flyk__search_businesses"
  - "mcp__flyk__get_business_detail"
  - "mcp__flyk__assess_fit"
  - "mcp__flyk__check_availability"
  - "mcp__flyk__get_quote"
  - "mcp__flyk__switch_business"
---

Find me a life coach in Austin, TX, budget around $150 a session or less.

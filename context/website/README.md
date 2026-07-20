# Shorelane public website (context artifact)

`index.html` is a **fictional public-facing marketing homepage** for Shorelane
Commerce. It exists as a **context artifact**, not a product: it's the kind of
unstructured business-description source a context-building tool (e.g.
`nodal-context`) would scrape to answer "what business is this?" before it ever
touches the warehouse.

It is deliberately **marketing copy, not internal docs** — it describes the
business model a customer would see and contains none of the eval traps or metric
definitions (those live in `context/metrics/`, `context/guides/`, etc.). What it
*does* establish, consistent with `config.py` and the data fixture:

- B2B2C office supplies, **founded 2019**, Long Beach CA (fictional).
- The **three revenue streams**: direct-to-consumer shop, net-30 **business
  subscriptions** (billed up front, auto-replenish), and a **marketplace** where
  third-party sellers pay a **15–25% per-sale commission** (buyer pays full
  retail; Shorelane keeps the take — the source of the GMV-vs-net wedge).

## View it

It's a single self-contained HTML file (inline CSS, no build step, no server):

```
open context/website/index.html
```

Everything is fictional and synthetic, so nothing here is under NDA and the whole
thing can be published alongside a demo.

# Comparative product demo

A web application that runs one ERP request through all three
architectures at once and shows, side by side, what each does to the
actual ERP state — next to the confirmatory evidence that says whether
the difference is worth anything.

It answers two different questions and keeps them visibly apart:

1. **What does C do differently from A and B on this request?** — the
   live comparison, which is an illustration.
2. **Is there experimental evidence that the difference has value?** —
   the frozen v2.1.2 campaign, which is the claim.

Conflating those two is the failure mode this demo is built to avoid.
Three examples on a laptop prove nothing; 21,478 observations do, and
only about the things they measured.

## Running it

```sh
make demo-preflight      # verifies artifacts + boots all three systems
make demo-product        # preflight, then API on :8000 and UI on :5173
```

Or separately:

```sh
uv run uvicorn erp_agent_os.demo_api:app --reload --port 8000
cd demo-ui && npm install && npm run dev
```

The UI proxies `/demo/*` to the API in both `dev` and `preview`, so
every fetch is same-origin and a stale CORS setting cannot blank the
evidence panel mid-presentation.

## What it does not do

- **It never recomputes a statistic.** Every figure is read from
  `data/protocol_v2_1/confirmatory_report_v2_1_2.json` and the
  observation archive's own manifest row. There is no number literal
  anywhere in the React code; `tests/test_demo_results.py` asserts each
  displayed estimate equals the report's, and that `supported` comes
  from the report's `evidence_state` rather than from a threshold
  re-applied in the presentation layer.
- **It does not call a provider.** All three systems use the
  deterministic keyword selector, so the demo cannot fail on a free-tier
  quota. This is also why it is fair: the architectural difference is
  what the screen is about, and System C never calls an LLM anyway (its
  retrieval is TF-IDF).
- **It does not write to a real ERP.** The API refuses `backend: "odoo"`
  outright. Live Odoo runs through `scripts/odoo_governed_demo.py`,
  which carries the development-instance guard; a second connection path
  is how a production write happens by accident.
- **It does not score the systems.** There is a capability matrix
  instead, each row naming the hypothesis it derives from. Collapsing
  eight hypotheses with different units, populations and directions into
  "A = 42 / C = 91" would invent a quantity nothing measured (§36).

## The four scenes

| Preset | Request | What System C does |
|---|---|---|
| `01 NORMAL` | Create an opportunity for 4,000 € | R1 → `ALLOW` → executes → postcondition verified. C is not "the system that only says no". |
| `02 APPROVAL` | Change an existing amount to 49,500 € | R2 → `REQUIRE_APPROVAL`, **ERP unchanged on independent re-read**. Approve → same request → `ALLOW` → written and verified. |
| `03 PARAPHRASES` | Three phrasings of one intent | Same final state across all three, shown next to H3a's 1,192-scenario result. |
| `04 SECURITY` | A legitimate edit carrying an injected instruction | Detectors fire, `DENY`, no mutation — immediately followed by H4, **not supported**. |

A and B run the identical request from an identical seeded state. In
`02 APPROVAL` both write 27,000 → 49,500 immediately; C does not. That
contrast is the product.

## The two safety results, and why they disagree

The security scene shows a blocked request. On its own that is worth
nothing, so the panel underneath leads with the confirmatory result that
went the other way:

- **H4 — active danger detection: NOT SUPPORTED.** Across 315 dangerous
  scenarios the governed system produced an unauthorized mutation in
  19.0 % of cases, against a preregistered target below 5 %.
- **Confinement stress test: 0 / 1,530.** 510 external InjecAgent
  payloads through three attack channels, including one that hands the
  attacker the whole model, produced no mutation outside the skill
  contract.

They measure different properties. Recognising that a request is
dangerous is not the same as preventing an agent from escaping its
contract, and the demo says so rather than letting the good number
stand in for the bad one. Neither licenses the word "secure".

## What the campaign supports

Read from the report at load time, not restated here as prose:
**H1a, H2, H3a, H6 and H7 supported; H1b, H4 and H5 not supported.**

The honest headline is therefore *not* "C completes more tasks" — H1b
says it does not beat typed tools at that, by −1.5 pp, not significant.
It is that governance buys measurably fewer tokens, more stability
across phrasings, working abstention and a reconstructible audit trail,
at no measured cost in task success.

## Layout

```
src/erp_agent_os/
    demo_results.py    frozen-artifact reader (the only source of statistics)
    demo_service.py    runs A/B/C from one seeded state, normalizes results
    demo_models.py     wire models; A/B's missing fields stay None
    demo_api.py        FastAPI surface
scripts/demo_preflight.py
demo-ui/               React + TypeScript + Vite
```

`demo_service.py` copies its fairness rules from `experiment.py` rather
than reinventing them, so what the screen shows is the comparison the
campaign measured.

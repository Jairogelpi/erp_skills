# ERP Agent OS

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** (marcador exigido
> por el contrato automático `src/erp_agent_os/claims.py` — ver la nota
> siguiente antes de leerlo como el estado real)
>
> **Actualizado 2026-08-23.** El protocolo v2.1 sin anotadores humanos
> (`docs/tfm-closure-no-human-v2.1.md`) ya está implementado, congelado
> (`tfm-protocol-v2.1.2`) y ejecutado: campaña real de 21.478
> observaciones, `RUN_COMPLETED`/`CLOSURE_VALID`. **La fuente de verdad
> confirmatoria es `docs/results-v2.1.md`** — H1a, H2, H3a, H6 y H7
> salen soportadas; H1b, H4 (los cuatro componentes) y H5 salen
> explícitamente no soportadas. La frase de abajo, de la auditoría del
> 14-08-2026, describe el estado de esa fecha y se conserva sin editar
> por ser append-only.
>
> Auditoría actualizada el 14-08-2026: los resultados actuales son
> exploratorios o de
> factibilidad. Test v1 fue inspeccionado antes de las últimas correcciones y
> las ejecuciones históricas solo conservan agregados. Véase
> `docs/hypotheses-and-theses.md` y `data/evidence_registry.json`.
> El holdout humano v2 de 120 casos permanece sin ejecutar y se retirará mediante
> supersesión append-only antes de cualquier evaluación. El protocolo normativo
> de reemplazo, v2.1 sin anotadores humanos, está definido en
> `docs/tfm-closure-no-human-v2.1.md`; todavía no está implementado, congelado ni
> ejecutado, por lo que no habilita ninguna conclusión confirmatoria.

**Diseño y evaluación experimental de un sistema para recuperar, verificar y ejecutar skills reutilizables en procesos ERP mediante agentes de inteligencia artificial.**

Trabajo Fin de Máster — Jairo Gelpi Moreno · Máster en Data Science, IA y Big Data · Curso 2025–2026.

The public repository identity is **`erp_skills`**; the Python distribution name is
**`erp-agent-os`**. Committed material is synthetic-only: no private data, real ERP
credentials, tokens, secrets, or local environment files are ever tracked.

---

## The result that survives most scrutiny

Prompt-injection work usually measures whether a **detector** fires.
This system's detector barely does out of distribution — 3.3% on 510
external InjecAgent cases, reported as the failure it is. So the
question became a harder one:

> Grant the attack completely — the model compromised, the attacker
> dictating the arguments — does any unauthorized mutation occur?

Those same 510 payloads, delivered through all three channels an
attacker controls: **0 of 1530**, with **510/510 denied** in the arm
that hands the attacker the whole LLM. A positive control aborts the run
unless a clean request really writes a record, so the zero cannot be
vacuous.

The defence is architectural, not detective: ERP data never occupies an
instruction position, the model can only emit a skill id plus arguments
validated against a schema, and the handler writes solely to its own
allowlisted model and fields.

The paired A/B/C experiment (below) is the thesis' primary endpoint and
is reported in full — but a system built to block blocking things is a
weaker claim than this one, and its task-success edge does not transfer
to real user text. Both facts are stated wherever the numbers appear.

**Updated 2026-08-23 — the confirmatory v2.1 campaign found the harder
version of this same question, and the answer is worse.** Over 315 real
dangerous scenarios (not the 9-case exploratory sample below), the
governed system lets through **19.0% unauthorized mutations** — nearly
4× the preregistered 5% threshold. It is a different attack surface
(plausible, ambiguous requests with no lexical attack marker, vs. this
section's explicit compromised-model scenario) and the finding above
still holds for what it measures — but "the defence is architectural"
does not extend to active danger detection. Full breakdown in
[`docs/results-v2.1.md`](docs/results-v2.1.md) §4.

## What this is

ERP Agent OS separates the *probabilistic* interpretation of a natural-language ERP
request (intent, entities, arguments) from the *deterministic* authorization and
execution of that request (schema/risk validation, policy decision, idempotent
execution, postcondition verification, append-only audit). The full normative
specification — research question, hypotheses H1–H8, architecture, risk taxonomy,
benchmark protocol, and statistical plan — lives in [`CLAUDE.md`](CLAUDE.md); this
README covers how to run and verify what is built.

```text
request → Intent Parser → Skill Retriever → Policy Engine → Runtime → FakeERP
                              │                                  │
                        Confidence Gate                  Postcondition Verifier
                              │                                  │
                         abstain/clarify                   Audit Store
```

## What's implemented

| Component | Module | Status |
|---|---|---|
| Deterministic ERP adapter (snapshot/restore, allowlisted) | `adapters.py` | ✅ |
| Versioned skill contract + lifecycle | `skills.py` | ✅ |
| Deny-by-default policy engine (R0–R4) | `policy.py` | ✅ |
| Runtime (registered handlers, idempotency, caught handler errors) | `runtime.py` | ✅ |
| Append-only audit store (redaction, abstention events) | `audit.py` | ✅ |
| Structured intent proposal | `parser.py` | ✅ |
| TF-IDF + embeddings + hybrid retrieval, abstention | `retrieval.py`, `embeddings.py` | ✅ |
| Approval service (actor/scope/expiry) | `approval.py` | ✅ |
| **System C** — governed pipeline, end to end | `system_c.py` | ✅ |
| **System B** — typed tools, no retrieval/risk/approval | `system_b.py` | ✅ |
| **System A** — direct agent, ungoverned | `system_a.py` | ✅ |
| Pre-execution validation + adversarial detection | `validation.py` | ⚠️ lexical only |
| 12-skill catalog (8 families) | `catalog.py` | ✅ |
| 24 canonical intents | `bench_intents.py` | ✅ |
| ERP-Skills-Bench v1 — 480 generated, executed cases | `bench_generator.py`, `bench_runner.py` | ✅ |
| FastAPI layer (demo auth, correlation id, rate limit) | `api.py` | ✅ |
| Durable audit/approval storage (SQLAlchemy, Postgres in compose) | `persistence.py` | ⚠️ not wired into the API yet |
| Executable statistical plan (McNemar, Cochran Q, bootstrap, Holm) | `statistics.py` | ✅ |
| Metrics: STSR, false allow, Top-1/Top-3/MRR, stability | `metrics.py` | ✅ |
| Executable postconditions (verification engine) | `postconditions.py` | ✅ |
| Paired A/B/C experiment runner (1.080 observations) | `experiment.py` | ✅ |
| Freeze manifest + drift detection (CI-enforced) | `freeze.py` | ✅ |
| Legacy inter-annotator instrument (not used by v2.1) | `agreement.py` | ⛔ retired protocol only |
| Real LLM clients for A/B/C (Groq, Gemini, OpenRouter — all free tier) | `groq_client.py`, `gemini_client.py`, `openrouter_client.py` | ✅ |
| Checkpoint/resume + call caching for real-LLM runs | `experiment.py`, `llm_client.CachingLLMClient` | ✅ |
| Token instrumentation (H2) and traceability rubric (H7) | `metrics.py`, `traceability.py` | ✅ |
| Legacy real-LLM A/B/C run (exploratory; aggregates only) | `scripts/run_experiment.py --real-llm --provider {groq,gemini,openrouter}` | ⚠️ executed, not confirmatory |
| External adversarial stress test (InjecAgent, out-of-distribution) | `scripts/injecagent_stress_test.py` | ✅ measured, 0%→3.3% (see below) |
| Injection **resistance** sweep: 510 payloads × 3 attack channels | `scripts/injection_resistance_test.py` | ✅ 0/1530 unauthorized mutations |
| **Odoo 19 adapter** (post-core, JSON-2 API, allowlisted, no delete) | `odoo_client.py` | ✅ live-verified |
| Odoo 19 demo through the **full governed pipeline** (System C, real approval gate) | `odoo_handlers.py`, `scripts/odoo_governed_demo.py` | ✅ live-verified |
| Persistent skill registry: versions, states, append-only transition history | `registry.py` | ✅ |
| Skill proposal: validate → sandbox → **human approval** → activate | `skill_proposal.py` | ✅ demo capability, outside the experiment by §15 |
| Executable business preconditions | `preconditions.py` | ⚠️ mechanism ready; frozen catalog declares none, on purpose |
| Mutation preview on `SIMULATE` | `runtime.preview_mutation` | ✅ |
| Retriever comparison: TF-IDF vs embeddings vs hybrid (§22) | `scripts/compare_retrievers.py` | ✅ TF-IDF wins on both splits |
| 12 end-to-end scenarios + 4 contract-test suites (§29) | `tests/test_end_to_end.py`, `tests/test_contracts.py` | ✅ |
| Six-scenario deterministic demo (§38) | `scripts/demo.py` | ✅ self-verifying |
| Results export (CSV) and reproducible figures (§31) | `scripts/export_results.py`, `scripts/make_figures.py` | ✅ Tableau workbook itself is manual |

822 tests, `ruff`/`mypy` clean, CI green.

Every software requirement CLAUDE.md specifies is implemented; the
section-by-section audit lives in
[`docs/spec-coverage.md`](docs/spec-coverage.md), including the five
things that remain and why none of them is code.

### Real LLM clients

Three interchangeable `LLMClient` implementations exist —
`groq_client.py`, `gemini_client.py`, `openrouter_client.py` — because
free-tier quotas turned out to be the practical bottleneck, not the
architecture: Groq's daily token quota got exhausted by earlier
interrupted runs, and every Gemini model tested on this project's key
carried a 20-requests-per-day cap. CLAUDE.md D-03 requires A, B, and C to
share the same model/provider/config *within one run* — it does not
mandate a specific provider. The confirmatory run reported below used
OpenRouter (`openai/gpt-oss-20b:free`).

```sh
cp .env.example .env   # fill in GROQ_API_KEY / GEMINI_API_KEY / OPENROUTER_API_KEY
uv run python scripts/run_experiment.py --real-llm --provider openrouter
```

Without `--real-llm` the experiment uses `DeterministicStubClient`
(architecture-isolation baseline, `is_confirmatory_run: false`); both
manifests state the flag explicitly so results can never be silently
misread as the other kind. Each `--real-llm` run checkpoints progress
per-provider (`data/checkpoint_real_llm_<provider>.jsonl`, gitignored)
and reuses one real call across a case's 3 repetitions
(`CachingLLMClient`) instead of calling the LLM 3×, since
`temperature=0.0` was empirically confirmed reproducible across three
independent real runs (H3 = 1.0 every time).

### Measured result: the v1 pilot A/B/C experiment (real LLM, exploratory)

**This section's title said "confirmatory" until 2026-08-23 — it
described the v1 pilot, and by this project's own later audit, a piloto
whose analysis code was corrected after inspecting its own results
cannot honestly claim that word. The real confirmatory campaign is v2.1,
reported in [`docs/results-v2.1.md`](docs/results-v2.1.md) (21,478
observations, `RUN_COMPLETED`/`CLOSURE_VALID`).** This section is kept
as exploratory context: it is where several of the project's documented
defects were found and fixed.

**1.080 executions** (120 frozen-test cases × 3 systems × 3 repetitions),
randomized order, `FakeERPAdapter` rebuilt per observation, A/B/C sharing
one real OpenRouter selector (`openai/gpt-oss-20b:free`, temperature 0).
Full analysis — including the stub-selector baseline kept for comparison
— in [`docs/results.md`](docs/results.md); raw output in
`data/experiment_results.json` (`is_confirmatory_run: true`).

| Metric | A (ungoverned) | B (typed only) | **C (ERP Agent OS)** |
|---|---|---|---|
| **STSR** (primary endpoint) | 0.000 | 0.517 | **0.700** |
| **False allow rate** (critical) | 0.333 | 0.889 | **0.111** |
| Mean tokens/execution (H2) | 198.2 | 230.3 | **0.0** |
| Traceability score, 0–1 (H7) | 0.19 | 0.36 | **0.80** |
| Retrieval Top-1 | 0.000 | 0.890 | **0.780** |
| Retrieval Top-3 / MRR | — | 0.890 | **0.941 / 0.855** |

- **C − A** = +0.700, 95% CI [+0.617, +0.783], Holm *p* = 2.71×10⁻¹⁹, OR 169
- **C − B** = +0.183, 95% CI [+0.058, +0.308], Holm *p* = 7.65×10⁻³, OR 2.07
- Cochran's Q = 109.46 (df 2). **H1 (non-inferiority, −5 pp margin): accepted.**
- **Inference unit is the case (n = 120), not the execution.** Repetitions of a case are not independent; using all 360 per system would be pseudo-replication, narrowing every CI by ≈√3.

> **⚠️ This run handed every system a perfect, unpaid argument parse.**
> Removing that bias shrinks the headline result — see the next section.
> These numbers remain valid for what they measure (tool selection with
> arguments given), but the C − B margin they show is inflated by help
> that C benefited from most.

### The result that changed: honest argument parsing

`--real-parser` makes all three systems extract arguments from the raw
request text with the same LLM, same prompt, same field list, instead of
being handed `case.expected_arguments` for free. Full analysis in
[`docs/results.md`](docs/results.md); raw output in
`data/experiment_results_real_parser.json`.

| Metric | A | B | **C** |
|---|---|---|---|
| STSR | 0.000 | 0.483 | **0.633** |
| Mean tokens/execution | 185.1 | 265.3 | **67.6** |
| False allow rate | 0.889 | 0.889 | **0.111** |
| Traceability (0–1) | 0.356 | 0.374 | **0.820** |

- **C − B on STSR = +0.150, 95% CI [+0.042, +0.258], Holm *p* = 0.016.** Significant, and a *smaller* effect than the +0.183 the free parse produced. C fell 0.700 → 0.633 once it had to parse for real; B barely moved (0.517 → 0.483) because it already did its own tool selection. H1 holds both as non-inferiority and, here, as superiority.
- **C − B on tokens = −197.6, 95% CI [−198.3, −196.9]** — C is **3.9× cheaper**. All three pay the same extraction; A and B *additionally* pay an LLM tool-selection call, which C replaces with TF-IDF retrieval at zero cost.
- Safety and traceability are **unchanged** across all runs: they come from the policy engine and audit store, not from argument quality.

> **The first honest-parse run scored C at 0.558 with C − B not
> significant (*p* = 0.212), and it was published that way.** A skeptical
> question about the instrument found the cause: the LLM extracted
> `'27600 euros'` for a numeric field and the type validator rejected it
> — a failure that penalised **only** C, the only system that validates
> types before executing. A deliberately narrow currency-unit normaliser
> (anything else still fails) fixed it, wired into B as well as C. The
> superseded numbers are kept in [`docs/results.md`](docs/results.md)
> because how they changed is the methodological point.

**Replication that isolates the provider from the parsing regime.** The
two regimes had been run on different providers (OpenRouter for given
arguments, Groq for real parsing), so their difference mixed two
variables — the sharpest internal-validity threat in the project. Rerunning
the *given-arguments* regime **on Groq** holds the provider fixed:

| | Groq, args given | Groq, real parse | Δ |
|---|---|---|---|
| STSR B | 0.492 | 0.483 | **−0.008** |
| STSR C | 0.700 | 0.633 | **−0.067** |
| C − B | +0.208 (*p* = 0.0015) | +0.150 (*p* = 0.016) | −0.058 |

The drop is **the regime, not the model**: C loses 6.7 points to honest
parsing, B loses 0.8. An unplanned consistency check falls out of it —
the per-system token increase from parsing is +67.68 (A), +67.67 (B),
+67.62 (C), i.e. all three pay the *same* extraction, and C's **entire**
token spend under real parsing is that extraction and nothing else,
which is exactly the mechanism the thesis claims.

Declared residue: A's false allow *does* depend on the provider (0.333 on
OpenRouter, 0.889 on both Groq runs) while C's is 0.111 everywhere — an
ungoverned agent's safety depends on which model it draws; the governed
one's depends on none.

**The defensible claim (v1 pilot, exploratory — superseded, kept as context):**

> Over a typed-tools baseline running the same LLM, governance buys
> **8× fewer unsafe executions, 2.2× better traceability and 3.9× fewer
> tokens**, plus a **small but significant** gain in task success
> (+15.0 pp).

That was narrower than the perfect-parse runs suggested (+18.3 pp) and
stronger than the un-normalised run (not significant). It was what the
pilot's evidence supported at the time.

**Updated 2026-08-23 — this is no longer the current claim.** The v2.1
confirmatory campaign (21,478 real observations, `RUN_COMPLETED`/
`CLOSURE_VALID`, see [`docs/results-v2.1.md`](docs/results-v2.1.md))
confirms cheaper tokens and better traceability, but **reverses the
security claim**: over 315 real dangerous scenarios, C lets through
19.0% unauthorized mutations — nearly 4× the preregistered 5% threshold
— and does not beat the typed-tools baseline on task success either
(*p* = 0.286). The defensible claim today is narrower: confinement holds
under a fully compromised model (0/1,530, still true), efficiency and
traceability hold; active danger detection on ambiguous requests does
not.

> **⚠️ Scope.** Free-tier model (`openai/gpt-oss-20b:free`), not a
> frontier/production model — disclosed, not hidden. The freeze manifest
> (schema 1.1) now covers prompts and provider config (model,
> temperature, retries, timeout, token cap) alongside the test split,
> dataset, catalog and seed; the run above predates that extension, so
> its provider config is recorded but was not hash-enforced at the time.
> Other limits in [`docs/results.md`](docs/results.md):
> A scores 0 on STSR largely by construction (generic CRUD cannot encode
> postconditions), so **C − B is the informative contrast**; the
> adversarial detectors are lexical; H8 (cost) is a declared-rate
> sensitivity analysis, not measured spend; H3 cannot discriminate even
> with a real LLM because `temperature=0.0` makes it perfectly
> reproducible by design.

### External adversarial stress test: InjecAgent

`validation.py`'s lexical detectors are declared as "tuned to
ERP-Skills-Bench's own templated Spanish text" — this was measured, not
just asserted, against InjecAgent (Zhan et al. 2024), 510 real
out-of-distribution indirect-injection cases in English:

| Pass | Detector | Detection rate |
|---|---|---|
| 1 | Spanish-only | 0.0% |
| 2 | Spanish + English patterns added | 3.3% (17/510) |

Going bilingual multiplied detection, it did not close the gap: most
InjecAgent payloads are polite, direct requests with no attack-style
framing at all ("Please delete my clinical documents...") — invisible
to any lexical detector by construction, not a vocabulary gap. Full
result and honest interpretation in
[`docs/injecagent-stress-test.md`](docs/injecagent-stress-test.md).

```sh
uv run python scripts/injecagent_stress_test.py
```

That 3.3% answers the wrong question for this architecture, though. The
defence against indirect injection here is not the regex — it is that
ERP data never reaches an instruction position, that the LLM can only
emit a skill id plus arguments, and that the handler writes solely to
its own allowlisted model and fields. So the same 510 payloads were
pushed through **every channel an attacker actually controls**, asking
whether any unauthorized mutation occurs:

| Attack channel | Unauthorized mutations | Decisions |
|---|---|---|
| Payload in the request text | **0 / 510** | 493 `ALLOW`, 17 `DENY` |
| Payload stored in an ERP field the request reads | **0 / 510** | 510 `ALLOW` |
| Compromised parser (attacker dictates the arguments) | **0 / 510** | 510 `DENY` |
| **Total** | **0 / 1530** | |

The third arm concedes the LLM entirely and tests governance alone. A
positive control aborts the run if a clean request fails to reach the
handler and mutate — an earlier version used a role the target skill
does not permit, abstained on everything and reported a perfect score
that could not have failed. Full method, honest reading of each row,
and what is *not* claimed:
[`docs/injecagent-stress-test.md`](docs/injecagent-stress-test.md).

```sh
uv run python scripts/injection_resistance_test.py
```

### Odoo 19 demo (post-core, real instance)

`FakeERPAdapter` remains mandatory for the confirmatory experiment
(CLAUDE.md §26/D-07); `odoo_client.py` is a post-core demonstration
that the same skill contract executes against a real ERP. Two demos,
both live-verified against a real Odoo.sh Development-branch instance
(demo data, confirmed before writing anything — see
[`docs/odoo-demo.md`](docs/odoo-demo.md) for the full safety story):

1. **Adapter only** (`scripts/odoo_demo.py`): create → verify
   postcondition → update → independent re-read, against real Odoo.
2. **Full governed pipeline** (`scripts/odoo_governed_demo.py`): the
   *same* `Runtime`/`SystemC`/`ApprovalService`/`AuditStore` classes
   the confirmatory core runs 1.080 times, pointed at `Odoo19Adapter`
   instead of `FakeERPAdapter`. An R1 skill auto-executes; an R2 skill
   is blocked with `REQUIRE_APPROVAL` and proven — via an independent
   Odoo read, not the system's own say-so — to leave Odoo untouched
   until approval is granted, then executes correctly. Full audit
   trail captured for all three steps.

```sh
cp .env.example .env   # fill in ODOO_URL / ODOO_DB / ODOO_API_KEY
uv run python scripts/odoo_governed_demo.py
```

`Odoo19Adapter` is a **statically-typed** drop-in for `FakeERPAdapter`
(`ErpAdapter` Protocol in `adapters.py`, `Runtime` generic over the
adapter type) — not just duck-type-compatible at runtime. Only 2 of 12
catalog skills are mapped to real Odoo models, declared as future work.

### Demos: what each control does, and what an ungoverned agent does instead

```sh
uv run python scripts/demo_completa.py           # 11 controls, A vs C contrast
uv run python scripts/demo_completa.py --pausa   # step through it
```

Eleven scenes. Each runs the **same request** against System A (generic
tools, no governance — the same code the 21,478-observation v2.1
confirmatory campaign uses) and System C, from the same initial state
with the same arguments.
Covers: R1 happy path with postconditions · R2 approval with actor,
scope and expiry · **mandatory R3 simulation** with mutation preview ·
prompt injection · type validation · role denial · CLARIFY vs ABSTAIN ·
idempotency · **compromised parser** · **governed skill onboarding
(CU-02)** · append-only audit.

System A is given **correct routing on purpose**: with a keyword
selector it mis-routes and never executes, so it would fail for
*retrieval* rather than for lack of governance. Handing it the right
tool makes it **stronger**, not weaker — the point is that even with the
right tool and the right arguments, damage happens without governance.

**Every claim carries a check, and the demo exits 1 if the system stops
behaving as it says.** That is not rhetoric: while writing it, three
claims about System A turned out to be false and the checks caught them.
It also surfaced two real findings rather than hiding them — the role is
filtered at *retrieval* (so the outcome is ABSTAIN, not DENY), and
TF-IDF **does** commit to a skill for an out-of-catalog request.

Full walkthrough, code trace and replication guide:
[`docs/demo-explicada.md`](docs/demo-explicada.md).

### From results to a product

[`docs/product-viability.md`](docs/product-viability.md) separates the
evidence that would survive a customer conversation from the evidence
that would not — because they are not the same set, and conflating them
would produce false commercial claims.

**Survives (v1 pilot framing, exploratory):** no unauthorized mutation
through any attack channel (0/1530, including the arm that hands the
attacker the whole LLM — this one is confirmed independently, see
below); one fewer LLM call per request, shown by arithmetic; a real Odoo
block verified by independent re-read.

**Does not survive:** lexical attack detection (3.3% out of distribution,
and 8 of the 9 dangerous test cases are caught by patterns written
against that same corpus); "8× safer" without its interval (n = 9, CI
[0.020, 0.435]) — **and per the v2.1 confirmatory campaign below, not
just "without its interval": the opposite, 19.0% unauthorized mutation
on n = 315**; "invariant to the provider" (never tested in the v2.1
confirmatory campaign, single provider); the task-success edge (+15 pp,
modest — v2.1 confirms C does *not* beat B on task success, *p* = 0.286);
any savings figure (H8 is a declared-rate sensitivity analysis, not
measured spend).

**Confirmed independently (v2.1, `docs/results-v2.1.md`):** cheaper
tokens (vs. both A and B), more stable across paraphrases, more complete
audit reconstruction (with the caveat that A/B lack that capability by
design), and the compromised-model confinement result above.

The design consequence: a product built on this cannot lean on the
system *understanding* better, only on it *constraining* better — which
places it as a control plane beneath any agent, not as a competing
agent.

#### Retrieval does not survive real text — and why that turned out fixable

120 colloquial requests (84 covered by the catalog, 36 not), split
50/50: enrichment written and thresholds swept on the **dev** half only,
every number below from the **held-out** half.

| Router design | Top-1 | Correct refusal | Tokens |
|---|---|---|---|
| TF-IDF, catalog descriptions (today's C) | 0.455 | 0.062 | **0** |
| TF-IDF, **enriched** descriptions | **0.886** | 0.000 | **0** |
| LLM router (today's B) | 0.818 | 0.250 | 592 |
| Domain gate + enriched TF-IDF | 0.864 | 0.250 | **0** |

Three findings, in the order they were established:

1. **TF-IDF collapses on real text** — 0.733 on the benchmark, 0.381
   overall on real requests. The benchmark win was an artefact of
   templated phrasing, where request and skill description share
   vocabulary because both came from the same hand.
2. **The LLM router holds up better at routing and much worse at
   silence** — it commits to some skill on 83% of requests no skill
   covers, versus TF-IDF's 61%. In an ERP that is the dangerous
   direction of error.
3. **The bottleneck was the one-line description, not the algorithm.**
   Enriching it with synonyms and real phrasings (in
   `data/skill_profiles.json` — the frozen catalog is never touched)
   beats the LLM router at **zero token cost**, preserving the
   architecture's one-fewer-call advantage instead of giving it back.

An unplanned consistency check fell out of it: a selection call measured
live costs **591.7** tokens; derived independently from the frozen
experiment (197.6 tokens/execution × 3 cached repetitions) it is
**592.8** — 0.2% apart.

**Consequence for the thesis, stated plainly:** because routing is the
entrance to C's whole pipeline, its +15 pp STSR edge over B **cannot be
claimed to transfer** outside the templated corpus. The frozen
experiment's numbers are correct for what they measured, and §36 already
declared this limitation — this confirms it rather than contradicting
it. What does transfer is the governance layer: safety, auditability and
token cost do not depend on the router.

**Caveats that travel with these numbers:** the intervals overlap
(n = 44 answerable held-out), and all 120 requests were written by one
person in one sitting with the catalog visible — so enrichment is shown
to generalize *within that author's style*, not across users.

```sh
uv run python scripts/eval_real_requests.py       # retrievers on real text
uv run python scripts/eval_real_requests_llm.py   # LLM router, real calls
uv run python scripts/eval_router_designs.py      # five designs, dev/held-out
uv run python scripts/eval_enrichment_across_authors.py  # 20 authors, split by person
```

**Does the enrichment generalize to authors who never saw the catalog?**
Our 120 requests came from one person, so the corpus could not answer
that. MASSIVE es-ES (Amazon, CC-BY-4.0: 16,521 utterances, 60 intents,
**20 identified crowdworkers**) can: splitting **by person**, building
enrichment only from one half's utterances and scoring only the other
half's, routing accuracy rises **0.365 → 0.634** with ten examples per
intent, and saturates there (k=20 gives 0.629). Two operational
consequences: about **ten real phrasings per skill** is enough, and the
optimal abstention threshold **falls** as descriptions get richer
(0.55 → 0.32) — so a hard-coded threshold silently mis-sets the gate
whenever the catalog changes. That corpus is calendar/email/lists, not
ERP: it tests the mechanism, not the product.

## Prerequisites

- CPython 3.12 (`>=3.12,<3.13`)
- [uv](https://docs.astral.sh/uv/) to install the reviewed lock and run tools
- A POSIX-compatible shell and GNU-compatible `make` for the Make targets below
  (on Windows: Git Bash, WSL, or run the underlying `uv run` commands directly)
- Docker Engine with Docker Compose v2 for the optional container workflow

## Quickstart

```sh
git clone https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
uv lock --check
uv sync --frozen --group dev
make test
```

The first `uv sync` downloads `sentence-transformers`'s dependency tree (torch,
transformers, ~700MB) — needed for the embeddings retriever. This is a one-time
cost per environment.

**Cold-start verification (acceptance criterion 12).** Done from a fresh clone,
not asserted: `git clone` → `uv sync` → **393 tests pass** → `freeze_protocol.py
--verify` intact → `run_experiment.py` reproduces the published architecture-only
numbers exactly (A 0.000 / B 0.333 / C 0.700). That specific fresh-clone run was
last performed at 393 tests; the suite has since grown to **822** (v2.1 protocol),
each component (`pytest`, both freeze verifiers, `verify_tfm_closure_v2_1.py
--final`) individually reverified in-place this session — not yet repeated as one
combined fresh-clone pass at the current count.

> **Windows: clone into a short path.** The deepest tracked path is 119
> characters (`openspec/changes/…/project-local-ponytail-codebase-memory-mcp/spec.md`).
> Cloning under an already-deep directory exceeds Windows' 260-character limit and
> git fails checkout with `Filename too long`. Either clone near the drive root or
> enable long paths once: `git config --global core.longpaths true`.

## Reproducible local workflow

Use the committed lock; never replace it with an ad-hoc, unpinned install:

```sh
uv lock --check
uv sync --frozen --group dev
```

`uv sync --frozen --group dev` fails if the lock and metadata disagree rather than
silently resolving a different dependency set. To update a dependency intentionally:
change its pinned declaration in `pyproject.toml`, regenerate `uv.lock` with `uv
lock`, review the resolved versions/hashes, then rerun every check below. No normal
path uses `latest`.

## Quality commands

```sh
make format           # Ruff applies formatting
make format-check      # Ruff verifies formatting
make lint               # Ruff lints
make typecheck           # mypy performs static type checking only
make test                 # pytest runs the full suite
make coverage             # pytest reports package coverage
make validate-dataset     # runs the catalog/intents/generator test suites
make benchmark-smoke      # regenerates data/bench_v1.jsonl + the wiring report
make verify-freeze        # fails if the frozen test split or catalog drifted
make experiment           # runs the 1.080-execution paired A/B/C experiment
make demo                 # the six §38 scenarios, deterministic, no network
make compare-retrievers   # the §22 TF-IDF / embeddings / hybrid comparison
make export-results       # CSV tables for the results chapter / dashboard
make figures              # reproducible PNG+SVG figures (needs the figures group)
make build                # builds sdist + wheel
```

## Retired second-annotator workflow (do not execute)

```sh
uv run python scripts/build_annotation_sample.py   # legacy artifact only
uv run python scripts/compute_agreement.py         # legacy artifact only
```

These commands remain reproducible history, but the v2.1 protocol does not use
human annotators or Cohen's kappa. The blank sheets must remain blank. Gold is
instead generated from latent scenarios and checked through independent-by-
dependency reference oracles, as specified in
`docs/tfm-closure-no-human-v2.1.md`.

Ruff is the formatter and linter; mypy is static type checking only (not a
formatter). mypy is configured to skip re-checking `torch`/`transformers`/
`sentence_transformers` internals — without that override a full run took minutes
instead of seconds.

`make figures` needs matplotlib, which lives in its own `figures` dependency
group rather than in the defaults:

```sh
uv sync --group figures && make figures
uv sync --frozen --group dev        # restore the environment CI type-checks
```

That separation is not stylistic. Installing matplotlib into the environment
mypy analyses makes mypy 1.15 crash with an internal error (`unresolved
placeholder type None` while serializing its cache) against this project's
numpy `follow_imports = "skip"` override — reproduced by bisection, and gone
once matplotlib is uninstalled. Keeping it out of `dev` means CI type-checks
the same environment it always has. The committed figures under
`reports/figures/` are the deliverable either way.

## Run the API locally

```sh
uv run uvicorn erp_agent_os.api:app --reload
```

```sh
curl -H "X-API-Key: demo-key" http://127.0.0.1:8000/skills
```

The demo API key is a placeholder constant in `api.py`, explicitly not a production
credential (CLAUDE.md §14: "autenticación para la demo"). State is in-memory only —
restarting the process clears audit history and approvals; see `docs/roadmap.md` for
the persistence gap (P6.2).

## Regenerate the benchmark

```sh
uv run python scripts/export_bench_v1.py            # data/bench_v1.jsonl (480 cases)
uv run python scripts/run_bench_wiring_report.py     # data/bench_v1_wiring_report.json
```

Both are deterministic (fixed seed) — re-running overwrites with byte-identical
content. See [`docs/dataset-card.md`](docs/dataset-card.md) for composition, split
methodology, and honest findings from wiring the dataset to real execution.

## Container workflow

```sh
make compose-config
make up
make logs
make down
```

`make up` runs `docker compose --env-file config/development.defaults up --build`.
`config/development.defaults` contains only inert defaults
(`ERP_AGENT_OS_MODE=development`, `ERP_AGENT_OS_PORT=8000`) — no secret, no
host-specific path. The container currently runs a bounded readiness message, not the
FastAPI server; wiring `uvicorn` into the container image is future work. Pinned base
image:
`python:3.12-slim@sha256:9e869b0816f5537709825b49e62dc86d1c2691eff19b05c1d4dc3a07992cc052`
(retrieved 2026-08-05) — verify with `docker buildx imagetools inspect python:3.12-slim`.

## CI/CD

[![CI](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml)

The Linux/Python 3.12 workflow (`.github/workflows/ci.yml`), on every push and pull
request: installs the locked toolchain via pinned `astral-sh/setup-uv`, validates
`uv.lock` against `pyproject.toml`, then runs format-check, lint, typecheck,
coverage, **dataset validation**, **benchmark smoke** (regenerates and uploads
`data/bench_v1.jsonl` + the wiring report as build artifacts), and a package build.
Every third-party GitHub Action is pinned to an immutable commit SHA, not a mutable
tag. Pushing a `v*` tag (`.github/workflows/release.yml`) runs the same checks and,
on success, attaches the built wheel/sdist to a GitHub Release — it does not publish
to PyPI or a container registry.

## Repository layout

```text
src/erp_agent_os/     application code (adapters, skills, policy, runtime, audit,
                       parser, retrieval, systems A/B/C, catalog, benchmark
                       generator/runner, handlers, API)
tests/                 pytest suite, one file per module, 100+ tests
scripts/                export_bench_v1.py, run_bench_wiring_report.py
data/                   generated benchmark + wiring report (regenerable, not
                        hand-edited)
docs/                   memoria.md (TFM draft, built from the real results),
                        results.md, dataset-card.md, audit.md, threat-model.md,
                        spec-coverage.md, product-viability.md, defensa.md,
                        presentacion.md, video-guion.md, video-plan-rodaje.md,
                        demo-explicada.md,
                        roadmap.md, and
                        the per-study pages
openspec/changes/       SDD trail: proposal/spec/design/tasks/apply-progress
                        per work unit, with TDD evidence and disclosed budget
                        exceptions where a unit exceeded the 400-line review
                        target
CLAUDE.md               the normative specification and the append-only
                        bitácora operativa (build log)
```

## Optional developer assistance

[Ponytail](.ponytail/UPSTREAM.md) is vendored with immutable provenance and a
SHA-256 manifest. Codebase Memory MCP setup and the always-index convention are
documented in [`docs/development-assistance.md`](docs/development-assistance.md).
Both are local, read-mostly assistance — not application runtime dependencies.

## Scope and non-negotiables

Full detail in [`CLAUDE.md`](CLAUDE.md#41-decisiones-no-negociables). In short:
`FakeERPAdapter` is the confirmatory core (Odoo 19 is a post-core extension);
R4-risk operations are unconditionally denied; skills are versioned with an
enforced lifecycle (no direct `DRAFT → ACTIVE`); the test split freezes before the
confirmatory experiment; synthetic data only, no secrets ever committed.

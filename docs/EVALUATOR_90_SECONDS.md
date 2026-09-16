# ERP Agent OS — 90-second evaluator summary

> Convenience document for evaluation. The canonical scientific submission remains the frozen tag/release `v1.3-tfm-final`; this page does not redefine any result or claim.

## What is the problem?

A language model can make mistakes. In a chatbot, a mistake may remain an incorrect answer. In an ERP, a mistaken action can create or modify customers, opportunities, orders, inventory or invoices.

ERP Agent OS studies a narrower question than “can an LLM call an API?”:

**Who has authority to mutate enterprise state after the model has proposed an action?**

## What is ERP Agent OS?

A control plane between the agent and the ERP:

```text
user request
  -> probabilistic interpretation
  -> skill retrieval / abstention
  -> versioned contract
  -> deterministic policy + risk + approval
  -> registered runtime handler
  -> ERP mutation
  -> independent postcondition verification
  -> audit evidence
```

**Thesis principle:** the LLM proposes; the architecture authorizes; the runtime executes.

A skill is a versioned operational contract, not just a prompt or Python function. It can declare intent, schema, permissions, risk, approval, handler, idempotency and postconditions.

## What was actually evaluated?

Three systems were compared under the same model/provider/task/state/evaluator:

- **A — Direct agent**
- **B — Typed tools**
- **C — ERP Agent OS**

The confirmatory campaign `tfm-protocol-v2.1.2` closed as `RUN_COMPLETED / CLOSURE_VALID` with **21,478 observed executions** over a synthetic procedural benchmark with known reference state by construction.

The benchmark is the experimental instrument, not a claim that synthetic requests represent real companies or users.

## What did the experiment find?

### Supported

- **H1a:** C is not inferior to A in strict task success; C-A = **+25.3 pp**.
- **H2:** C uses about **468 fewer tokens than A** and **648 fewer than B** per execution.
- **H3a:** C is more stable across paraphrases; **OR = 9.35**.
- **H6:** abstention reduces false reuse by **8.6 pp**.
- **H7:** C improves complete audit reconstruction by **42.7 pp** versus A.

### Not supported — deliberately preserved

- **H1b:** no demonstrated task-success superiority over typed tools; C-B = **-1.5 pp**, p=0.286.
- **H4:** **19.0% unauthorized mutation** across the dangerous-scenario population, versus a preregistered target below 5%.
- **H5:** selective retrieval remains insufficient; selective accuracy **0.589**, false reuse **0.411**.

The most important lesson is that **confinement is not the same as danger recognition**. The architecture can constrain what code is allowed to do while still misclassifying an apparently legitimate but dangerous request.

The separate InjecAgent stress test observed **0/1,530 outside-contract unauthorized mutations** under explicit attacker-controlled content. That supports a confinement claim for that stress condition; it does **not** override H4 and does not prove general safety.

## What does the Odoo demo prove?

Odoo 19 is a separate end-to-end feasibility demonstration on a Development branch with demo data:

```text
R1 -> ALLOW -> write -> reread -> verified
R2 without approval -> REQUIRE_APPROVAL -> reread -> unchanged
approval -> same R2 -> ALLOW -> write -> reread -> verified
```

The positive control after approval matters: “nothing changed” is not accepted as evidence if the integration could not write in the first place.

Only 2/12 catalog skills are mapped to real Odoo models. This is a declared feasibility boundary, not hidden product completeness.

## How do I verify it?

Use the frozen academic tag:

```bash
git clone --branch v1.3-tfm-final --depth 1 https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
uv python install 3.12
uv sync --frozen --group dev
uv run python scripts/professor_demo.py --check
```

Expected final line:

```text
REVIEWER CHECK PASSED
```

Then launch the comparative demo:

```bash
uv run python scripts/professor_demo.py
```

No API key or Odoo credentials are required for the comparative evaluator path.

For the full evaluator workflow, see [`../PROFESSOR_QUICKSTART.md`](../PROFESSOR_QUICKSTART.md). For scientific results, see [`results-v2.1.md`](results-v2.1.md).
# ERP Agent OS — five-minute defense video

> Preparation aid only. This document does not change the frozen scientific claims in `v1.3-tfm-final`.

Target duration: **4:45–4:55**. Use the author's natural voice. Keep Odoo visible during the live feasibility segment; this should explain the project, not behave as a five-minute pitch deck.

## 0:00–0:35 — the business problem

**On screen:** ERP/CRM plus one sentence: `A mistake is no longer only text`.

**Voice:**

> A language model can make mistakes. In a chatbot, that mistake may remain an incorrect answer. In an ERP, a mistake can create or modify a customer, an order, stock or an invoice. My TFM starts from one question: how can we use AI agents without turning the probabilistic model into the final authority over enterprise state?

## 0:35–1:20 — the architecture

**On screen:** `user -> LLM -> governance -> runtime -> ERP -> verification`.

**Voice:**

> ERP Agent OS introduces an authority boundary. The LLM interprets the request and proposes a capability. Deterministic software then checks the skill contract, arguments, role, risk and approval. The runtime only executes registered handlers and, after execution, rereads the ERP to verify the effect and preserve evidence. The principle is simple: the LLM proposes; the architecture authorizes; the runtime executes.

## 1:20–2:30 — real Odoo demonstration

**On screen:** Odoo 19 Development. Show R1 allowed, R2 without approval, then the same R2 after approval.

**Voice:**

> The architecture is not only a diagram. I integrated it with Odoo 19 on a Development branch with demo data. Here an R1 operation is allowed, written and verified by a postcondition. Now I launch an R2 modification without approval: the system returns REQUIRE_APPROVAL and an independent reread confirms that Odoo has not changed. I then grant approval and execute exactly the same request. This time it writes. That positive control matters because it proves the previous absence of change was a real governance decision, not a broken integration.

## 2:30–3:35 — A/B/C experiment

**On screen:** A/B/C comparison plus a simplified results table.

**Voice:**

> To evaluate the proposal I compared three systems: A, a direct agent; B, typed tools; and C, ERP Agent OS. The confirmatory campaign closed with 21,478 observed executions. C was not inferior to A in task success, used about 468 fewer tokens than A and 648 fewer than B, was more stable across paraphrases and produced substantially more reconstructible audit evidence. But it did not demonstrate better task success than B. Governance adds control and traceability; it does not magically make the model more intelligent.

## 3:35–4:25 — the results that failed

**On screen:** `H4 = 19.0%`, `H5 = 0.589`, then `0/1,530 InjecAgent` labelled `confinement != detection`.

**Voice:**

> The most important results are precisely the ones that fail. In H4, 19 percent of the dangerous scenarios ended in an unauthorized mutation, far above the preregistered five-percent target. Retrieval reached a selective accuracy of 0.589. I do not hide those results: they define the current limit of the system. The external stress test produced zero outside-contract mutations in 1,530 explicit attack attempts, but that measures confinement. H4 shows that recognizing a dangerous request and confining what may execute are different problems.

## 4:25–4:55 — conclusion

**On screen:** `Control plane for ERP agents` plus the next three steps.

**Voice:**

> The conclusion of the TFM is not that I built a perfect agent. It is that separating probabilistic interpretation from deterministic authorization and execution provides measurable properties and makes the remaining failures explicit. The next step is to improve risk classification and retrieval, extend the Odoo mapping and validate the system with real users and organizations. ERP Agent OS is therefore a control plane between any agent and the ERP.

---

## Five short defense answers

### Why use a synthetic benchmark?

Because its role is to compare A, B and C under the same initial state with a reference action, policy and final state known by construction. That maximizes internal validity and reproducibility. It does not establish representativeness of real user language, so the thesis explicitly limits external validity and complements the benchmark with InjecAgent and an Odoo feasibility demo.

### How can the thesis discuss security if H4 fails?

It does not claim general safety. H4 is a material negative result: 19.0% unauthorized mutation. What the architecture can support is a narrower structural claim: when the contract and policy are correct, deterministic enforcement can confine what may execute. The central finding is that confinement and danger recognition are separate problems.

### Why are only 2 of 12 skills mapped to real Odoo?

The Odoo integration is a feasibility experiment, not the confirmatory backend. Two mapped skills are enough to demonstrate that the same contract/runtime can allow, require approval, write and verify against a real ERP. The A/B/C campaign remains on a controlled adapter so every system starts from the same state. Mapping the full catalog is productization work.

### Does H7 structurally favor C?

Partly, and the thesis says so. A and B do not produce skill version, Policy Engine decision or postcondition evidence, and the evaluator is not allowed to invent missing facts. H7 therefore measures an architectural property — reconstructibility of execution — rather than model intelligence.

### Is it production ready?

No. It is a reproducible prototype with end-to-end feasibility. Before production it still needs H4/H5 remediation, broader Odoo mapping, authentication and tenant isolation, secret management, durable/integrity-protected audit, observability/SLOs, recovery testing and validation with real users and organizations.

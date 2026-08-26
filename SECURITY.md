# Security policy

## Scope

ERP Agent OS is a research prototype developed as part of a master's thesis. It is **not** presented as a production-certified ERP security product and should not be used to justify unattended writes to production financial, HR, inventory, CRM or other high-impact enterprise systems without an independent security review.

The current confirmatory results are intentionally mixed. In particular, H4 did **not** meet its preregistered target: System C produced a 19.0% unauthorized-mutation rate across 315 dangerous scenarios, versus a target below 5%. This result must travel with any security discussion of the project.

A separate external stress test observed 0 outside-contract unauthorized mutations across 1,530 explicit compromised-model attack attempts. That experiment measures **confinement under explicit compromise**, not general danger recognition and not absolute security.

## Supported environment

The repository is tested as a research codebase on Python 3.12. The real-ERP integration is a feasibility demonstration only.

Real Odoo writes are permitted only through the guarded demonstration path and only against an explicitly identified **Development** instance with demo data. Production, staging and unspecified destinations are rejected by the demo guard.

The comparative A/B/C product-demo API is intentionally FakeERP-only and must not expose an interchangeable `odoo` backend.

## Reporting a vulnerability

Please do **not** publish credentials, secrets, customer data, exploit payloads containing real organizational information, or instructions that would place a real ERP instance at risk.

For vulnerabilities in the public research code, open a GitHub Security Advisory for this repository if available. If a private reporting channel is not available through GitHub, open a minimal issue that states that a security concern exists without including exploit details or secrets, so that a private channel can be established.

Include, when possible:

- affected commit or release;
- affected module or endpoint;
- prerequisites and threat model;
- minimal synthetic reproduction;
- observed impact;
- whether the issue can cause unauthorized state mutation;
- whether the issue affects FakeERP only or the guarded Odoo demonstration path.

## Credentials and data

Never commit:

- `.env` files;
- API keys or access tokens;
- Odoo credentials;
- private ERP URLs when disclosure is not intended;
- customer, employee, supplier or financial records;
- production database dumps;
- logs containing secrets or personal data.

The repository's committed research material is intended to remain synthetic or publicly licensed research material.

## Security invariants for demos

1. A blocked write is not evidence by itself. A positive control must prove that the same environment can write once the operation is legitimately approved.
2. The product-demo must not infer governance evidence for systems that do not produce it.
3. The product-demo must not calculate or invent a composite security score.
4. Odoo real execution must remain on the single guarded route rather than being exposed as a generic comparative backend.
5. Independent ERP re-reads are preferred over trusting the agent's self-reported execution result.

## Research findings are not vulnerability promises

`SUPPORTED` and `NOT SUPPORTED` in the thesis refer to preregistered experimental hypotheses. They are not CVSS ratings, product guarantees, certifications or warranties.

The software is distributed under the MIT License and therefore without warranty. See [`LICENSE`](LICENSE) and [`docs/results-v2.1.md`](docs/results-v2.1.md).

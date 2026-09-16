# Evaluator — start here

The canonical scientific submission is the frozen tag/release **`v1.3-tfm-final`**. This page is an evaluation convenience layer and does not alter the frozen evidence.

## 1. Understand the project in 90 seconds

Read [`docs/EVALUATOR_90_SECONDS.md`](docs/EVALUATOR_90_SECONDS.md).

In one sentence: **ERP Agent OS is a deterministic control plane between a probabilistic AI agent and ERP mutations — the LLM proposes, the architecture authorizes, the runtime executes.**

## 2. Reproduce the evaluator path

Use [`PROFESSOR_QUICKSTART.md`](PROFESSOR_QUICKSTART.md).

Minimal path from the frozen tag:

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

## 3. See the evidence

- Current confirmatory results: [`docs/results-v2.1.md`](docs/results-v2.1.md)
- One-page status: [`docs/tfm-current-status.md`](docs/tfm-current-status.md)
- Audit history: [`docs/audit.md`](docs/audit.md)
- Odoo feasibility demo: [`docs/odoo-demo.md`](docs/odoo-demo.md)

The main negative results are part of the contribution, not hidden backlog:

- H4: **19.0% unauthorized mutation**; preregistered target <5%.
- H5: selective accuracy **0.589**, false reuse **0.411**.
- H1b: no demonstrated task-success superiority over typed tools.

## 4. Defense / delivery aids

- Five-minute defense video: [`docs/DEFENSE_VIDEO_5MIN.md`](docs/DEFENSE_VIDEO_5MIN.md)
- UCM submission checklist: [`docs/SUBMISSION_CHECKLIST_UCM.md`](docs/SUBMISSION_CHECKLIST_UCM.md)

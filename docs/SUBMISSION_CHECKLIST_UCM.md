# TFM submission checklist — UCM Big Data / Data Science / AI

> Administrative/evaluator convenience document. It does not modify the frozen scientific result in `v1.3-tfm-final`.

## Deliverables

- [ ] Main technical report is within the **20-page body limit**. Cover, table of contents and annexes do not count; bibliography does.
- [ ] Final file name contains the student's first name and two surnames separated with underscores.
- [ ] Code is available through the public GitHub repository and all links open without requesting access.
- [ ] The project is reproducible from a clean clone.
- [ ] Conclusions are explicit and distinguish supported results, unsupported hypotheses and limitations.
- [ ] Annexes contain the deeper technical/reproducibility material referenced by the main text.
- [ ] Bibliography remains concise.

## Video

- [ ] Format: **MP4**.
- [ ] Duration: **<= 5:00**; practical target **4:45–4:55**.
- [ ] Preferably **<= 50 MB** where feasible.
- [ ] Includes the author's **voice-over**. Appearing on camera is not required.
- [ ] Explains the project, approach, conclusions and lessons learned; it is not only an elevator pitch.
- [ ] Shows the end-to-end Odoo behavior rather than using five minutes of static slides.

## Repository / evaluator path

Canonical academic state:

```text
v1.3-tfm-final
```

Clean evaluator path:

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

Launch the comparison UI:

```bash
uv run python scripts/professor_demo.py
```

No LLM API key or Odoo credential is required for this evaluator path.

## Last-day checks

- [ ] Open the repository in an incognito/private window.
- [ ] Open the video link in an incognito/private window if delivered by URL.
- [ ] Confirm the final PDF opens correctly and every figure/table is readable at 100% zoom.
- [ ] Confirm the final PDF still distinguishes the synthetic confirmatory benchmark from the Odoo feasibility demo.
- [ ] Confirm H4 and H5 remain visible as negative results rather than being softened into product claims.
- [ ] Confirm `0/1,530` is described as explicit-attack confinement evidence, not proof of general safety.
- [ ] Do **not** move or rewrite the canonical `v1.3-tfm-final` tag after submission.

## Recommended evaluator reading order

1. [`EVALUATOR_90_SECONDS.md`](EVALUATOR_90_SECONDS.md)
2. [`../PROFESSOR_QUICKSTART.md`](../PROFESSOR_QUICKSTART.md)
3. [`results-v2.1.md`](results-v2.1.md)
4. [`tfm-current-status.md`](tfm-current-status.md)
5. [`audit.md`](audit.md) only if methodological provenance is being reviewed in depth.

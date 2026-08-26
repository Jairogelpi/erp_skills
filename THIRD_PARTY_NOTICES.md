# Third-party notices

ERP Agent OS is licensed under MIT, but third-party datasets, benchmark material and publications retain their own licenses and attribution requirements. The project license does **not** relicense external material.

## InjecAgent

**Project:** InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents  
**Authors:** Qiusi Zhan, Zhixiang Liang, Zifan Ying, Daniel Kang  
**Source:** https://github.com/uiuc-kang-lab/InjecAgent  
**License:** MIT  
**Upstream license:** https://github.com/uiuc-kang-lab/InjecAgent/blob/main/LICENCE

ERP Agent OS uses InjecAgent as an external out-of-distribution security benchmark. Results derived from that benchmark are reported separately from the project's confirmatory ERP-Skills-Bench campaign.

The external stress result must be interpreted narrowly: 0 outside-contract unauthorized mutations were observed across 1,530 explicit attack attempts in the project's confinement test. This does not override the confirmatory H4 result and does not establish general safety.

## MASSIVE

**Project:** MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages  
**Copyright:** Amazon.com, Inc. or its affiliates  
**Source:** https://github.com/alexa/massive  
**Dataset mirror / metadata:** https://huggingface.co/datasets/AmazonScience/massive  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**License:** https://creativecommons.org/licenses/by/4.0/

ERP Agent OS uses the Spanish portion of MASSIVE only for an exploratory cross-author retrieval/enrichment study. MASSIVE is not an ERP dataset and is not part of the confirmatory benchmark; it tests whether the retrieval-description mechanism transfers across authors in a different intent-classification domain.

Suggested upstream citation:

> FitzGerald, J., Hench, C., Peris, C., Mackie, S., Rottmann, K., Sanchez, A., Nash, A., Urbach, L., Kakarala, V., Singh, R., Ranganath, S., Crist, L., Britan, M., Leeuwis, W., Tur, G., & Natarajan, P. (2022). MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages.

## Papers, specifications and documentation

References to papers, Odoo documentation, NIST material, Agent Skills, MCP and other specifications are citations/links rather than relicensing of those works. Their respective copyright and license terms remain with their publishers and authors.

## Repository-owned material

Unless a file or directory states otherwise, original software and documentation authored for ERP Agent OS are covered by the root [`LICENSE`](LICENSE) (MIT).

If new third-party material is added, update this file with at least: title, owner/authors, source, license, how it is used, and whether it participates in confirmatory, exploratory, external-stress or feasibility evidence.

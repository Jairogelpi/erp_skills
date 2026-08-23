# PROTOCOLO RETIRADO — NO ENTREGAR A ANOTADORES NI EJECUTAR

> **EVIDENCE-STATUS: superseded-before-system-evaluation**
>
> El autor ha decidido que no participarán anotadores humanos. Este documento
> se conserva únicamente como historial append-only del diseño v2. Ningún CSV
> debe completarse y ningún sistema A/B/C debe ejecutarse sobre este holdout.
> La sustitución normativa es `docs/tfm-closure-no-human-v2.1.md`; su recibo
> formal de supersesión se generará al implementar Task 1 del plan v2.1.

# Entrega humana del holdout prospectivo v2 (histórico)

## Estado actual

`EVIDENCE-STATUS-HISTORICAL: v2_candidates_sealed_awaiting_human_annotation`

El 13-08-2026 quedaron selladas 120 peticiones nuevas. No se ha ejecutado
ninguno de los sistemas A/B/C sobre ellas. El manifiesto canónico es:

`data/prospective_v2/bench_v2_candidate_seal_386fdf8b16f8283280d4f7127b1613fff5e0917e37a8bb11132896a06c63f037.json`

Su hash de candidatos es
`0f738bf7feaa9f31f67e2dc908d1efe16112cf20a50f6efe1baabb381493e799`.
El manifiesto también fija los hashes del código experimental, catálogo,
prompts y configuración de proveedores. Si cambia alguno, el finalizador
rechaza el holdout.

## Separación obligatoria

- Anotador A recibe únicamente `bench_v2_annotation_annotator_1.csv` y este
  código de anotación.
- Anotador B recibe únicamente `bench_v2_annotation_annotator_2.csv` y este
  código de anotación.
- Deben trabajar de forma independiente y sustituir el identificador genérico
  por un seudónimo estable y distinto.
- Ninguno puede consultar el archivo `bench_v2_author_proposals_*.jsonl`.
  Este contiene propuestas del autor, no verdad de referencia.
- No debe ejecutarse A/B/C, el retriever ni un LLM sobre las peticiones v2
  antes de terminar y congelar las anotaciones.

## Columnas que debe completar cada anotador

| Columna | Valor permitido |
|---|---|
| `annotator_id` | Seudónimo estable del humano; distinto en ambos CSV. |
| `annotated_intent` | Una de las 24 intenciones de la tabla inferior. |
| `annotated_skill` | Skill asociada o `sin_skill/abstención`. |
| `annotated_arguments_json` | Objeto JSON, por ejemplo `{"customer_name":"Acme"}`. |
| `annotated_decision` | `ALLOW`, `SIMULATE`, `REQUIRE_APPROVAL`, `DENY`, `CLARIFY` o `ABSTAIN`. |
| `annotated_risk_class` | `R0`, `R1`, `R2`, `R3` o `R4`. |
| `annotated_error_type` | `none` o una causa concreta y estable. |
| `annotated_case_label` | `NORMAL`, `NOISE` o `ADVERSARIAL`. |
| `clarification_required` | `true` o `false`. |
| `state_transition` | `MAY_CHANGE` o `UNCHANGED`. |
| `annotation_status` | `COMPLETE` solo después de revisar toda la fila. |
| `notes` | Justificación breve cuando exista ambigüedad. |

No se modifica `request_id` ni `request_text`. Las 120 filas deben quedar
completas. El validador bloquea filas ausentes, duplicadas, valores inválidos,
identificadores iguales o textos alterados.

## Código de intenciones

| Intención | Skill | Argumentos principales |
|---|---|---|
| `crm.create_opportunity.new` | `crm.create_opportunity` | `customer_name`, `expected_revenue` |
| `crm.create_opportunity.followup` | `crm.create_opportunity` | `customer_name`, `expected_revenue` |
| `crm.update_expected_revenue.adjust` | `crm.update_expected_revenue` | `opportunity_id`, `expected_revenue` |
| `crm.update_expected_revenue.correct` | `crm.update_expected_revenue` | `opportunity_id`, `expected_revenue` |
| `crm.detect_duplicate_contact.check` | `crm.detect_duplicate_contact` | `customer_name` |
| `crm.detect_duplicate_contact.merge_check` | `crm.detect_duplicate_contact` | `customer_name` |
| `contacts.search_contact.by_name` | `contacts.search_contact` | `query` |
| `contacts.search_contact.lookup` | `contacts.search_contact` | `query` |
| `sales.create_quote_draft.new` | `sales.create_quote_draft` | `customer_name` |
| `sales.create_quote_draft.for_lead` | `sales.create_quote_draft` | `customer_name` |
| `sales.add_quote_line.add_product` | `sales.add_quote_line` | `quote_id`, `product_name`, `quantity` |
| `sales.add_quote_line.add_service` | `sales.add_quote_line` | `quote_id`, `product_name`, `quantity` |
| `sales.confirm_order.validate` | `sales.confirm_order` | `order_id` |
| `sales.confirm_order.finalize` | `sales.confirm_order` | `order_id` |
| `purchasing.create_purchase_draft.new` | `purchasing.create_purchase_draft` | `supplier_name` |
| `purchasing.create_purchase_draft.restock` | `purchasing.create_purchase_draft` | `supplier_name` |
| `product.update_field.price` | `product.update_field` | `product_name`, `field`, `value` |
| `product.update_field.description` | `product.update_field` | `product_name`, `field`, `value` |
| `inventory.check_availability.single` | `inventory.check_availability` | `product_name` |
| `inventory.check_availability.reorder` | `inventory.check_availability` | `product_name` |
| `tasks.create_task.followup` | `tasks.create_task` | `title` |
| `tasks.create_task.reminder` | `tasks.create_task` | `title` |
| `billing.create_draft_invoice.from_order` | `billing.create_draft_invoice` | `customer_name` |
| `billing.create_draft_invoice.manual` | `billing.create_draft_invoice` | `customer_name` |

Ante una petición cancelada, ambigua o incompatible con el catálogo, el
anotador puede usar `sin_skill/abstención`; no debe forzar una reutilización.

## Cómo avanzar el protocolo

Después de recibir los dos CSV completos:

```powershell
uv run python scripts/advance_v2_holdout.py
```

El comando calcula acuerdo y Cohen's kappa. Si hay desacuerdos, crea
`bench_v2_adjudication.csv`; debe resolverlo una tercera persona distinta. Al
repetir el comando se crean dos paquetes de revisión de estados. Dos revisores
independientes deben marcar cada estado `ACCEPT` y cada fila `COMPLETE`. Un
rechazo bloquea la congelación y obliga a documentar y corregir el protocolo,
no a editar silenciosamente el gold.

Solo cuando el comando devuelva
`prospectively_frozen_unseen_ready_for_one_shot_evaluation` existirán el gold y
el manifiesto final. Entonces se podrá realizar una única corrida:

```powershell
uv run python scripts/run_experiment.py --real-llm --real-parser `
  --provider groq `
  --v2-gold data/prospective_v2/bench_v2_gold_<hash>.jsonl `
  --v2-manifest data/prospective_v2/bench_v2_final_freeze_<hash>.json
```

El runner verifica todos los hashes y deja un recibo ligado al gold. Si ese
recibo ya existe, rechaza otra corrida como confirmatoria.

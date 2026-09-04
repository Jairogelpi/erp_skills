# Storyboard final de presentación — ERP Agent OS

Este documento es **material auxiliar para construir el vídeo del TFM**.
La guía vigente exige un vídeo explicativo de máximo 5 minutos; no se
utiliza este fichero como fuente de resultados. Para cifras canónicas,
ver `docs/results-v2.1.md` y `docs/tfm-current-status.md`.

## 1. Problema — 20 s

**Se ve:** ejemplo de estado ERP persistente.

**Mensaje:** un error de un agente conectado a un ERP no es solo texto
incorrecto: puede mutar estado empresarial.

No presentar el cambio 15.000 → 27.600 € de la toma inicial como una
acción causada por un agente; es una escena preparada para ilustrar el
riesgo.

## 2. Frontera de autoridad — 30 s

**Se ve:** dos zonas.

```text
LLM / probabilístico          Arquitectura / determinista
interpreta y propone    ->    valida, autoriza, ejecuta y verifica
```

Frase: **el LLM propone; la arquitectura autoriza; el runtime ejecuta**.

## 3. Pipeline — 30 s

```text
request
 -> retrieval / abstention
 -> versioned skill contract
 -> policy + risk + approval
 -> deterministic runtime
 -> ERP adapter
 -> independent postcondition
 -> append-only audit evidence
```

## 4. Diseño experimental — 30 s

- A: agente directo.
- B: tools tipadas.
- C: ERP Agent OS.
- ERP-Skills-Bench-Proc v2.1: benchmark sintético/procedural con verdad
  de referencia conocida por construcción.
- **21.478 observaciones experimentales** procedentes de ejecuciones
  observadas sobre escenarios sintéticos.
- `RUN_COMPLETED / CLOSURE_VALID`.

El benchmark es el instrumento experimental del proyecto software, no
una muestra que se presente como representativa de usuarios reales.

## 5. Resultados que limitan la tesis — 45 s

- **H1b no soportada:** C no demuestra superioridad sobre B en STSR
  (C−B = -1,5 pp; p=0,286).
- **H4 no soportada:** 19,0 % de mutación no autorizada sobre **315
  escenarios peligrosos del benchmark confirmatorio**; objetivo <5 %.
- **H5 no soportada:** selective accuracy 0,589; false-reuse 0,411.

No resumir esto como «A/B son más seguros»: parte de sus DENY procede de
errores de ejecución y no constituye una detección homologable.

## 6. Resultados soportados — 45 s

- **H1a:** no inferioridad de C frente a A; +25,3 pp.
- **H2:** C consume ~468 tokens menos que A y ~648 menos que B.
- **H3a:** mayor estabilidad entre formulaciones; OR 9,35;
  p=2,2×10^-18.
- **H6:** abstención reduce false-reuse en 8,6 pp.
- **H7:** reconstrucción completa de auditoría +42,7 pp frente a A;
  p=2,85×10^-112, con la salvedad estructural declarada en memoria.
- **H8:** descriptiva; no demuestra ahorro monetario observado.

## 7. Confinamiento ≠ detección — 40 s

**H4:** petición peligrosa ambigua/plausible → el sistema no alcanza el
criterio de seguridad activa.

**Stress test externo InjecAgent:** 510 payloads × 3 superficies =
1.530 intentos → **0/1.530 mutaciones no autorizadas fuera de contrato**.

Mensaje: ese cero es evidencia de confinamiento en ese stress test, no
prueba de seguridad general y no reemplaza H4.

## 8. Odoo 19 Development — 40 s

**Se ve:** demo end-to-end con datos demo.

1. R1 → ALLOW → escritura → relectura.
2. R2 sin aprobación → REQUIRE_APPROVAL → relectura sin cambio.
3. Aprobación → ALLOW → escritura → nueva relectura.

Llamarlo **demostración de factibilidad sobre Odoo 19 Development con
datos demo**, nunca validación en producción. La integración actual
mapea 2/12 skills del catálogo.

## 9. Productivización — 25 s

Antes de producción:

- cerrar H4 y reevaluar prospectivamente;
- mejorar retrieval;
- ampliar mapeo Odoo;
- identidad, secretos y multi-tenant;
- persistencia e integridad de auditoría;
- observabilidad/SLO y recuperación;
- UX de aprobación/aclaración.

## 10. Cierre — 15 s

> La gobernanza aporta propiedades medibles, pero no convierte por sí
> sola un agente en seguro. El valor de ERP Agent OS está en separar
> interpretación probabilística de autoridad empresarial determinista y
> hacer esa frontera verificable y auditable.

## Terminología bloqueada para entrega

Usar:

- «21.478 observaciones experimentales»;
- «ejecuciones observadas sobre escenarios sintéticos»;
- «315 escenarios peligrosos del benchmark confirmatorio»;
- «Odoo 19 Development con datos demo»;
- «consume menos tokens»;
- «0/1.530 mutaciones fuera de contrato en el stress test específico».

Evitar:

- «observaciones reales» / «escenarios reales» para el benchmark;
- «seguro» / «inmune»;
- «validado en producción»;
- «ahorra X €»;
- «más barato» cuando solo se está midiendo consumo de tokens.

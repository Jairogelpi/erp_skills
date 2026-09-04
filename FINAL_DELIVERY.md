# ERP Agent OS — auditoría final de entrega TFM

Este fichero marca el **freeze documental de entrega**. La referencia
estable de entrega es la rama `tfm-final-2026`, creada sobre el commit que
incorpora este documento. El PDF entregado debe registrar el SHA exacto de
esa referencia.

## 1. Fuente científica canónica

- Protocolo: `tfm-protocol-v2.1.2`.
- Estado: `RUN_COMPLETED / CLOSURE_VALID`.
- Resultados: `docs/results-v2.1.md`.
- Resumen de claims: `docs/tfm-current-status.md`.
- Encuadre del benchmark: `docs/tfm-benchmark-positioning.md`.

Estados vigentes:

- H1a, H2, H3a, H6, H7: **soportadas**.
- H1b, H4, H5: **no soportadas**.
- H3b, H8: **descriptivas**.

## 2. Terminología de datos bloqueada

La campaña se describe como:

- **21.478 observaciones experimentales**;
- **ejecuciones observadas sobre escenarios sintéticos/procedurales**;
- H4: **315 escenarios peligrosos del benchmark confirmatorio**.

ERP-Skills-Bench-Proc v2.1 se presenta como **instrumento experimental de
un proyecto técnico software**, no como el objeto de un TFM de análisis de
dataset ni como muestra representativa de usuarios/empresas.

Los documentos de entrega no deben sugerir que las frecuencias del
benchmark son prevalencias organizativas.

## 3. Claims numéricos bloqueados

| Hipótesis | Claim de entrega |
|---|---|
| H1a | C no es inferior a A; C−A = +25,3 pp, margen NI -5 pp |
| H1b | no se demuestra superioridad sobre B; C−B = -1,5 pp; p=0,286 |
| H2 | C consume ~468 tokens menos que A y ~648 menos que B |
| H3a | OR 9,35; p=2,2×10^-18 |
| H4 | 19,0 % de mutación no autorizada sobre 315 escenarios peligrosos del benchmark; objetivo <5 % |
| H5 | selective accuracy 0,589; false-reuse 0,411 |
| H6 | false-reuse -8,6 pp con abstención |
| H7 | reconstrucción completa +42,7 pp frente a A; p=2,85×10^-112; salvedad estructural declarada |
| H8 | sensibilidad modelada; no ahorro monetario observado |

Stress test externo InjecAgent: **0/1.530 mutaciones no autorizadas fuera
de contrato** sobre 510 payloads × 3 superficies. Este resultado es de
confinamiento bajo el stress test específico; no prueba seguridad general
y no sustituye H4.

## 4. Odoo

La formulación única de entrega es:

> **Demostración de factibilidad end-to-end sobre Odoo 19 Development con
> datos demo.**

- Producción y staging se rechazan por código antes de escribir.
- La demo no pertenece a la inferencia confirmatoria A/B/C.
- Cobertura actual: 2/12 skills.
- No usar «validación en producción».

## 5. Documentos activos alineados

- `README.md`
- `CITATION.cff`
- `docs/results-v2.1.md`
- `docs/tfm-current-status.md`
- `docs/tfm-benchmark-positioning.md`
- `docs/tfm-submission-readiness.md`
- `docs/defensa-v2.1-final.md`
- `docs/video-guion.md`
- `docs/video-plan-rodaje.md`
- `docs/presentacion.md`
- `docs/demo-explicada.md`
- `docs/odoo-demo.md`
- `docs/product-viability.md`
- `docs/roadmap.md`

Los ficheros `docs/defensa.md`, `docs/results.md`,
`docs/experiment-protocol.md` y `docs/memoria.md` se mantienen únicamente
como puntos de compatibilidad/aviso de versión y redirigen a las fuentes
vigentes. Los artefactos generados `reports/memoria.html` y
`reports/memoria.pdf`, que correspondían a una memoria anterior, se han
retirado de la rama final para evitar una segunda versión aparentemente
canónica.

## 6. Excepciones históricas intencionales

No se reescribe contenido histórico que forma parte de la procedencia del
proyecto, especialmente:

- `CLAUDE.md` como especificación/bitácora append-only;
- `docs/audit.md` como registro de auditoría del instrumento;
- `openspec/changes/**` como propuestas y tareas históricas;
- artefactos crudos/congelados de `data/**`.

Una formulación antigua dentro de esos registros no constituye un claim de
entrega y se conserva precisamente para no reescribir la historia del
experimento.

## 7. Auditoría de enlaces y acceso

El repositorio está configurado con **visibilidad pública** en GitHub.
Los destinos relativos utilizados por el README y por los documentos
canónicos se han resuelto contra el árbol de `main`, incluidos:

- `docs/results-v2.1.md`
- `docs/tfm-current-status.md`
- `docs/tfm-closure-no-human-v2.1.md`
- `docs/audit.md`
- `docs/tfm-benchmark-positioning.md`
- `docs/product-demo.md`
- `docs/odoo-demo.md`
- `docs/product-viability.md`
- `LICENSE`
- `SECURITY.md`
- `CITATION.cff`

La documentación externa principal de `uv` también resuelve públicamente.
La visibilidad pública del repositorio evita que Carlos Ortega o Santiago
Mota necesiten permisos adicionales para leerlo.

## 8. Vídeo del TFM

Fuentes de narración:

- `docs/video-guion.md`
- `docs/video-plan-rodaje.md`

El guion está alineado con la memoria y tiene objetivo aproximado de
**4:20**, por debajo del máximo de **5:00**.

Antes de subir el MP4 final deben comprobarse sobre el fichero multimedia:

- duración <= 5:00;
- contenedor/formato MP4;
- voz del autor;
- tamaño recomendado <= ~50 MB cuando sea razonablemente posible;
- ausencia de credenciales/datos identificables en pantalla;
- mismos claims numéricos que esta auditoría.

**El MP4 no está versionado en este repositorio**, por lo que esta auditoría
certifica el guion y los claims, no las propiedades técnicas de un fichero
de vídeo que no forme parte del árbol Git.

## 9. Entregables y fecha

TFM ordinario:

- memoria: PDF/DOCX/HTML admitidos por la guía;
- código/anexos: repositorio accesible;
- vídeo explicativo: MP4, máximo 5 minutos;
- fecha de entrega comunicada para el TFM: **17 de septiembre de 2026**.

La competición de becas es independiente y tiene su propia fecha; no debe
confundirse con el entregable obligatorio del TFM.

Nombre de memoria recomendado:

`Jairo_Gelpi_Moreno_TFM_ERP_Agent_OS_FINAL.pdf`

Nombre de vídeo recomendado:

`Jairo_Gelpi_Moreno_TFM_ERP_Agent_OS_VIDEO.mp4`

## 10. Regla de freeze

Tras crear `tfm-final-2026` no realizar cambios en código, protocolo,
resultados o documentación de entrega sin repetir esta auditoría y volver a
actualizar la referencia del PDF. La finalidad es que PDF, vídeo y
repositorio correspondan a una única versión identificable.

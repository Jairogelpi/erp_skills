# ERP Agent OS — auditoría final de entrega TFM

Este fichero marca el **freeze documental de entrega**. La referencia canónica de entrega es el tag/release **`v1.3-tfm-final`**, que debe apuntar al mismo commit que la rama estable `tfm-final-2026`. El PDF entregado debe registrar el SHA exacto de ese estado congelado.

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
- `PROFESSOR_QUICKSTART.md`
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

## 7. Auditoría de enlaces, PR y acceso

El repositorio está configurado con **visibilidad pública** en GitHub.
Los destinos relativos utilizados por el README y por los documentos
canónicos se han resuelto, incluidos:

- `PROFESSOR_QUICKSTART.md`
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

El PR histórico `#2` (`codex/competition-readiness`) se ha cerrado sin merge de
forma deliberada: era una rama anterior al cierre v2.1.2, no era mergeable con
el estado final y contenía documentación/artefactos ya superados. No existe una
funcionalidad final pendiente que deba recuperarse mediante el merge de ese PR.

La visibilidad pública del repositorio evita que los tutores necesiten permisos adicionales para leerlo.

## 8. Instalación y prueba por un evaluador

La ruta canónica está documentada en `PROFESSOR_QUICKSTART.md` y no requiere
GNU make, API keys ni Odoo para probar el artefacto principal.

Secuencia prevista:

```text
git clone --branch v1.3-tfm-final --depth 1 ...
uv python install 3.12
uv sync --frozen --group dev
uv run python scripts/professor_demo.py --check
uv run python scripts/professor_demo.py
```

El `--check` ejecuta el mismo camino que CI y verifica:

- evidencia confirmatoria legible;
- A/B/C operativos;
- aprobación R2 sin mutación previa;
- control positivo tras aprobar;
- auditoría;
- `npm ci` sobre `demo-ui/package-lock.json`;
- typecheck TypeScript;
- build Vite;
- arranque HTTP real de API y UI;
- proxy UI → API operativo.

La demo comparativa usa `FakeERP` reproducible. Odoo y los proveedores LLM son
opcionales y están fuera de la ruta mínima de evaluación.

## 9. Vídeo del TFM

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
de vídeo que no forma parte del árbol Git.

## 10. Entregables y fecha

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

## 11. Freeze final

- **Tag/release canónico:** `v1.3-tfm-final`.
- **Rama estable de espejo:** `tfm-final-2026`.
- `main` puede continuar evolucionando después de la entrega; la referencia académica permanente es el tag.
- `v1.0-tfm`, `v1.1-tfm-final` y `v1.2-tfm-final` se conservan únicamente como snapshots históricos y no son la fuente final de evaluación.
- La fuente de claims sigue siendo `docs/results-v2.1.md` bajo `tfm-protocol-v2.1.2`.

A partir del tag final, cualquier cambio de código, protocolo, resultados o documentación científica pertenece a una versión posterior y no modifica el artefacto académico entregado.

# TFM — checklist final de entrega

Este documento concentra las comprobaciones previas a la entrega del Trabajo Fin de Máster. No introduce evidencia nueva ni modifica resultados.

## 1. Memoria

Verificado el 2026-08-27 contra `Jairo_Gelpi_Moreno_TFM_ERP_Agent_OS_FINAL_CORREGIDO (2).docx` (con el commit SHA ya insertado en Anexo A — ver §7 más abajo). Lo marcado con ✅ se comprobó programáticamente o leyendo el documento entero; lo que sigue en `[ ]` no se pudo verificar desde aquí (requiere abrir el DOCX en Word/paginado real) y queda pendiente de una pasada visual antes de generar el PDF final.

- [x] Portada con autor, título, máster, tutores y curso académico. *(Jairo Gelpi Moreno · Máster en Big Data, Data Science e IA · UCM · tutores Carlos Ortega y Santiago Mota · curso 2025–2026 — presentes)*
- [x] Índice actualizado. *(11 secciones + Resumen ejecutivo + Referencias + Anexos, con paginación 1–17; cuadra con la estructura real del documento)*
- [ ] Memoria principal <= 20 caras, excluyendo portada, índice y anexos. *(el índice interno ya declara que el cuerpo va de la cara 1 a la 14 — dentro del límite —, pero el recuento de caras real depende de la paginación de Word, no verificable desde código; confirmar visualmente)*
- [x] Arial/Verdana y tamaño legible conforme a la guía. *(fuente Arial en todo el documento, tamaños 9–11pt, verificado programáticamente)*
- [x] Resumen ejecutivo y palabras clave.
- [x] Problema, estado de la cuestión, objetivos, arquitectura, implementación, datos, metodología, resultados, discusión, productivización y conclusiones. *(las 11 secciones están presentes y en ese orden)*
- [x] Resultados positivos y negativos reportados sin reformulación post hoc. *(§8.1: "el resultado no es uniformemente favorable... cinco endpoints apoyan la propuesta y tres no lo hacen")*
- [x] H4 y H5 identificadas explícitamente como no soportadas. *(§8.3, Anexo B, Tabla 6)*
- [x] Diferencia entre confinamiento y detección explicada. *(§9.2, título literal "Seguridad: confinamiento no equivale a detección")*
- [x] Integración con Odoo presentada como factibilidad, no como réplica confirmatoria. *(Anexo B: "las demos de Odoo se consideran evidencia de factibilidad, no causalidad sobre H1-H8")*
- [ ] Bibliografía breve y homogénea. *(9 referencias presentes con formato consistente; juicio de "homogeneidad" de estilo de cita requiere revisión manual, no automatizable con confianza)*
- [x] Derechos de uso de datos, privacidad/GDPR y procedencia de InjecAgent documentados. *(§6.5 y Anexo D)*
- [x] Declaración transparente de uso de asistentes de IA incluida en anexos. *(Anexo D, párrafo "Declaración de uso de IA: durante el desarrollo se utilizaron asistentes de IA...")*

## 2. Reproducibilidad del repositorio

Ejecutar desde un clon limpio antes de entregar:

```bash
uv sync --group dev
uv run ruff check .
uv run mypy src
uv run pytest
make verify-tfm-closure
```

El último comando debe terminar en `CLOSURE_VALID` usando los artefactos confirmatorios versionados.

**Verificado el 2026-08-27 desde clon limpio** (commit `e930c7d2ca07bcde7d02c580bd8ee458b3e65eec`, branch `product-demo-unified-v2`): `ruff check .` → All checks passed; `mypy src` → Success (66 files); `pytest` → **895/895 passed** (233.61s); `verify-tfm-closure --final` → **`CLOSURE_VALID`**. `demo-preflight` también en verde (confirmatorio, A/B/C, Skill Studio); el único WARN es Odoo live, esperado — el guardián rechaza correctamente escribir contra un host que no sea development/local.

## 3. Claims

Fuente canónica: `docs/results-v2.1.md` y resumen en `docs/tfm-current-status.md`.

**Soportadas:** H1a, H2, H3a, H6, H7.  
**No soportadas:** H1b, H4, H5.  
**Descriptivas/no direccionales:** H3b, H8.

No utilizar en portada, README, vídeo o defensa claims incompatibles con esta tabla.

## 4. Datos y privacidad

- ERP-Skills-Bench-Proc v2.1: sintético y generado por el autor.
- InjecAgent: benchmark público bajo licencia MIT, utilizado con atribución.
- Odoo: solo Development con datos demo; producción y staging rechazados por `require_development_instance()`.
- No versionar credenciales, `.env`, peticiones reales identificables ni datos de empresa.

## 5. Entregables

- [ ] Memoria DOCX/PDF final. *(borrador `(2).docx` con SHA en Anexo A ya generado; falta pasada visual de paginación/bibliografía de §1 y exportar el PDF definitivo)*
- [ ] Vídeo MP4 <= 5 minutos. *(`docs/GUION-DEFINITIVO.md`: 7/8 tomas grabadas, cierre pendiente de grabar; guion actualmente ~5:28 de narración a ritmo normal, por encima del límite — ver "candidatos de recorte" en ese documento)*
- [ ] Repositorio público y accesible para Carlos Ortega y Santiago Mota. *(no verificable desde este entorno — confirmar visibilidad del repo y acceso de los tutores manualmente)*
- [x] Anexos con código, protocolo, resultados completos y artefactos de reproducción. *(Anexos A-G presentes en el DOCX; Anexo A ahora incluye el commit de entrega)*
- [ ] Comprobar todos los enlaces desde una sesión no autenticada. *(no verificable desde este entorno)*

## 6. Defensa

El autor debe poder explicar sin apoyarse en el texto:

1. Por qué el benchmark es sintético y qué gana/pierde con ello.
2. Cómo se garantiza la independencia entre oráculos y sistema evaluado.
3. Diferencias exactas entre A, B y C.
4. Qué mide STSR.
5. Por qué H1b no se soporta.
6. Por qué H4 falla y por qué eso no contradice el stress test 0/1.530.
7. Qué significa que H5 falle.
8. Por qué la abstención mejora H6.
9. Qué cambió entre v2.1.1 y v2.1.2 y por qué el cambio no se ocultó.
10. Qué falta para convertir el prototipo en un producto empresarial.

## 7. Freeze de entrega

Antes de generar el ZIP/PDF definitivo, registrar el commit exacto de entrega en la memoria o en un fichero de entrega. A partir de ese punto, cualquier cambio que afecte a resultados, cifras o protocolo requiere una nueva revisión completa de coherencia.

**Commit de entrega registrado (2026-08-27):** `32e675bfd7ca1f7d7dfff8fb8bc6684093125ab7` (branch `product-demo-unified-v2`) — sustituye a `e930c7d2ca07bcde7d02c580bd8ee458b3e65eec` (mismo `CLOSURE_VALID`, este además corrige dos frases del guion del vídeo que afirmaban más de lo que esa toma demuestra). Repetido el cierre completo en clon limpio sobre este commit: ruff/mypy/pytest 895-895/`CLOSURE_VALID`/`demo-preflight` todo en verde, igual que en la primera pasada. Insertado en el README (sección "TFM delivery freeze"); **el Anexo A del DOCX sigue con el SHA anterior** — actualizarlo antes de generar el PDF definitivo si se usa este commit como entrega. Cualquier commit posterior a este no está cubierto por la memoria entregada — si se toca código, resultados o protocolo después de este punto, repetir §2 y esta sección con el nuevo SHA.
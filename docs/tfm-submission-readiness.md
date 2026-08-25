# TFM — checklist final de entrega

Este documento concentra las comprobaciones previas a la entrega del Trabajo Fin de Máster. No introduce evidencia nueva ni modifica resultados.

## 1. Memoria

- [ ] Portada con autor, título, máster, tutores y curso académico.
- [ ] Índice actualizado.
- [ ] Memoria principal <= 20 caras, excluyendo portada, índice y anexos.
- [ ] Arial/Verdana y tamaño legible conforme a la guía.
- [ ] Resumen ejecutivo y palabras clave.
- [ ] Problema, estado de la cuestión, objetivos, arquitectura, implementación, datos, metodología, resultados, discusión, productivización y conclusiones.
- [ ] Resultados positivos y negativos reportados sin reformulación post hoc.
- [ ] H4 y H5 identificadas explícitamente como no soportadas.
- [ ] Diferencia entre confinamiento y detección explicada.
- [ ] Integración con Odoo presentada como factibilidad, no como réplica confirmatoria.
- [ ] Bibliografía breve y homogénea.
- [ ] Derechos de uso de datos, privacidad/GDPR y procedencia de InjecAgent documentados.
- [ ] Declaración transparente de uso de asistentes de IA incluida en anexos.

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

- [ ] Memoria DOCX/PDF final.
- [ ] Vídeo MP4 <= 5 minutos.
- [ ] Repositorio público y accesible para Carlos Ortega y Santiago Mota.
- [ ] Anexos con código, protocolo, resultados completos y artefactos de reproducción.
- [ ] Comprobar todos los enlaces desde una sesión no autenticada.

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
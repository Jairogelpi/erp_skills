# TFM — checklist final de entrega

Este documento concentra las comprobaciones previas a la entrega del
Trabajo Fin de Máster. No introduce evidencia nueva ni modifica
resultados.

## 1. Memoria

- [x] Portada con autor, título, máster, tutores y curso académico.
- [x] Índice actualizado.
- [x] Memoria principal dentro del límite indicado por la guía; portada,
      índice y anexos tratados conforme a sus reglas de cómputo.
- [x] Arial/Verdana y tamaño legible conforme a la guía.
- [x] Resumen ejecutivo y palabras clave.
- [x] Problema, estado de la cuestión, objetivos, arquitectura,
      implementación, datos, metodología, resultados, discusión,
      productivización y conclusiones.
- [x] Se declara explícitamente que el TFM es un **proyecto técnico
      aplicado** y que ERP-Skills-Bench-Proc v2.1 es un **instrumento
      experimental**, no el objeto de un TFM de análisis de dataset.
- [x] Se describe el benchmark como sintético/procedural y se separan
      validez interna y validez externa.
- [x] Para la campaña se usa «21.478 observaciones experimentales» o
      «ejecuciones observadas sobre escenarios sintéticos».
- [x] Para H4 se usa «315 escenarios peligrosos del benchmark
      confirmatorio».
- [x] La interpretabilidad se formula como explicabilidad/trazabilidad
      operacional (petición -> skill -> argumentos -> policy -> aprobación
      -> ejecución -> postcondición), sin presentar SHAP/LIME como
      requisito artificial de un sistema que no entrena un modelo
      predictivo propio.
- [x] Resultados positivos y negativos reportados sin reformulación post
      hoc.
- [x] H4 y H5 identificadas explícitamente como no soportadas.
- [x] Diferencia entre confinamiento y detección explicada.
- [x] Integración con Odoo presentada como factibilidad sobre
      **Development con datos demo**, no como réplica confirmatoria ni
      validación en producción.
- [x] Bibliografía breve y homogénea.
- [x] Derechos de uso de datos, privacidad/GDPR y procedencia de
      InjecAgent documentados.
- [x] Declaración transparente de uso de asistentes de IA incluida en
      anexos.

## 2. Reproducibilidad del repositorio

Verificado sobre el commit final de entrega mediante CI y cierre de protocolo.
La CI debe permanecer verde en la referencia congelada.

```bash
uv sync --group dev
uv run ruff check .
uv run mypy src
uv run pytest
make verify-tfm-closure
```

El último comando debe terminar en `CLOSURE_VALID` usando los artefactos
confirmatorios versionados.

## 3. Claims

Fuente canónica: `docs/results-v2.1.md` y resumen en
`docs/tfm-current-status.md`.

**Soportadas:** H1a, H2, H3a, H6, H7.  
**No soportadas:** H1b, H4, H5.  
**Descriptivas/no direccionales:** H3b, H8.

No utilizar en memoria, README, vídeo o material de evaluación claims
incompatibles con esta tabla.

Para el encuadre metodológico y la terminología sobre el benchmark, usar
`docs/tfm-benchmark-positioning.md`. Este documento no sustituye a
`docs/results-v2.1.md` como fuente de resultados.

## 4. Datos y privacidad

- [x] ERP-Skills-Bench-Proc v2.1: sintético y generado por el autor;
      instrumento experimental de la evaluación confirmatoria.
- [x] Las 21.478 filas son observaciones experimentales de ejecuciones del
      sistema sobre escenarios sintéticos; no registros procedentes de
      usuarios o empresas.
- [x] InjecAgent: benchmark público bajo licencia MIT, utilizado con
      atribución.
- [x] Odoo: solo Development con datos demo; producción y staging rechazados
      por `require_development_instance()`.
- [x] No se versionan credenciales, `.env`, peticiones identificables ni datos
      de empresa en los materiales de entrega.

## 5. Entregables

- [x] Memoria PDF final preparada.
- [x] Nombre de la memoria incluye nombre y dos apellidos.
- [ ] Vídeo **MP4** de máximo **5 minutos** — pendiente del fichero multimedia final.
- [ ] Tamaño recomendado del vídeo <= ~50 MB cuando sea posible — pendiente del MP4 final.
- [ ] Voz del autor incluida — pendiente de validar sobre el MP4 final; no es obligatorio aparecer en cámara.
- [x] Repositorio público y accesible sin autenticación.
- [x] Anexos/código/protocolo/resultados completos accesibles mediante el
      repositorio.
- [x] Enlaces canónicos del README y documentos de entrega resueltos.
- [x] Commit final de entrega registrado y referencia estable preparada.

## 6. Vídeo

Fuentes canónicas: `docs/video-guion.md` y
`docs/video-plan-rodaje.md`.

El guion está alineado con la memoria. Sobre el MP4 final todavía debe
comprobarse que el audio conserva exactamente estos límites:

- H1b: no se demuestra superioridad sobre B.
- H4: 19,0 % sobre 315 escenarios peligrosos del benchmark; criterio
  <5 %, no soportada.
- H5: retrieval no alcanza el punto operativo.
- H2: «consume menos tokens», no «ahorra X euros».
- InjecAgent: 0/1.530 mutaciones fuera de contrato en el stress test;
  no prueba seguridad general.
- Odoo: Development + datos demo + factibilidad.

## 7. Explicación que debe poder dar el autor

1. Por qué el benchmark es sintético y qué gana/pierde con ello.
2. Por qué el benchmark es un instrumento de evaluación de un proyecto
   software y no el objeto de un TFM de análisis de dataset.
3. Cómo se garantiza la independencia entre oráculos y sistema evaluado.
4. Diferencias exactas entre A, B y C.
5. Qué mide STSR.
6. Por qué H1b no se soporta.
7. Por qué H4 falla y por qué eso no contradice el stress test 0/1.530.
8. Qué significa que H5 falle.
9. Por qué la abstención mejora H6.
10. Qué significa interpretabilidad operacional en ERP Agent OS y cómo
    H7 la mide.
11. Qué falta para producción.

## 8. Freeze de entrega

La referencia final del repositorio debe apuntar a un único commit y la
release de entrega debe corresponder a ese mismo estado. A partir de ese
punto, cualquier cambio que afecte a resultados, cifras o protocolo requiere
una nueva revisión completa de coherencia. El único entregable todavía no
certificable desde el repositorio es el MP4 final, porque no forma parte del
árbol Git.

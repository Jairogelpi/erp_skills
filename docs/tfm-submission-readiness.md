# TFM — checklist final de entrega

Este documento concentra las comprobaciones previas a la entrega del
Trabajo Fin de Máster. No introduce evidencia nueva ni modifica
resultados.

## 1. Memoria

- [ ] Portada con autor, título, máster, tutores y curso académico.
- [ ] Índice actualizado.
- [ ] Memoria principal dentro del límite indicado por la guía; portada,
      índice y anexos tratados conforme a sus reglas de cómputo.
- [ ] Arial/Verdana y tamaño legible conforme a la guía.
- [ ] Resumen ejecutivo y palabras clave.
- [ ] Problema, estado de la cuestión, objetivos, arquitectura,
      implementación, datos, metodología, resultados, discusión,
      productivización y conclusiones.
- [ ] Se declara explícitamente que el TFM es un **proyecto técnico
      aplicado** y que ERP-Skills-Bench-Proc v2.1 es un **instrumento
      experimental**, no el objeto de un TFM de análisis de dataset.
- [ ] Se describe el benchmark como sintético/procedural y se separan
      validez interna y validez externa.
- [ ] Para la campaña se usa «21.478 observaciones experimentales» o
      «ejecuciones observadas sobre escenarios sintéticos».
- [ ] Para H4 se usa «315 escenarios peligrosos del benchmark
      confirmatorio».
- [ ] La interpretabilidad se formula como explicabilidad/trazabilidad
      operacional (petición -> skill -> argumentos -> policy -> aprobación
      -> ejecución -> postcondición), sin presentar SHAP/LIME como
      requisito artificial de un sistema que no entrena un modelo
      predictivo propio.
- [ ] Resultados positivos y negativos reportados sin reformulación post
      hoc.
- [ ] H4 y H5 identificadas explícitamente como no soportadas.
- [ ] Diferencia entre confinamiento y detección explicada.
- [ ] Integración con Odoo presentada como factibilidad sobre
      **Development con datos demo**, no como réplica confirmatoria ni
      validación en producción.
- [ ] Bibliografía breve y homogénea.
- [ ] Derechos de uso de datos, privacidad/GDPR y procedencia de
      InjecAgent documentados.
- [ ] Declaración transparente de uso de asistentes de IA incluida en
      anexos.

## 2. Reproducibilidad del repositorio

Ejecutar desde un clon limpio antes de entregar:

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

- ERP-Skills-Bench-Proc v2.1: sintético y generado por el autor;
  instrumento experimental de la evaluación confirmatoria.
- Las 21.478 filas son observaciones experimentales de ejecuciones del
  sistema sobre escenarios sintéticos; no registros procedentes de
  usuarios o empresas.
- InjecAgent: benchmark público bajo licencia MIT, utilizado con
  atribución.
- Odoo: solo Development con datos demo; producción y staging rechazados
  por `require_development_instance()`.
- No versionar credenciales, `.env`, peticiones identificables ni datos
  de empresa.

## 5. Entregables

- [ ] Memoria DOCX/PDF final.
- [ ] Nombre de la memoria incluye nombre y dos apellidos.
- [ ] Vídeo **MP4** de máximo **5 minutos**.
- [ ] Objetivo recomendado de vídeo: no más de ~50 MB cuando sea posible.
- [ ] Voz del autor incluida; no es obligatorio aparecer en cámara.
- [ ] Repositorio público y accesible para Carlos Ortega y Santiago Mota.
- [ ] Anexos/código/protocolo/resultados completos accesibles mediante el
      repositorio.
- [ ] Comprobar enlaces desde una sesión no autenticada.
- [ ] Registrar el commit exacto de entrega y congelar una referencia
      estable de entrega.

## 6. Vídeo

Usar como fuente `docs/video-guion.md` y
`docs/video-plan-rodaje.md`.

Comprobar que el audio dice exactamente:

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

Antes de generar el paquete definitivo, registrar el commit exacto de
entrega. A partir de ese punto, cualquier cambio que afecte a resultados,
cifras o protocolo requiere una nueva revisión completa de coherencia.
Cambios puramente documentales posteriores deben evitarse para que PDF,
vídeo y repositorio apunten a una única versión.

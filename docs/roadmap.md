# Hoja de ruta final — ERP Agent OS

Esta hoja sustituye planes históricos anteriores. La evidencia
confirmatoria vigente es `tfm-protocol-v2.1.2` y su estado es
`RUN_COMPLETED / CLOSURE_VALID`.

## Punto de partida

- 21.478 observaciones experimentales de ejecuciones sobre un benchmark
  sintético/procedural.
- H1a, H2, H3a, H6, H7 soportadas.
- H1b, H4, H5 no soportadas.
- H3b, H8 descriptivas.
- Odoo 19: demostración Development con datos demo, 2/12 skills mapeadas.

## Prioridad 1 — seguridad activa

H4 observa 19,0 % de mutaciones no autorizadas sobre 315 escenarios
peligrosos del benchmark confirmatorio, frente al objetivo <5 %.

Trabajo:

1. revisar las cinco categorías que fallan;
2. endurecer policy/contratos sin reutilizar el test como objetivo de
   ajuste;
3. construir una nueva población prospectiva;
4. volver a congelar y medir antes de ampliar cualquier claim de
   seguridad.

## Prioridad 2 — retrieval y abstención

H5 no alcanza el punto operativo; H6 muestra que la abstención sí reduce
false-reuse.

Trabajo:

- enriquecer descripciones de skills con ejemplos/condiciones negativas;
- calibrar umbrales;
- mantener `ABSTAIN/CLARIFY` como salidas de primera clase;
- evaluar generalización fuera del generador confirmatorio sin mezclarla
  con H1–H8.

## Prioridad 3 — cobertura Odoo

- ampliar de 2/12 skills a una cobertura funcional útil;
- mantener allowlists de modelos/campos;
- modelar errores y transiciones específicas de Odoo;
- conservar Development/datos demo hasta completar controles de
  producción.

## Prioridad 4 — plataforma

- autenticación e identidad;
- aislamiento multi-tenant;
- gestión de secretos;
- persistencia e integridad de auditoría;
- observabilidad, métricas, SLO;
- recuperación/rollback;
- UX de aprobación y aclaración.

## Prioridad 5 — validación externa y negocio

Antes de formular claims de adopción/ROI:

- validar con usuarios/organizaciones bajo base legal adecuada;
- medir tiempo humano de aprobación/aclaración;
- medir coste operativo y errores evitados;
- repetir con distintos modelos/proveedores;
- separar siempre evidencia confirmatoria, exploratoria, stress externo y
  factibilidad.

## Regla

No transformar trabajo futuro en un claim actual. La hoja de ruta existe
precisamente para separar lo demostrado de lo que todavía falta.

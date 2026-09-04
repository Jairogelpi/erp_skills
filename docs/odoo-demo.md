# Demo de factibilidad: skills contra Odoo 19 Development

La integración con Odoo 19 es una **demostración post-core de
factibilidad end-to-end**. No es un backend adicional de la campaña
confirmatoria A/B/C y no se utiliza para inferir superioridad estadística.

## Entorno permitido

La demo debe ejecutarse exclusivamente contra una rama **Development con
datos demo**.

El guardián de instancia rechaza:

- producción;
- staging;
- destinos no declarados/ambiguos.

No versionar ni mostrar credenciales, tokens, datos identificables o
información operativa de empresa.

Configuración conceptual:

```sh
cp .env.example .env
# configurar ODOO_URL / ODOO_DB / credenciales para Development
uv run python scripts/odoo_governed_demo.py
```

## Secuencia gobernada

```text
R1 request
 -> ALLOW
 -> escritura
 -> relectura independiente
 -> postcondición verificada

R2 request sin aprobación
 -> REQUIRE_APPROVAL
 -> relectura independiente
 -> estado sin cambio

aprobación concedida
 -> ALLOW
 -> escritura
 -> nueva relectura
 -> cambio verificado
```

La relectura independiente evita considerar una respuesta HTTP/API
satisfactoria como prueba suficiente del estado final.

## Qué demuestra

- que el adaptador puede alcanzar una instancia Odoo 19 externa;
- que una operación R1 permitida puede persistirse;
- que una operación R2 puede detenerse hasta disponer de aprobación;
- que el estado puede verificarse de manera independiente tras cada paso;
- que el mismo runtime/policy model puede conectar con un ERP concreto sin
  trasladar toda la autoridad al LLM.

## Qué no demuestra

- superioridad A/B/C en Odoo;
- seguridad general;
- readiness de producción;
- comportamiento sobre datos de clientes;
- cobertura completa del ERP;
- ROI económico.

## Cobertura

La demostración actual mapea **2 de las 12 skills** del catálogo a
operaciones de Odoo. Esta cifra se presenta como límite explícito de
factibilidad, no como completitud de producto.

## Relación con la campaña confirmatoria

La comparación confirmatoria se ejecuta sobre el adaptador experimental
controlado para garantizar igualdad de estado inicial y reproducibilidad.
La demo Odoo se ejecuta aparte y responde otra pregunta:

> ¿Puede la frontera de autoridad implementada operar end-to-end contra
> un ERP externo y verificar el efecto persistido?

La respuesta demostrada es sí para la ruta y skills mapeadas, bajo
**Development con datos demo**.

## Artefactos

- `scripts/odoo_governed_demo.py`
- `data/odoo_governed_demo_results.json`
- adaptador/handlers Odoo en `src/erp_agent_os/`

Para el vídeo, usar la formulación:

> «Demostración de factibilidad sobre Odoo 19 Development con datos demo;
> no forma parte de la inferencia confirmatoria y no es validación en
> producción.»

# ERP Agent OS — quick start para evaluación

Este documento es la ruta recomendada para un tutor, profesor o evaluador que
quiera instalar el repositorio desde cero, verificar que el artefacto está
íntegro y abrir la demo comparativa A/B/C.

La demo comparativa **no necesita ninguna API key, cuenta de Odoo ni acceso a
datos privados**. Usa el backend reproducible `FakeERP` y lee la evidencia
confirmatoria v2.1.2 ya congelada en el repositorio.

## 1. Requisitos

Instalar únicamente:

- Git.
- [`uv`](https://docs.astral.sh/uv/).
- Node.js **18 o superior** con npm; se recomienda Node.js 20 LTS.

No es necesario instalar Python manualmente: `uv` puede instalar la versión
3.12 usada por el proyecto.

## 2. Clonar la versión académica

La referencia final de entrega es `v1.3-tfm-final`.

```bash
git clone --branch v1.3-tfm-final --depth 1 https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
```

## 3. Preparar el entorno

```bash
uv python install 3.12
uv sync --frozen --group dev
```

`uv.lock` fija las dependencias Python utilizadas por la entrega. El frontend
tiene además su propio `demo-ui/package-lock.json`; el comprobador del siguiente
paso ejecuta `npm ci`, no una resolución abierta de versiones.

## 4. Comprobación recomendada

En Windows, macOS y Linux puede utilizarse el mismo comando:

```bash
uv run python scripts/professor_demo.py --check
```

La comprobación debe terminar con:

```text
REVIEWER CHECK PASSED
```

Antes de mostrar ese resultado, el script verifica:

- Python 3.12;
- Node.js/npm;
- lectura del informe confirmatorio congelado;
- protocolo y estado de campaña;
- arranque de A, B y C;
- puerta `REQUIRE_APPROVAL` sin mutación previa;
- control positivo: la misma petición sí escribe después de aprobarse;
- auditoría disponible;
- instalación reproducible del frontend con `npm ci`;
- typecheck de TypeScript;
- build de producción de Vite;
- arranque real de la API y de la UI por HTTP;
- funcionamiento del proxy UI → API.

## 5. Abrir la demo

```bash
uv run python scripts/professor_demo.py
```

El script vuelve a ejecutar el preflight y el build, inicia la API y la UI, y
abre automáticamente:

```text
http://127.0.0.1:5173
```

La API se sirve únicamente en `127.0.0.1:8000`. Para detener ambos procesos,
pulsar `Ctrl+C` en la terminal.

La pantalla dispone de **tres presets de escenario** y una prueba adicional de
paráfrasis asociada al escenario de aprobación:

- `01 NORMAL`: operación permitida y postcondición verificada.
- `02 APPROVAL`: A/B escriben; C mantiene el ERP sin cambios hasta recibir una
  aprobación explícita. Desde este caso se puede ejecutar `PARAPHRASES` para
  comparar distintas formulaciones del mismo intent.
- `04 SECURITY`: ejemplo bloqueado acompañado del resultado confirmatorio H4,
  que permanece explícitamente **no soportado**.

La pestaña `Experimental evidence` lee las cifras desde los artefactos
confirmatorios versionados; la UI no recalcula ni inventa resultados.

## 6. Verificación científica completa, opcional

Si se desea ejecutar además la suite de tests completa y verificar el cierre
del protocolo v2.1.2:

```bash
uv run python scripts/professor_demo.py --full-check
```

Esto añade `pytest` y el verificador de cierre confirmatorio. No llama a ningún
proveedor LLM ni consume una nueva muestra.

## 7. Odoo es opcional y está separado

La prueba anterior es suficiente para evaluar el artefacto reproducible. La
demostración con Odoo 19 es una prueba de factibilidad independiente y requiere
credenciales propias de una rama **Development** con datos demo.

Nunca debe utilizarse una instancia de producción o staging para probar el
repositorio. El código contiene un guard que las rechaza antes de escribir.

Variables opcionales, documentadas también en `.env.example`:

```text
ODOO_URL=
ODOO_DB=
ODOO_API_KEY=
```

Para la demo comparativa A/B/C del apartado 5 deben permanecer innecesarias.

## 8. Problemas habituales

Si `uv` no está disponible, instalarlo siguiendo su documentación oficial y
repetir desde el apartado 3. Si el comprobador informa de Node.js ausente o
antiguo, instalar Node.js 20 LTS. Si los puertos 8000 o 5173 están ocupados,
cerrar la aplicación que los esté usando antes de lanzar la demo.

No debe ejecutarse `pip install` sobre el entorno global ni modificar
`uv.lock`/`package-lock.json` para evaluar la entrega: el objetivo es probar el
estado reproducible que se entregó.

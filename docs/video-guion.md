# Guion literal — competición de becas

**Dirección aprobada:** método primero. **Duración objetivo:** 4:45 (con el
tramo de generación de skills, §12 CU-02, que faltaba en versiones previas de
este guion). **Rechazo interno:** > 4:50. **Límite absoluto:** 5:00. Ensayar
a 125–135 palabras por minuto y cortar, no acelerar, si una toma supera 4:40.

Cada rótulo numérico incluye su estado de evidencia dentro del plano. Mientras
v2 siga pendiente, no se reemplaza por una cifra v1.

## 0:00–0:25 — El riesgo

**Imagen:** Odoo, oportunidad comercial y cambio de importe. Rótulo:
`UN ERROR DEL AGENTE CAMBIA ESTADO EMPRESARIAL`.

**Locución:**

> En un chatbot, un error produce una respuesta incorrecta. En un ERP puede
> duplicar una oportunidad, cambiar un importe o confirmar un documento. Mi
> proyecto parte de una idea simple: que el modelo entienda la petición no
> significa que deba tener autoridad para ejecutarla.

## 0:25–0:50 — Pregunta de investigación

**Imagen:** A · agente directo; B · herramientas tipadas; C · ERP Agent OS.

**Locución:**

> La pregunta es si separar la interpretación probabilística de la ejecución
> determinista mejora fiabilidad, eficiencia y trazabilidad. Para responderla
> comparo un agente directo, un agente con herramientas tipadas y una
> arquitectura gobernada mediante skills verificables.

## 0:50–1:25 — Método antes que números

**Imagen:** `reports/video/01-method.svg`.

**Locución:**

> El test prospectivo, ERP-Skills-Bench v2, tendrá ciento veinte peticiones
> nuevas: cinco por cada una de veinticuatro intenciones. Cada caso se ejecuta
> en los tres sistemas y en tres repeticiones independientes: mil ochenta
> observaciones. El modelo que redacta las peticiones es distinto del selector,
> y el resultado esperado se compila después mediante reglas deterministas.

## 1:25–1:55 — Congelación y una sola mirada

**Imagen:** dataset → hashes → tag de freeze → checkpoint cifrado → agregado.

**Locución:**

> Antes de observar una sola salida, se congelan dataset, catálogo, política,
> prompts, configuración, semilla y plan estadístico. El runner aleatoriza el
> orden, restaura el mismo estado y prohíbe reutilizar respuestas entre
> repeticiones. Los parciales quedan cifrados. Solo se publica un agregado si
> las mil ochenta unidades y todos sus hashes validan.

## 1:55–2:30 — Arquitectura y verificación

**Imagen:** `reports/video/02-architecture.svg`.

**Locución:**

> El LLM propone intención y argumentos. A partir de ahí, el catálogo recupera
> una skill versionada; la política comprueba rol, riesgo y aprobación; el
> runtime ejecuta solo un handler registrado; y el verificador vuelve a leer el
> estado final. Cada postcondición tiene nombre y evidencia. Si falla el
> verificador, el sistema falla cerrado. Si se repite la petición, la
> idempotencia evita una segunda mutación.

## 2:30–2:45 — Cuando no hay skill: proponer, nunca autodesplegar

**Imagen:** terminal, `uv run python scripts/demo_completa.py --solo 10`
(escena aislada de CU-02, sin correr las otras diez). Antes de grabar,
ejecutar `chcp 65001` en PowerShell para que los acentos no salgan como
`�` en pantalla.

**Locución:**

> ¿Y si no hay skill adecuada? El modelo puede proponer una nueva —
> validada, probada en sandbox, pero nunca activada sola. Solo un humano con
> nombre la aprueba; nunca entra en el experimento congelado.

## 2:45–3:20 — Demo Odoo como prueba visual

**Imagen:** grabación continua; rótulo fijo:
`DEMOSTRACIÓN ODOO · NO RESULTADO EXPERIMENTAL`.

**Locución:**

> La misma tubería funciona contra un Odoo de desarrollo. Una operación R1 se
> ejecuta. Una R2 sin aprobación queda bloqueada, y una relectura independiente
> demuestra que el ERP no cambió. Después de aprobarla, se ejecuta y se vuelve
> a verificar. La demo prueba integración técnica; no sustituye el experimento
> con FakeERP.

## 3:20–3:55 — Estado honesto de los resultados

**Imagen:** `reports/video/04-results.svg`.

**Locución:**

> El resultado confirmatorio v2 está pendiente, así que no voy a inventarlo ni
> a promover una corrida antigua. La evidencia v1 es exploratoria. Como señal,
> estimó una mejora de quince puntos de STSR frente al baseline tipado, menos
> false allow y menos tokens. Son cifras útiles para justificar v2, no para dar
> la hipótesis por demostrada.

## 3:55–4:20 — El peor número y el límite adversarial

**Imagen:** `3,3 % DETECCIÓN EXTERNA`; después:
`STRESS EXPLORATORIO · CONFINAMIENTO POR TRES CANALES · 0/1.530`;
sello `NO ADAPTATIVO`.

**Locución:**

> Mi peor resultado es importante: el detector léxico solo reconoció el tres
> coma tres por ciento de un dataset externo. En un stress test exploratorio,
> esos payloads no produjeron mutaciones no autorizadas por tres canales. Pero
> ese cero está acotado: no cubre adversarios adaptativos, y un test posterior
> consciente del catálogo encontró un caso de inyección en campo.

## 4:20–4:37 — Innovación y límites

**Imagen:** `reports/video/05-limitations.svg`, luego contrato de skill.

**Locución:**

> La contribución no es conectar un LLM con Odoo. Es un método reproducible
> para convertir una propuesta incierta en una acción contractual y auditable.
> Los límites son visibles: datos sintéticos, doce skills, sin usuarios reales
> y sin segundo anotador humano.

## 4:37–4:45 — Cierre

**Imagen:** marca ERP Agent OS, fondo limpio.

**Locución:**

> ERP Agent OS. El modelo propone. El contrato decide.

## Reglas de montaje

- Ninguna toma recreada se presenta como ejecución real.
- La secuencia Odoo se graba continua; se permiten cortes solo antes o después.
- Los rótulos `V2 PENDIENTE`, `EXPLORATORIO` y `DEMOSTRACIÓN` ocupan al menos
  el 4 % de la altura del plano.
- No usar música con derechos no acreditados ni mostrar claves, URLs privadas,
  nombres de clientes o terminales con secretos.
- Exportar a 1080p, comprobar audio con auriculares y móvil, y mantener la
  versión final por debajo de 4:50 para absorber silencios de plataforma.

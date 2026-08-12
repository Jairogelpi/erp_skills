# Presentación de defensa — método primero

Versión de 12 diapositivas para 10–12 minutos. Las cifras v1 llevan siempre la
etiqueta **EXPLORATORIO**; el resultado principal lleva **V2 PENDIENTE** hasta
que existan freeze y 1.080 observaciones válidas.

## 1 — Portada

**Se ve:** ERP Agent OS · Automatización ERP gobernada mediante skills
verificables · Jairo Gelpi Moreno.

**Se dice:** «Un modelo propone una acción. Mi trabajo estudia cómo impedir
que esa propuesta se convierta en una mutación inválida.»

## 2 — El riesgo concreto

**Se ve:** una petición legítima que intenta cambiar un importe y tres fallos:
herramienta incorrecta, alcance excesivo y repetición duplicada.

**Se dice:** «En un chatbot, un error produce texto. En un ERP puede producir
estado empresarial. Por eso separar interpretación y ejecución es el problema
de investigación.»

## 3 — Pregunta y comparación

**Se ve:** A agente directo · B herramientas tipadas · C ERP Agent OS.

**Se dice:** «Comparo los mismos casos y controles. C añade recuperación,
política, aprobación, idempotencia, postcondiciones y auditoría.»

## 4 — Diseño prospectivo v2

**Se ve:** `reports/video/01-method.svg`.

**Se dice:** «Ciento veinte textos nuevos; tres sistemas; tres repeticiones
independientes; 1.080 observaciones. El texto lo redacta un modelo distinto del
selector y el oracle se compila después. C−B en STSR es el contraste primario.»

## 5 — Congelación y una sola mirada

**Se ve:** dataset → hash → tag `v2-protocol-freeze` → checkpoint cifrado →
validador → agregado.

**Se dice:** «No se puede observar una salida y después cambiar el instrumento.
El runner no publica parciales y el registro no promociona un resultado sin
prueba cruzada de hashes y cardinalidad.»

## 6 — Arquitectura

**Se ve:** `reports/video/02-architecture.svg`.

**Se dice:** «El LLM queda en la zona probabilística. La zona determinista
valida, decide, ejecuta handlers registrados y comprueba el estado final.»

## 7 — Verificación ejecutada

**Se ve:** seis estados: verified, failed, not_executed,
missing_verification, verifier_error, replayed.

**Se dice:** «Una postcondición ya no es texto en YAML: se ejecuta. Todas las
comprobaciones dejan evidencia; un error del verificador falla cerrado; un
reintento no duplica la mutación.»

## 8 — Prueba Odoo

**Se ve:** `reports/video/03-odoo-proof.svg` y, en directo, una única secuencia:
R1 ejecuta → R2 sin aprobación no cambia el ERP → R2 aprobada ejecuta →
relectura independiente.

**Etiqueta visible:** `DEMOSTRACIÓN · NO RESULTADO A/B/C`.

## 9 — Estado de resultados

**Se ve:** `reports/video/04-results.svg`.

**Se dice:** «El resultado confirmatorio v2 está pendiente. Como señal
exploratoria, v1 estimó STSR 0,483 en B y 0,633 en C; false allow 0,889 frente
a 0,111; y 265,3 frente a 67,6 tokens. No uso esos números como conclusión
final.»

## 10 — Resultado negativo y alcance adversarial

**Se ve:** detector externo = 3,3 %; debajo, `EXPLORATORIO · CONFINAMIENTO POR
TRES CANALES: 0/1.530`; a la derecha, `NO ADAPTATIVO`.

**Se dice:** «El detector léxico apenas transfiere: 3,3 %. El stress test
acotado no observó mutaciones no autorizadas en tres canales, pero eso no
prueba robustez general. El test consciente del catálogo encontró además un
caso de inyección en campo.»

## 11 — Limitaciones y validez

**Se ve:** `reports/video/05-limitations.svg`.

**Se dice:** «Datos sintéticos, español, doce skills, sin usuarios reales, sin
segundo anotador humano y Odoo limitado a demo. El audit de IA es consistencia,
no acuerdo humano. El coste es escenario, no ahorro medido.»

## 12 — Contribución y cierre

**Se ve:** contratos versionados · benchmark y protocolo · runtime verificable
· evidencia auditable · límites explícitos.

**Se dice:** «La innovación no es conectar un LLM con Odoo. Es convertir una
propuesta probabilística en una acción contractual, falsable y auditable. El
modelo propone. El contrato decide.»

## Diapositivas de reserva

1. Definición exacta de STSR y unidad emparejada.
2. Siete componentes de trazabilidad y pesos.
3. Taxonomía R0–R4 y matriz rol/acción.
4. Historial de defectos metodológicos v1 y por qué fuerza v2.
5. Endpoint `not_estimable` y denominadores.
6. Evidencia de Odoo y separación demo/experimento.
7. Evidencia adversarial: detector, confinamiento, stress de catálogo.
8. Trabajo futuro: anotación humana, usuarios reales y transferencia.

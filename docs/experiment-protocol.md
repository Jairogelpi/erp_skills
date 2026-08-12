# Protocolo experimental prospectivo — ERP-Skills-Bench v2

Este documento define el único protocolo que puede producir evidencia
confirmatoria A/B/C. Todas las ejecuciones v1 conservadas en `data/` son
exploratorias o de sensibilidad según `data/evidence_registry.json`.

**Estado al 12 de agosto de 2026: pendiente.** El generador, la puerta de
congelación, el runner cifrado y el análisis existen; el dataset v2, su
manifiesto firmado por hashes y las 1.080 observaciones todavía no se han
producido. Por tanto, este documento no contiene resultados v2.

## 1. Pregunta y endpoint primario

La pregunta es si ERP Agent OS (C) mejora el éxito estricto frente a
herramientas tipadas sin gobierno completo (B). El endpoint primario es STSR:

`acción correcta ∧ argumentos válidos ∧ permisos respetados ∧ estado esperado ∧ sin efectos laterales`.

El contraste primario predeclarado es C−B. Se informa diferencia emparejada,
IC bootstrap del 95 % y McNemar. La hipótesis se considera apoyada únicamente
si el límite inferior del IC es mayor que cero. Un resultado nulo o adverso
sigue siendo el resultado válido.

## 2. Muestra, unidad y contaminación

- 120 peticiones nuevas: cinco por cada una de las 24 intenciones congeladas.
- Por intención: tres paráfrasis ordinarias, una ruidosa y un caso de borde
  gobernado.
- Autoría del texto con proveedor/modelo distinto del selector A/B/C.
- Oracle de skill, argumentos, decisión y transición compilado después de la
  autoría mediante catálogo y política deterministas.
- Ningún texto v2 puede reutilizar exactamente una petición v1.
- Los resultados v2 no pueden utilizarse para cambiar prompts, catálogo,
  umbrales, reglas, etiquetas o código.

La unidad es `request_id × estado inicial restaurado × repetición`. Cada caso
se ejecuta tres veces en A, B y C: 120 × 3 × 3 = **1.080 observaciones**. Los
contrastes se colapsan a 120 unidades emparejadas por sistema antes de la
inferencia.

## 3. Controles idénticos

Un `RunConfig` inmutable fija proveedor, modelo, versión, temperatura, límite
de tokens, timeout, reintentos, pasos, rol, hash del prompt de extracción,
hash de la factoría de estado inicial y semilla. El mismo hash se registra en
cada observación. Cada repetición usa llamadas independientes: ningún cache de
respuestas puede compartirse entre sistemas o repeticiones.

Cada observación aporta hashes del estado inicial y final. Las nueve
observaciones de un caso deben partir del mismo hash inicial. Una discrepancia
detiene la validación.

## 4. Sistemas

- **A:** agente directo con herramientas ERP genéricas.
- **B:** herramientas tipadas, sin memoria de skills ni verificador completo.
- **C:** recuperación, abstención, políticas, aprobación, runtime determinista,
  idempotencia, postcondiciones ejecutadas y auditoría.

`FakeERPAdapter` es obligatorio. La demostración Odoo no forma parte del
contraste ni hereda sus conclusiones.

## 5. Endpoints secundarios

Para cada sistema se publican denominador y estado `estimated` o
`not_estimable`:

- false allow en el subconjunto peligroso y false block en el subconjunto
  seguro que debía permitirse, con IC del 95 %;
- tokens de entrada, salida y total, además de diferencias emparejadas C−A y
  C−B;
- trazabilidad total y sus siete componentes ponderados;
- Top-1, Top-3, coverage, selective accuracy y false-reuse risk en el
  subconjunto elegible;
- coincidencia del estado final entre las tres repeticiones;
- latencia, llamadas al modelo y reintentos por observación.

Un denominador cero se publica como `not_estimable` con motivo; nunca se
convierte en cero ni desaparece del esquema.

## 6. Puerta de congelación y regla de una sola mirada

Antes de cualquier salida A/B/C, `scripts/freeze_protocol_v2.py --verify`
debe verificar un árbol limpio y el tag exacto `v2-protocol-freeze`. El
manifiesto incluye hashes del dataset y procedencia, configuración, catálogo,
política, sistemas, evaluador, runner y este plan.

El runner aleatoriza el orden con la semilla congelada y escribe únicamente un
checkpoint Fernet cifrado, con clave externa al repositorio. No imprime
observaciones ni agregados parciales. Si falla la infraestructura, registra de
forma cifrada la unidad, el número completado y el tipo de error sanitizado;
solo puede reanudarse con la misma configuración.

`scripts/analyze_experiment_v2.py` publica el agregado únicamente después de
validar 1.080 unidades únicas, hashes, restauración, llamadas independientes,
esquema y endpoint primario. Solo entonces el registro de evidencia puede
clasificar el artefacto como confirmatorio.

## 7. Limitaciones predeclaradas

- Datos sintéticos, español y un dominio ERP acotado; no se extrapola a
  producción ni a usuarios reales.
- No hay segundo anotador humano disponible. El chequeo opcional con IA es una
  revisión de consistencia, no acuerdo humano.
- La detección léxica externa observada fue 3,3 %, un resultado negativo.
- Los stress tests de confinamiento son exploratorios y no cubren adversarios
  adaptativos.
- Odoo prueba integración técnica en una demo; no aporta estimaciones A/B/C.

## 8. Comandos

```powershell
uv run python scripts/generate_bench_v2.py ...
uv run python scripts/freeze_protocol_v2.py --write
# commit + tag v2-protocol-freeze, sin observar salidas A/B/C
uv run python scripts/freeze_protocol_v2.py --verify
uv run python scripts/run_experiment_v2.py --executor paquete:funcion_congelada
uv run python scripts/analyze_experiment_v2.py
uv run python scripts/audit_evidence_status.py --require-confirmatory
```

La ejecución real se mantiene pendiente mientras falte cualquiera de esas
precondiciones.

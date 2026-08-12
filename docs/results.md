# Resultados y estado de la evidencia

## Lectura obligatoria

**No existe todavía un resultado confirmatorio A/B/C.** El único protocolo
elegible es ERP-Skills-Bench v2 y permanece pendiente: no se han generado el
dataset final, el manifiesto del tag `v2-protocol-freeze` ni las 1.080
observaciones independientes.

Los números históricos se conservan porque sirven para depurar el instrumento
y estimar si el proyecto es viable. `data/evidence_registry.json` los clasifica
como exploratorios, de sensibilidad o demostración. Ningún flag antiguo dentro
de un JSON cambia esa clasificación.

| Línea de evidencia | Estado | Uso permitido |
|---|---|---|
| ERP-Skills-Bench v2 A/B/C | **Pendiente** | Única inferencia confirmatoria futura |
| Cinco ejecuciones v1 A/B/C | **Exploratoria / sensibilidad** | Magnitud provisional y depuración |
| InjecAgent: detector léxico | **Exploratoria externa** | Resultado negativo de transferencia |
| Stress de confinamiento | **Exploratoria y acotada** | Tres canales sintéticos, no robustez general |
| Stress consciente del catálogo | **Exploratoria** | Busca bypasses plausibles del contrato |
| Odoo 19 | **Demostración** | Prueba de integración, no comparación causal |

## 1. Resultado principal: pendiente v2

El protocolo prospectivo predeclara:

- 120 textos nuevos, cinco por intención;
- autor de textos distinto del selector A/B/C;
- tres sistemas y tres repeticiones independientes;
- estado restaurado y probado por hash en cada unidad;
- C−B en STSR como contraste primario;
- IC bootstrap del 95 % y McNemar;
- publicación solo después de validar las 1.080 observaciones.

Hasta completar esa puerta, las tarjetas y diapositivas deben mostrar
`V2 PENDIENTE`, sin rellenar el hueco con una cifra v1.

## 2. Estimación exploratoria v1 más informativa

La ejecución con Groq, parseo real y normalización estrecha de unidades es la
estimación histórica más cercana al sistema actual. Son 120 casos sintéticos,
tres sistemas y tres repeticiones, pero sus cambios y congelación no satisfacen
la regla prospectiva v2.

| Métrica exploratoria | A directo | B tipado | **C gobernado** |
|---|---:|---:|---:|
| STSR | 0,000 | 0,483 | **0,633** |
| False allow | 0,889 | 0,889 | **0,111** |
| Tokens por ejecución | 185,1 | 265,3 | **67,6** |
| Trazabilidad, 0–1 | 0,356 | 0,374 | **0,820** |

En este análisis exploratorio, C−B en STSR fue +0,150, IC95
[+0,042, +0,258], *p* de Holm = 0,0162. Es una señal prometedora, no la
confirmación final. La unidad inferencial fue el caso (n = 120), después de
colapsar sus repeticiones; tratar las 360 filas por sistema como independientes
sería pseudorreplicación.

### Qué cambió durante la depuración

1. Dar los argumentos correctos a los tres sistemas regalaba el parseo y
   beneficiaba especialmente a C.
2. En la ejecución 3 histórica, activar parseo real redujo inicialmente C−B a
   +0,075, *p* = 0,212.
3. Se detectó que una unidad monetaria textual penalizaba solo al sistema que
   valida tipos; una normalización estrecha produjo la estimación anterior.
4. El hallazgo demuestra por qué v2 debe congelarse antes de observar salidas.

### Sensibilidades conservadas

| Selector / régimen | STSR A | STSR B | STSR C | Lectura |
|---|---:|---:|---:|---|
| OpenRouter, argumentos dados | 0,000 | 0,517 | 0,700 | Exploratoria; parseo regalado |
| Groq, argumentos dados | 0,000 | 0,492 | 0,700 | Sensibilidad de proveedor |
| Groq, parseo real normalizado | 0,000 | 0,483 | 0,633 | Exploratoria más informativa |

La estabilidad salió 1,0 con temperatura cero. Eso no discrimina arquitecturas:
es una consecuencia esperable de una configuración determinista.

## 3. Seguridad: resultado negativo primero

El detector léxico aplicado a 510 peticiones externas de InjecAgent alcanzó
**3,3 %** después de añadir patrones en inglés. La primera versión obtuvo 0 %.
Este resultado muestra que reconocer frases conocidas no equivale a contener
una acción ERP; además, el dataset externo no es una prueba completa de un
adversario adaptativo.

### Confinamiento por tres canales

Los mismos 510 payloads se inyectaron de forma exploratoria en tres posiciones:

| Canal exploratorio | Mutaciones no autorizadas |
|---|---:|
| Texto de la petición | 0 / 510 |
| Campo almacenado leído por la petición | 0 / 510 |
| Parser comprometido con argumentos dictados | 0 / 510 |
| **Total acotado** | **0 / 1.530** |

Es un **resultado exploratorio de confinamiento por tres canales**. Prueba que
esos payloads no escaparon de esos límites en esa implementación; no prueba
resistencia universal, certificación ni cobertura de ataques adaptativos.

### Stress consciente del catálogo

`data/catalog_aware_stress_results.json` contiene 18 observaciones sintéticas
registradas: 16 cumplieron el desenlace, una reveló un hallazgo de inyección en
campo y una quedó fuera de la política implementada. Es evidencia exploratoria,
no una ejecución online ni una estimación poblacional.

## 4. Postcondiciones y auditoría

System C ya no atribuye éxito por el mero retorno del handler. Cada acción
declara comprobaciones con nombre, captura el estado estructural permitido,
ejecuta todas las comprobaciones y registra evidencia inmutable. Los estados
posibles son `verified`, `failed`, `not_executed`, `missing_verification`,
`verifier_error` y `replayed`.

Clarificación, abstención, denegación y fallos del verificador conservan
`postconditions_met = null`; nunca se convierten en éxito. Los errores de
snapshot, mapeo o comprobación fallan cerrados y se auditan sin filtrar secretos.

## 5. Recuperación

En los experimentos heredados, C alcanzó Top-1 = 0,780 y una tasa de abstención
de 0,093 en su población elegible. Esos valores son exploratorios y dependen del
benchmark plantillado. V2 volverá a medir Top-1, Top-3, coverage, selective
accuracy y false-reuse risk en denominadores predeclarados.

## 6. Anotación

No hay un segundo anotador humano disponible. Por eso no se informa ninguna
medida de acuerdo humano. El repositorio incluye una muestra estratificada y un
audit opcional de consistencia con IA, registrado como revisión de IA; no se
presenta como sustituto de evaluación humana.

## 7. Odoo 19

La secuencia Odoo demuestra que el adaptador limitado ejecuta una skill R1,
bloquea una R2 antes de aprobación, vuelve a leer el ERP y la ejecuta tras la
aprobación. Es una prueba de integración contra datos de demo. No es una
observación del benchmark A/B/C ni permite extrapolar rendimiento a producción.

## 8. Amenazas a la validez

- benchmark sintético, español, 24 intenciones y 12 skills;
- un solo autor principal de etiquetas y sin revisión humana independiente;
- modelos gratuitos y límites de cuota en los experimentos históricos;
- cambios instrumentales entre ejecuciones v1;
- detectores léxicos con baja transferencia externa;
- stress tests no adaptativos;
- Odoo limitado a dos skills de demostración;
- coste empresarial modelado por escenarios, no ahorro observado.

## 9. Reproducción y auditoría

```powershell
# Clasificación autoritativa de cada artefacto
uv run python scripts/audit_evidence_status.py

# Estimaciones históricas: siempre exploratorias
uv run python scripts/run_experiment.py --real-llm --real-parser --provider groq

# Protocolo v2: se detiene si falta dataset, freeze, tag o configuración
uv run python scripts/freeze_protocol_v2.py --verify
uv run python scripts/run_experiment_v2.py --executor paquete:funcion_congelada
uv run python scripts/analyze_experiment_v2.py

# Ningún informe puede promover evidencia sin la prueba completa
uv run python scripts/audit_evidence_status.py --require-confirmatory
```

La ausencia de un resultado v2 no se oculta: es el estado científico correcto
hasta que la ejecución prospectiva completa exista.

# Resultados confirmatorios — ERP Agent OS v2.1.2

Este documento es la fuente textual canónica de resultados para la
entrega del TFM. Resume la campaña cerrada bajo
`tfm-protocol-v2.1.2` sin reinterpretar resultados históricos.

El informe detallado anterior permanece íntegramente accesible en el
historial de Git y los artefactos crudos/versionados siguen siendo la
fuente reproducible de cada cifra.

## 1. Estado de la campaña

- **Protocolo:** `tfm-protocol-v2.1.2`.
- **Estado:** `RUN_COMPLETED / CLOSURE_VALID`.
- **Cierre de recolección:** 2026-08-22.
- **Re-congelado de la capa de análisis:** 2026-08-23.
- **Proveedor/modelo:** OpenRouter · `deepseek/deepseek-v4-flash`.
- **Campaña:** **21.478 observaciones experimentales procedentes de
  ejecuciones observadas sobre escenarios sintéticos/procedurales**.
- **Unidad inferencial:** escenario latente; no cada repetición o
  superficie lingüística.

ERP-Skills-Bench-Proc v2.1 es un **instrumento experimental
sintético/procedural**. Permite definir intención, rol, estado inicial,
riesgo, política y resultado esperado antes de generar el texto y comparar
A/B/C bajo condiciones controladas. No se presenta como una muestra
representativa de usuarios, empresas o prevalencias organizativas.

## 2. Sistemas comparados

| Sistema | Descripción |
|---|---|
| **A — agente directo** | selección/ejecución con menor capa específica de gobierno |
| **B — tools tipadas** | herramientas con esquemas explícitos y cobertura funcional comparable |
| **C — ERP Agent OS** | retrieval selectivo, contrato versionado, policy/riesgo, aprobación, runtime determinista y postcondiciones |

A, B y C comparten proveedor/modelo, tarea, rol, estado inicial y
evaluador según el protocolo; difieren en la estructura y gobernanza que
se pretende estudiar.

## 3. Matriz de resultados

| Hipótesis | Endpoint | Resultado principal | Veredicto |
|---|---|---|---|
| **H1a** | STSR C vs A | C−A = **+25,3 pp**; límite inferior IC95 +23,2 pp; margen NI -5 pp | **Soportada** |
| **H1b** | STSR C vs B | C−B = **-1,5 pp**; p=0,286 | **No soportada** |
| **H2** | tokens | C usa ~**468 menos que A** y ~**648 menos que B** | **Soportada** |
| **H3a** | estabilidad entre formulaciones | OR = **9,35**; p=2,2×10^-18 | **Soportada** |
| **H3b** | repetición estocástica | consistencia 0,367 [0,246; 0,501] | **Descriptiva** |
| **H4** | seguridad activa | **19,0 %** de mutación no autorizada sobre **315 escenarios peligrosos del benchmark confirmatorio**; objetivo <5 % | **No soportada** |
| **H5** | retrieval selectivo | selective accuracy **0,589**; false-reuse **0,411** | **No soportada** |
| **H6** | efecto de abstención | false-reuse **-8,6 pp** frente a ablación sin abstención | **Soportada** |
| **H7** | reconstrucción de auditoría | **+42,7 pp** frente a A; p=2,85×10^-112 | **Soportada** |
| **H8** | sensibilidad económica | 243 escenarios de coste × 3 sistemas | **Descriptiva; no ahorro observado** |

## 4. Lectura por hipótesis

### H1 — éxito de tarea

**H1a está soportada:** C no es inferior a A bajo el margen
prerregistrado de -5 puntos porcentuales.

**H1b no está soportada:** no se demuestra que C supere a B en éxito
estricto de tarea. La estimación puntual es ligeramente negativa y
p=0,286. Por tanto, el valor medido de la gobernanza no puede venderse
como «más éxito que las tools tipadas».

### H2 — consumo de tokens

C consume aproximadamente 468 tokens menos que A y 648 menos que B por
unidad en el brazo específico de H2. Las comparaciones conjuntas cumplen
el criterio registrado tras aplicar el control previsto para ambas
comparaciones.

Esto es **consumo de tokens**, no ahorro monetario observado.

### H3 — estabilidad

H3a muestra mayor consistencia de C cuando el mismo escenario se expresa
mediante tres superficies lingüísticas distintas (OR 9,35;
p=2,2×10^-18).

H3b se mantiene descriptiva y no se utiliza para formular un claim
direccional adicional.

### H4 — seguridad activa

Este es el principal resultado negativo.

Sobre **315 escenarios peligrosos del benchmark confirmatorio**, C
produce una mutación no autorizada en **19,0 %** de los casos. El límite
superior del 95 % es 23,1 %, frente a un objetivo prerregistrado inferior
al 5 %. El fallo se distribuye en cinco de las siete categorías de la
población peligrosa.

La comparación de decisiones `DENY` con A/B debe interpretarse con
cautela: parte de sus denegaciones procede de errores de ejecución y no de
una detección de seguridad homologable. Por ello, la conclusión correcta
no es «A/B son más seguros», sino **H4 no alcanza el criterio
prerregistrado de seguridad activa**.

### H5 — retrieval

El punto operativo registrado no se alcanza: selective accuracy 0,589 y
false-reuse 0,411. El retrieval es un cuello de botella del prototipo y
limita cualquier extrapolación a operación real.

### H6 — abstención

La abstención reduce el false-reuse en 8,6 puntos porcentuales frente a
la ablación sin abstención. En procesos con efectos persistentes, no
forzar una selección es una capacidad funcional, no simplemente un fallo.

### H7 — auditoría

C mejora en 42,7 puntos porcentuales la reconstrucción completa de
hechos de auditoría frente a A (p=2,85×10^-112).

Existe una salvedad estructural: A/B no producen por diseño todos los
hechos de gobernanza que C registra. La ventaja se reporta precisamente
como **trazabilidad/explicabilidad operacional**, no como una propiedad
oculta del modelo.

### H8 — sensibilidad de costes

Se publica una rejilla de sensibilidad bajo supuestos declarados. No es
un experimento de ahorro económico observado y no justifica afirmar una
cantidad concreta de euros ahorrados.

## 5. Stress test externo: InjecAgent

La prueba externa responde una pregunta distinta de H4.

- 510 payloads externos.
- 3 superficies de ataque por payload.
- 1.530 intentos en total.
- **0/1.530 mutaciones no autorizadas fuera de contrato observadas**.
- Detección fuera de distribución: baja (3,3 %).

Interpretación: evidencia de **confinamiento estructural bajo el stress
test explícito evaluado**. No prueba seguridad general, riesgo cero ni
sustituye el resultado negativo de H4.

**Confinamiento no equivale a detección.**

## 6. Integración con Odoo 19

La integración se evalúa aparte como **demostración de factibilidad** en
una rama **Odoo 19 Development con datos demo**.

Secuencia demostrada:

```text
R1 -> ALLOW -> escritura -> relectura independiente -> verificación
R2 sin aprobación -> REQUIRE_APPROVAL -> relectura -> sin cambio
aprobación -> ALLOW -> escritura -> nueva relectura -> cambio verificado
```

No forma parte de la inferencia estadística A/B/C, no es validación en
producción y actualmente cubre **2 de 12 skills** del catálogo.

## 7. Incidencia v2.1.1 -> v2.1.2

Tras completar la campaña se detectó que el análisis de H2 implementaba
la comparación C-A pero omitía C-B, aunque el protocolo exigía ambas.

La corrección de la capa de análisis invalidó automáticamente el freeze,
como debía ocurrir. Se realizó un nuevo congelado formal
`tfm-protocol-v2.1.2`, se mantuvieron intactos los datos crudos y el resto
de componentes protegidos, y se conservó la procedencia del informe
anterior. La comparación añadida confirmó el mismo veredicto de H2.

Este incidente se conserva como evidencia de trazabilidad del instrumento,
no se oculta ni se reescribe la historia experimental.

## 8. Límites de inferencia

Las conclusiones se restringen a ERP-Skills-Bench-Proc v2.1 y a las
condiciones registradas. En particular:

- el benchmark es sintético/procedural;
- no se ha demostrado representatividad del lenguaje de usuarios;
- no se infieren prevalencias organizativas;
- no se infiere seguridad universal;
- el retrieval actual no está listo para producción;
- la demo Odoo usa Development y datos demo;
- no existe ROI monetario observado;
- la evolución gobernada de skills es una demo funcional, no una causa
  confirmada de H1–H8.

## 9. Artefactos reproducibles

- Crudo:
  `data/protocol_v2_1/runs_v2/confirmatory_observations_v21_2d36433e861121928cceac5899ff1cf4ed346fe63250ff87956f8aba4f082c5c.jsonl`
- Informe:
  `data/protocol_v2_1/confirmatory_report_v2_1_2.json`
- Manifiesto:
  `data/protocol_v2_1/code_freeze_manifest.json`
- Verificación:

```sh
make verify-tfm-closure
```

El verificador debe cerrar en `CLOSURE_VALID` sin sustituir los artefactos
confirmatorios por una nueva campaña.

## 10. Conclusión confirmatoria

> Bajo ERP-Skills-Bench-Proc v2.1 y las condiciones registradas, ERP Agent
> OS no es inferior al agente directo en éxito de tarea y aporta ventajas
> medibles de consumo de tokens, estabilidad entre formulaciones,
> abstención y trazabilidad. No demuestra superioridad frente a tools
> tipadas en éxito de tarea, el retrieval no alcanza el punto operativo y
> la seguridad activa falla de forma material en escenarios ambiguos.
> Gobernar un agente aporta propiedades medibles, pero no elimina por sí
> mismo el riesgo de operar sobre un ERP.

# Encuadre metodológico del benchmark para el TFM

Este documento fija el lenguaje que debe utilizarse en memoria, README,
vídeo y material de evaluación para describir ERP-Skills-Bench-Proc v2.1
sin atribuirle una representatividad que no tiene.

## 1. Modalidad del TFM

ERP Agent OS se encuadra como **proyecto técnico aplicado con desarrollo
de solución software y evaluación experimental**. El benchmark no
constituye el objeto del TFM como ejercicio de análisis de dataset: es el
**instrumento experimental** utilizado para comparar de forma controlada
tres arquitecturas de agente ERP.

Texto recomendado para la memoria:

> El presente TFM se encuadra en la modalidad de proyecto técnico
> aplicado. ERP-Skills-Bench-Proc v2.1 no constituye el objeto del
> trabajo como dataset de análisis, sino un instrumento experimental
> sintético diseñado para evaluar de forma controlada la arquitectura
> software propuesta. Su construcción procedural permite fijar antes de
> generar el lenguaje la intención, el rol, el estado inicial, el riesgo
> y el resultado esperado, manteniendo oráculos independientes del
> sistema evaluado.

## 2. Qué significa que el benchmark sea sintético

El carácter sintético se utiliza deliberadamente para maximizar
**validez interna, control experimental y reproducibilidad**. Permite
conocer por construcción la verdad de referencia y mantener idénticos
los estados iniciales de A, B y C.

No permite afirmar:

- representatividad del lenguaje de usuarios reales;
- comportamiento o prevalencias de organizaciones reales;
- ahorro económico observado;
- seguridad universal.

Sí permite estudiar, bajo las condiciones registradas:

- éxito estricto de tarea;
- diferencias entre arquitecturas;
- consumo de tokens;
- estabilidad ante variación lingüística controlada;
- recuperación selectiva y abstención;
- mutaciones no autorizadas dentro de la población experimental;
- reconstrucción de auditoría.

## 3. Terminología obligatoria

Usar:

- **21.478 observaciones experimentales**;
- **21.478 ejecuciones observadas sobre escenarios sintéticos**;
- **315 escenarios peligrosos del benchmark confirmatorio**;
- **benchmark sintético/procedural**;
- **integración de factibilidad con Odoo 19 Development y datos demo**.

Evitar cualquier formulación que pueda hacer creer que las 21.478 filas
proceden de usuarios/empresas o que los 315 escenarios de H4 fueron
peticiones recogidas en una organización. También evitar llamar a la demo
de Odoo «validación en producción».

Cuando sea necesario distinguir la ejecución del origen de los datos,
usar:

> La campaña contiene ejecuciones observadas del sistema sobre escenarios
> sintéticos con verdad de referencia conocida por construcción.

## 4. Triangulación de evidencia

La evaluación no descansa en una única fuente:

1. **Confirmatoria controlada:** ERP-Skills-Bench-Proc v2.1.2, para
   validez interna y comparación A/B/C.
2. **Stress test externo:** InjecAgent, para evaluar confinamiento ante
   payloads adversariales de un benchmark publicado.
3. **Factibilidad operacional:** Odoo 19 Development con datos demo,
   escritura persistente, bloqueo, aprobación y relectura independiente
   del estado final.
4. **Exploratoria/transferencia:** estudios adicionales del repositorio,
   que no se mezclan con los claims confirmatorios.

Estas fuentes responden preguntas diferentes y sus resultados no deben
colapsarse en un único indicador.

## 5. Interpretabilidad aplicable al proyecto

ERP Agent OS no entrena un modelo predictivo propio sobre el que tenga
sentido aplicar SHAP o LIME como requisito central. La interpretabilidad
relevante es **operacional y de decisión**: reconstruir qué petición se
recibió, qué skill y versión se seleccionó, qué argumentos se propusieron,
qué política se aplicó, qué riesgo se asignó, si existió aprobación, qué
handler se ejecutó y qué postcondición se verificó.

H7 mide precisamente esa propiedad mediante Audit Reconstruction Success
Rate. Debe describirse como **explicabilidad/trazabilidad operacional**,
sin afirmar interpretabilidad interna de los pesos del LLM.

## 6. Respuesta de defensa si cuestionan los datos sintéticos

> El benchmark sintético es una decisión metodológica, no un intento de
> sustituir datos empresariales. Necesitaba conocer antes de la ejecución
> cuál era la acción, autorización y estado final correctos para comparar
> A, B y C bajo exactamente las mismas condiciones. Esa decisión mejora
> la validez interna y la reproducibilidad, pero limita la validez
> externa, y lo declaro explícitamente. Por eso no extrapolo las
> frecuencias del benchmark a usuarios u organizaciones y separo la
> campaña confirmatoria de la prueba externa InjecAgent y de la
> demostración contra Odoo 19 Development con datos demo.

## 7. Regla de claims

Todo claim debe indicar la clase de evidencia que lo sostiene:
**confirmatoria**, **exploratoria**, **stress externo** o **factibilidad**.
Ningún resultado del benchmark sintético debe presentarse como frecuencia
observada en una empresa real.

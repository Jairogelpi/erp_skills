# Estrategia de defensa — ERP Agent OS

## Tesis en una frase

ERP Agent OS no da autoridad al modelo: convierte su propuesta en una acción
estructurada que políticas, aprobaciones, idempotencia y postcondiciones pueden
aceptar, rechazar y auditar.

## Orden recomendado

1. Riesgo empresarial concreto.
2. Pregunta de investigación y A/B/C.
3. Método prospectivo v2 y prevención de contaminación.
4. Arquitectura y postcondiciones realmente ejecutadas.
5. Demo Odoo como prueba de integración.
6. Resultado v2 pendiente; v1 solo como señal exploratoria.
7. Resultado negativo del detector y alcance adversarial.
8. Limitaciones y contribución.

El jurado debe entender primero por qué los números futuros serán creíbles. La
demo prueba que el artefacto existe; no reemplaza el experimento.

## Estado de evidencia que debe memorizarse

- **Confirmatorio:** ninguno todavía; v2 pendiente.
- **Exploratorio v1 de referencia:** STSR B 0,483 y C 0,633; C−B +0,150,
  IC95 [+0,042, +0,258]; false allow B 0,889 y C 0,111; tokens B 265,3
  y C 67,6; trazabilidad B 0,374 y C 0,820.
- **Resultado negativo externo:** detección léxica 3,3 %.
- **Confinamiento exploratorio:** 0/1.530 mutaciones no autorizadas en tres
  canales sintéticos; no adaptativo.
- **Stress de catálogo:** 18 observaciones registradas, 16 conformes, un
  hallazgo de inyección en campo y un caso fuera de política.
- **Odoo:** demostración técnica, no dato A/B/C.
- **Anotación:** sin segundo humano; el audit de IA no es acuerdo humano.

## Preguntas difíciles

### «¿Entonces el experimento no está terminado?»

Respuesta: «El prototipo, sus controles y la puerta experimental están
implementados. La inferencia prospectiva v2 permanece pendiente porque prefiero
no promover corridas que preceden a la congelación completa. Esa separación es
parte de la contribución metodológica.»

### «¿Por qué debería creer los resultados futuros?»

Respuesta: «Dataset nuevo, autor distinto del selector, oracle compilado
después, tag y hashes previos a cualquier salida, estado inicial probado,
llamadas independientes, parciales cifrados y publicación solo con 1.080
unidades válidas. El resultado nulo también se publica.»

### «¿No está diseñado C para ganar?»

Respuesta: «A, B y C comparten modelo, configuración, rol, estado, acciones
permitidas y evaluador. C conserva sus diferencias arquitectónicas declaradas.
El contraste primario es C−B, no el baseline A más débil.»

### «¿Por qué A dio cero en v1?»

Respuesta: «STSR exige estado final y ausencia de efectos laterales; las
herramientas CRUD genéricas lo tienen difícil. Por eso no uso A como contraste
principal y v2 predeclara C−B.»

### «¿Puede decir que es seguro?»

Respuesta: «No. El detector externo fue débil, 3,3 %. El 0/1.530 pertenece a
un stress test exploratorio de confinamiento por tres canales y no cubre adversarios adaptativos.
Puedo describir controles y evidencia acotada, no certificar seguridad.»

### «¿Por qué el test encontró un bypass?»

Respuesta: «Porque el test consciente del catálogo dejó de usar payloads
obviamente fuera de esquema y buscó argumentos válidos. El hallazgo de
inyección en campo delimita el contrato y se conserva; no se maquilla.»

### «¿La IA fue el segundo anotador?»

Respuesta: «No. Es una revisión de consistencia registrada como IA. No hay
segundo humano y no reporto una medida de acuerdo humano.»

### «¿Odoo valida el resultado?»

Respuesta: «Valida integración: misma tubería, aprobación y relectura. El
experimento usa FakeERP para restauración y comparabilidad; Odoo no aporta una
estimación causal.»

### «¿Dónde está la innovación?»

Respuesta: «En la combinación evaluable: contrato versionado, recuperación
selectiva, política de riesgo, ejecución determinista, idempotencia,
postcondiciones con evidencia y un protocolo que impide promoción retrospectiva
de resultados. No en una simple conexión LLM–Odoo.»

### «¿Qué haría con más tiempo?»

Respuesta: «Completar v2 sin tocar el protocolo; conseguir revisión humana
independiente; ampliar Odoo y usuarios reales solo como validación externa;
y evaluar ataques adaptativos que conocen el catálogo.»

## Errores que invalidan la defensa

- Llamar confirmatoria a una corrida v1.
- Mostrar un número antiguo en el hueco de v2.
- Presentar el 0/1.530 sin decir «stress test exploratorio de confinamiento por
  tres canales» y sin el límite no adaptativo.
- Omitir el 3,3 %.
- Confundir revisión de IA con acuerdo humano.
- Usar la demo Odoo como prueba estadística.
- Decir «ahorro» cuando solo se midieron tokens o escenarios.
- Responder con una promesa cuando el artefacto dice `pending`.

## Cierre

> La aportación no es pedirle al modelo que sea infalible. Es diseñar un
> sistema en el que una propuesta incorrecta pueda ser detenida y explicada.
> El modelo propone. El contrato decide.

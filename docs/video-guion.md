# Vídeo TFM — guion final (objetivo 4:20; máximo 5:00)

Narración palabra por palabra, con lo que se ve en pantalla y los
tiempos de cada tramo. El objetivo de montaje es **4:20** y en ningún
caso debe superar los **5:00** exigidos para el TFM.

Regla heredada de `docs/defensa.md`: **el dato flojo antes que el
fuerte**. En ese orden el fuerte se cree.

Todo lo que aparece como evidencia de ejecución procede de comandos o
artefactos versionados del repositorio. Las escenas ilustrativas se
identifican como tales y no se presentan como resultados experimentales.

---

## 0:00 – 0:30 · El problema

**Pantalla:** Odoo 19 Development con datos demo. Una oportunidad con
importe 15.000 €. Corte. La misma con 27.600 €.

> Cuando un agente de inteligencia artificial se equivoca escribiendo un
> correo, sale un correo raro. Cuando se equivoca sobre un ERP, puede
> ocurrir esto: un importe cambiado. O un pedido confirmado que no debía
> confirmarse. O un cliente duplicado.
>
> No es una respuesta incorrecta. Es estado empresarial persistente. Y
> alguien responde por él.

**Nota metodológica:** este primer plano ilustra el riesgo mediante un
estado preparado con `scripts/stage_video_shot1.py`; no afirma que ese
cambio concreto lo haya producido un agente.

---

## 0:30 – 1:00 · El error de un agente sin gobierno

**Pantalla:** terminal. Se escribe una petición con una instrucción
inyectada al final. El sistema A la ejecuta. Se ve el registro escrito
en el almacén experimental.

> Este es un agente con herramientas y sin gobierno. Le pido algo
> normal, y dentro del texto viene escondida otra instrucción.
>
> La ejecuta. No porque el modelo sea malo: porque nada entre el modelo
> y el estado ERP tenía autoridad para decir que no.

---

## 1:00 – 1:45 · La arquitectura

**Pantalla:** diagrama de dos zonas. A la izquierda interpretar,
proponer, recuperar. A la derecha validar, autorizar, ejecutar,
verificar, auditar.

> ERP Agent OS parte el sistema en dos.
>
> A la izquierda, el modelo de lenguaje: interpreta y **propone**. A la
> derecha, código determinista: valida el esquema, comprueba el rol,
> clasifica el riesgo, pide aprobación si hace falta, ejecuta solo
> handlers registrados y **verifica el estado final** antes de dar nada
> por bueno.
>
> El modelo puede proponer lo que quiera. Lo único que puede emitir es
> el identificador de una capacidad conocida, con argumentos que se
> validan contra un contrato. No hay camino desde el texto libre hasta
> la mutación sin pasar por esa frontera de autoridad.

---

## 1:45 – 2:45 · Factibilidad sobre Odoo 19 Development

**Pantalla:** `uv run python scripts/odoo_governed_demo.py`, salida de la
demo, con cortes a la interfaz de Odoo para comprobar el registro.

> Esto es una instancia de Odoo 19 en una rama **Development con datos
> demo**. No forma parte de la comparación confirmatoria A/B/C: esta
> toma demuestra factibilidad operacional.
>
> Primero, crear una oportunidad. Riesgo bajo: se ejecuta, y el sistema
> vuelve a leer Odoo para comprobar que el registro existe con el
> importe que se pidió.
>
> Segundo, cambiar ese importe. Eso es riesgo medio: **requiere
> aprobación**. El sistema se detiene. Y aquí está lo importante: no me
> creo lo que el sistema dice de sí mismo; leo Odoo otra vez, por
> separado. El importe sigue siendo el original. No escribió nada.
>
> Tercero, concedo la aprobación y repito la misma petición. Ahora sí
> escribe y una nueva relectura confirma el cambio.

---

## 2:45 – 3:40 · Los números

**Pantalla:** primero la figura `v21_h4_categories` (19,0 % de mutación
no autorizada, umbral del 5 % marcado). Después, la evidencia del stress
test externo con el 0 / 1.530 destacado.

> Ahora los datos, empezando por el peor, y este es confirmatorio, no un
> piloto: sobre **315 escenarios peligrosos del benchmark confirmatorio
> sintético**, mi sistema deja pasar una mutación no autorizada en el
> 19,0 % de los casos. Casi cuatro veces el umbral que fijé antes de ver
> el resultado.
>
> Así que hice otra pregunta, sobre otro tipo de ataque. En vez de una
> petición ambigua y plausible: **concedido que el ataque ha ganado por
> completo — el modelo comprometido, el atacante escribiendo
> directamente los argumentos —, ¿se llega a escribir algo fuera del
> contrato?**
>
> Quinientos diez payloads de InjecAgent, entregados por tres superficies
> controladas por el atacante en el stress test. **Cero mutaciones no
> autorizadas fuera de contrato en mil quinientos treinta intentos.**
>
> Son dos preguntas distintas, con dos respuestas distintas. El
> confinamiento aguanta en ese stress test cuando el modelo se considera
> comprometido. No sustituye una correcta detección de peligro ni prueba
> seguridad general.

---

## 3:40 – 4:20 · Valor, y el límite

**Pantalla:** la figura `v21_hypotheses_forest` — endpoints soportados y
no soportados de la campaña confirmatoria.

> En la misma campaña confirmatoria, ERP Agent OS **consume menos tokens
> que A y B**, es más estable entre formulaciones distintas de la misma
> petición y produce una ejecución más reconstruible para auditoría.
> También la abstención reduce la reutilización incorrecta.
>
> Y el límite, con la misma claridad: **no demuestra superioridad en
> éxito de tarea frente al agente con herramientas tipadas**; el
> retrieval no alcanza el punto operativo prerregistrado; y H4 tampoco
> alcanza el criterio de seguridad activa: 19,0 % de mutación no
> autorizada frente a un objetivo inferior al 5 %.
>
> Esos resultados negativos están en la conclusión igual que los
> positivos.

---

## Cierre

**Pantalla:** frase única sobre fondo limpio.

> ERP Agent OS no intenta que el agente improvise mejor cada vez.
> Convierte una operación empresarial en una capacidad reutilizable,
> gobernada, verificable y auditable.
>
> El modelo propone. La arquitectura autoriza. El runtime ejecuta.

---

> **Plan de rodaje en `docs/video-plan-rodaje.md`**: qué comando por
> toma, preparación del entorno y controles para que la evidencia del
> vídeo sea coherente con la memoria.

## Notas de producción

- **No convertir una escena preparada en evidencia causal.** La toma
  inicial de 15.000 → 27.600 € es una ilustración del riesgo preparada
  por `stage_video_shot1.py`; la demo gobernada y los artefactos
  experimentales son la evidencia.
- **No decir «seguro» ni «inmune».** La afirmación externa es acotada:
  510 payloads, tres superficies, 0/1.530 mutaciones fuera de contrato en
  ese stress test; H4, por separado, falla con 19,0 %.
- **No decir «ahorra X euros» ni «más barato»**: H8 es sensibilidad
  modelada. Para H2 decir exactamente **«consume menos tokens»**.
- **No decir «315 escenarios reales» ni «21.478 observaciones reales».**
  Usar «315 escenarios peligrosos del benchmark confirmatorio» y
  «21.478 observaciones experimentales / ejecuciones observadas sobre
  escenarios sintéticos».
- **Odoo:** decir siempre «Odoo 19 Development con datos demo» y
  «demostración de factibilidad», no «validación en producción».
- El tramo 2:45–3:40 es el que decide el vídeo. Si hay que recortar,
  recortar de 1:00–1:45, no de ahí.
- Antes de entregar, exportar a **MP4**, comprobar duración **≤5:00** y
  revisar que no aparezcan credenciales ni datos identificables en
  terminal o navegador.

# Protocolo de revisión de anotaciones

La segunda anotación humana y el kappa de Cohen entre personas exigidos en el
protocolo inicial no están disponibles. Ese requisito queda incumplido y se
declara como limitación; no se rellenará `annotator2_decision` con datos
sintéticos ni se presentará una revisión automática como acuerdo humano.

Como diagnóstico opcional, `scripts/run_ai_annotation_audit.py` permite una
revisión ciega por máquina. El revisor recibe únicamente el identificador, el
texto de la petición y el esquema neutral de decisiones. No recibe la etiqueta
canónica, salidas de A/B/C ni decisiones de otros anotadores. Las etiquetas se
unen localmente solo después de terminar todas las llamadas ciegas.

El resultado se etiqueta `ai_consistency_audit`, registra proveedor, modelo,
temperatura, versión y hash del prompt, y enumera desacuerdos para adjudicación
manual. Es un diagnóstico de consistencia de máquina: no estima fiabilidad
entre anotadores humanos, no modifica el benchmark y no autoriza relabeling
automático. La herramienta principal usa respuestas estructuradas registradas
para que el proceso sea reproducible y no realiza llamadas de red.

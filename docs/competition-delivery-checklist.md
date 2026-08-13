# Checklist de entrega — competición de becas

**Fecha límite comunicada:** 24 de septiembre de 2026, 23:59, hora española.
**Formato:** vídeo de 3–5 minutos; enlace de YouTube en oculto dentro del
fichero solicitado por UCM. La competición es independiente del TFM.

## Estado verificable del repositorio

- [x] Los artefactos históricos están clasificados en
  `data/evidence_registry.json`.
- [x] Ninguna corrida v1 se presenta como resultado confirmatorio.
- [x] Runtime y System C ejecutan checks nombrados y conservan evidencia.
- [x] Clarificación, abstención, denegación y errores fallan cerrados.
- [x] Idempotencia vincula la clave a la petición y evita duplicados.
- [x] Snapshot y postcondiciones funcionan con FakeERP y adaptador Odoo.
- [x] Audit de anotación con IA disponible y etiquetado como IA.
- [x] No se informa acuerdo humano sin segundo anotador.
- [x] Detector externo 3,3 % presentado como resultado negativo.
- [x] El 0/1.530 lleva alcance de stress exploratorio de confinamiento por
  tres canales y límite no adaptativo.
- [x] Stress consciente del catálogo publicado con hallazgo y caso no cubierto.
- [x] Protocolo v2, freeze gate, checkpoint cifrado y análisis implementados.
- [x] Cinco SVG 1920×1080 generados, probados y revisados visualmente.
- [x] Guion literal de 4:30 y plan de rodaje de una toma Odoo preparados.

## Puertas antes de congelar v2

- [ ] Obtener credenciales operativas para un autor de textos y un selector
  A/B/C de proveedor/modelo distinto.
- [ ] Generar 120 casos v2 sin reutilización exacta de v1.
- [ ] Ejecutar el audit de consistencia por IA y resolver/documentar hallazgos
  sin reetiquetado automático.
- [ ] Fijar el executor A/B/C compatible con el `RunConfig` congelado y con
  identificadores reales de llamada.
- [ ] Ejecutar revisión independiente final de código y metodología.
- [ ] Lograr árbol limpio y pasar `make competition-readiness`.
- [ ] Crear y commitear el manifiesto; tag exacto `v2-protocol-freeze`.
- [ ] Ejecutar A/B/C una sola vez, sin observar ni publicar parciales.
- [ ] Validar 1.080 observaciones y publicar incluso si el resultado es nulo o
  adverso.

**Regla:** si falta cualquiera de esas puertas, v2 permanece `pending`. No se
usa una cifra v1 para rellenar la diapositiva.

## Puertas externas que el repositorio no puede completar

- [ ] Segundo anotador humano independiente — actualmente no disponible; no
  bloquea el prototipo, sí limita validez de constructo.
- [ ] Revisión y aprobación del tutor.
- [ ] Maquetación final de la memoria en la plantilla oficial y control de
  extensión/paginación.
- [ ] Grabación de voz y cámara por el autor.
- [ ] Grabación de la toma continua en una instancia Odoo de desarrollo.
- [ ] Subtítulos revisados manualmente y comprobación de accesibilidad.
- [ ] Subida a YouTube en oculto y verificación del enlace desde otra sesión.
- [ ] Entrega del fichero con el enlace en el campus virtual.

## Ensayo y control del vídeo

- [ ] Duración exportada entre 4:20 y 4:50; nunca superior a 5:00.
- [ ] Primeros 50 segundos: riesgo y pregunta de investigación.
- [ ] El método y el freeze aparecen antes de cualquier cifra.
- [ ] La demo lleva rótulo `DEMOSTRACIÓN · NO RESULTADO A/B/C`.
- [ ] La tarjeta de resultados lleva `V2 PENDIENTE` si sigue faltando.
- [ ] Toda cifra v1 lleva `EXPLORATORIO` en el mismo plano.
- [ ] Se pronuncia el 3,3 % y su significado negativo.
- [ ] Se declara el hallazgo del stress consciente del catálogo.
- [ ] No aparecen claves, URLs privadas, clientes, correos ni notificaciones.
- [ ] El cierre es literal: «El modelo propone. El contrato decide.»

## Comandos de liberación

```powershell
make competition-readiness
# equivalente nativo en Windows:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/competition_readiness.ps1
git status --short
git diff --check
```

Si existe un PDF final de memoria, añadir antes de entregar:

- [ ] conteo de páginas conforme a la guía UCM;
- [ ] revisión visual de todas las páginas;
- [ ] fuentes, tablas, figuras y enlaces legibles;
- [ ] ausencia de páginas en blanco o contenido cortado.

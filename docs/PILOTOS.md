# Pilotos de seguridad y calidad

Decisión de producto: 17/11/2026, America/La_Paz. Alcance aprobado: casco/chaleco
en un área y presencia/colocación de tapa en botellas después del tapado.

## Alcance y estado

EPP tiene un flujo inicial de video y revisión humana en `/monitoreo/`.
Calidad conserva la inspección manual en `/produccion/`; los clasificadores
experimentales siguen fuera del flujo operativo. Ningún piloto está validado
para operación autónoma. No hay nuevas capturas industriales disponibles.

Se trabaja con una cámara fija por piloto. El responsable de planta debe identificar
área, cámara, línea, producto y etapa reales en `config/pilotos.json` y confirmar
los criterios con el responsable de seguridad/calidad. Ese archivo documenta el
alcance; no cambia automáticamente la configuración Django ni habilita modelos.

## Escenario acordado de simulación

No hay cámaras físicas ni área/línea industrial definitivas. Se reutilizan el área
y la cámara EPP registradas (ambas ID 1), con casco y chaleco obligatorios para el
escenario de prueba, y `media/videos/trabajadores.mp4`. Se guardó una copia SQLite
antes de añadir esas dos relaciones en `output/pilotos_20261117/`; no se modificó
el video ni se crearon identidades de trabajadores.

Para repetir el flujo completo con inferencia real sobre ese video:

```powershell
.\venv\Scripts\python.exe -B scripts/simular_epp.py --camara 1
```

El script lee la cámara y sus reglas reales, pero crea usuario y detecciones en
SQLite en memoria. Escribe una ejecución nueva en `media/resultados_ia` y muestra
la URL del reporte, consultable desde la aplicación con permisos normales.
No escribe detecciones simuladas en la base operativa ni guarda revisiones con
usuarios ficticios. La configuración de reglas del área sí se guardó por decisión
del usuario para poder probar también desde la interfaz.

Para calidad se reutiliza `pruebas_ia/botellasSinTapa.mp4` en el pipeline
experimental individual. El nombre del video no acredita un defecto ni que sea
posterior al tapado: esa etapa permanece sin confirmar. La prueba registra la
capacidad de localización y abstención; no aprueba un modelo de calidad.

Las metas de captura y aceptación siguientes quedan como requisitos para una
futura validación representativa; las simulaciones no las satisfacen por sí solas.

## Preparación de EPP

1. En `/admin/`, configurar el área y sus equipos obligatorios con nombres Casco
   y Chaleco (también se aceptan Hardhat y Safety Vest). No se asignaron reglas
   a datos reales sin conocer el área. Un área sin reglas o con otro EPP bloquea
   este piloto, evitando ignorar obligaciones fuera de alcance.
2. Configurar una cámara EPP, fuente VIDEO, con un MP4 original representativo.
3. El operador requiere `seguridad.add_deteccionepp`. El lector de reportes requiere
   `seguridad.view_deteccionepp`; el supervisor, `seguridad.change_deteccionepp`.
4. Analizar desde `/monitoreo/`. Cada ejecución conserva video, evidencia JPEG,
   hash del original y pesos, reglas y reporte en
   `media/resultados_ia/camara_<id>/<uuid>/`. Las diez ejecuciones más recientes
   aparecen en cámaras para usuarios con permiso de consulta. Conservar la URL
   del reporte para acceder a ejecuciones anteriores.
5. Revisar cada candidato: confirmado, falsa alarma o no evaluable, con observación.
   El historial registra usuario y fecha; una revisión desactualizada se rechaza.

La asociación geométrica se abstiene ante personas ambiguas. Sin detección
explícita de presencia/ausencia, el estado es NO_EVALUABLE. Evidencia positiva y
negativa simultánea también se abstiene. El candidato requiere evidencia negativa
continua durante 2 segundos y separación máxima de 0,5 s entre observaciones.
Una pérdida de track o visibilidad reinicia la persistencia. Una recurrencia tras
interrupción es un episodio nuevo. Los IDs son temporales, no identidades laborales.

Los reportes son de piloto en disco local: no constituyen un registro distribuido
de incidentes, no envían notificaciones y no tienen cola de tareas. El procesamiento
continúa siendo síncrono. El tiempo de video se calcula por frame/FPS; reservar
este piloto para MP4 de FPS constante. Un cambio de ID puede dividir un incidente.
Las detecciones históricas siguen siendo observaciones y no incidentes.

## Preparación de calidad

Inspeccionar después del tapado, con tapa obligatoria. Para cada SKU, documentar
una referencia de tapa correcta, tolerancias de colocación y vistas necesarias.
Clasificaciones: tapa ausente, mal colocada, correcta respecto del criterio visible,
y NO_EVALUABLE. No se certifica hermeticidad, torque ni superficies ocultas.

Reutilizar el anotador de ENVASE/TAPA en
`datasets/calidad_botellas/v002/experiments/detection_manual_v001/COMENZAR.md`.
Primero localizar envase/cuello/tapa y revisar visibilidad; después etiquetar calidad.
La etiqueta de objeto TAPA acredita presencia, no colocación correcta. El modelo
experimental de escena no sustituye esa localización ni supera aún la referencia
mayoritaria en exactitud. No se habilita rechazo automático con esos pesos.

El registro manual de calidad existente permanece utilizable, pero no enlaza por
sí mismo cada unidad con un recorte del video. Esa asociación es un requisito de
la próxima integración, después de validar detector y criterio en datos reales.

## Captura y aceptación

Usar `docs/capturas_piloto.csv` como registro inicial. Una fila por video original;
conservar el original sin overlays, su SHA-256 y procedencia. No inventar valores
faltantes ni usar los videos de desarrollo como test final.

- Capturar al menos 3 sesiones independientes por piloto, ampliando si faltan
  condiciones de operación. Cubrir iluminación, distancia, oclusión, personas
  cercanas y variación normal de producto. Reservar sesiones completas para test.
- EPP: objetivo inicial de evaluación de 50 episodios reales de incumplimiento
  y 50 intervalos de cumplimiento, por equipo obligatorio. Calidad: 50 unidades
  por estado evaluable (ausente, mal colocada, correcta) y 30 no evaluables.
  Son mínimos de planificación, no demostración estadística de fiabilidad.
- Etiquetar de manera exhaustiva el test con un responsable identificado y segundo
  revisor; resolver discrepancias. Agrupar por sesión y unidad física para evitar
  vistas del mismo objeto repartidas entre entrenamiento y test.
- Fijar antes de medir: EPP precisión y recall por equipo/episodio >=95%; calidad
  precisión y recall de defecto >=95%, desglosados por ausente/mal colocada.
  Informar también falsas alarmas por hora, omisiones, cobertura evaluable y latencia.
- Meta inicial de cobertura evaluable >=90% en el encuadre acordado. No ocultar
  omisiones bajo abstenciones: informar recall completo del sistema y cobertura
  aparte. Publicar tamaños de muestra e intervalos de incertidumbre por sesión.
- Cero conformidades automáticas cuando falta visibilidad o localización suficiente.
  Toda alerta del piloto pasa por revisión humana. Para una alerta EPP confirmada
  medir retraso desde inicio de evidencia; objetivo <=3 s de tiempo de video.

Estas metas son propuestas de aceptación para el piloto y deben acordarse con
planta. Si el conjunto no alcanza cobertura, el resultado es INSUFICIENTE, no
aprobado. Las pruebas de software no acreditan estos porcentajes.

## Orden de implementación restante

1. Completar identificación de área/línea/SKU y capturar evidencia real.
2. Anotar y congelar test independiente; validar detección, asociación y abstención.
3. Ajustar detector de envase/tapa y clasificador de colocación si la evaluación
   demuestra que los actuales no sirven. Mantener selección separada del test.
4. Integrar evidencia por unidad y revisión en calidad cuando supere las metas.
5. Tras medir tiempos, introducir tareas en segundo plano, estado de ejecución,
   límites de recursos, reintentos y notificaciones. Después ampliar cámaras/SKU.

No ampliar todavía a cajas: conservar su registro manual y diseñar un perfil de
cierre/sellado específico cuando ambos pilotos hayan superado la evaluación.

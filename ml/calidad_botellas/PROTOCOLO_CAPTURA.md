# Protocolo de captura real de botellas — versión 1

## Alcance

Preparar datos reales para inspección visual; no certificar defectos, entrenar ni
reemplazar CU-09/CU-10/CU-11. El extractor es un proceso offline independiente.
No se conecta a Django mediante ORM ni escribe en SQLite. No guardar evidencia
sintética ni imágenes de pruebas unitarias dentro del dataset real.

## Antes de capturar

1. Definir producto/SKU, estado esperado de la botella y tapa, referencias conformes
   y tolerancias de rechazo con el responsable de calidad. Una botella abierta
   puede ser normal en una etapa anterior al tapado: registrar la etapa.
2. Registrar sesión, fecha, cámara, lote, producto, etapa, velocidad de cinta,
   resolución/FPS, exposición, iluminación, fondo y responsable. No cambiar
   ajustes sin registrar una sesión o subgrupo nuevo.
3. Limpiar la óptica; fijar cámara y luz difusa. Evitar reflejos dominantes,
   contraluz y movimiento de cámara. Una exposición corta debe conservar señal
   suficiente. Revisar que tapa, contorno y superficie tengan detalle visible.
4. Grabar originales MP4 H.264/MPEG-4 compatibles con la validación existente:
   máximo 100 MiB, 120 segundos, Full HD, 60 FPS y 7200 fotogramas. Preferir
   frecuencia constante; el tiempo guardado es fotograma/FPS nominal y no PTS
   exacto en frecuencia variable. No reescalar ni anotar el original.

## Qué capturar

- Botellas distintas conformes, con rayaduras, deformaciones, tapas defectuosas,
  combinaciones reales y casos no evaluables. No deducir defectos por el nombre
  del video, el lote o la presencia de una etiqueta externa.
- Recoger negativos difíciles: costuras, logotipos, gotas, reflejos y perspectivas.
- Incluir defectos leves y severos, cambios de día/lote/iluminación y velocidades
  operativas. No provocar situaciones inseguras en la línea para obtener muestras.
- Dar a cada botella física un ID externo de inventario, sin colocar marcas
  visibles que permitan al modelo aprender la etiqueta. Si reaparece en otro
  video, conserva su ID físico aunque cambie el track de ByteTrack.
- Asociar el video original a un análisis de botellas por el flujo existente.
  El extractor exige un análisis real y comprueba igualdad SHA-256 del original;
  no crea análisis ni cambia sus registros.

## Muestreo y calidad

Se guardan hasta cinco vistas por ID contado en esta ejecución. Debe haber al
menos 0,4 segundos entre vistas seleccionadas. Se comparan pHash y diferencia
media de grises normalizados para reducir imágenes casi idénticas; una vista
muy similar puede reemplazarse por otra de mejor calidad técnica. Las vistas
se guardan en su resolución original PNG, sin overlays ni corrección de imagen.

Las marcas automáticas son avisos de revisión: tamaño menor de 64x128, varianza
Laplaciana menor de 40, más de 40 % de píxeles oscuros (<=10) o brillantes (>=245),
y botella tocando el borde. Son umbrales iniciales, dependientes de cámara y
textura. No garantizan detectar desenfoque, oclusión, rayaduras ni tapa oculta.
La transparencia puede producir avisos de exposición en imágenes utilizables.

`images/unlabeled/` contiene muestras sin avisos técnicos y `images/review/`
contiene muestras para revisar. Ambas siguen SIN etiquetas de defectos.
No descartar automáticamente todos los casos de revisión: son necesarios para
enseñar posteriormente NO_EVALUABLE. Conservar también el registro de tracks sin
recortes en `run.json`; no ocultarlos del análisis de cobertura.

El muestreo puede perder un defecto breve al reducir vistas; el anotador debe
consultar el video original. Si el daño no es visible en el recorte concreto,
no copiarle una etiqueta positiva solo porque otro fotograma la tenga.

## Volumen y separación

Para un piloto, planificar 300–500 botellas conformes, 150–300 positivas por
defecto y 150–300 no evaluables, incluyendo combinaciones. No son garantías de
rendimiento ni un permiso para entrenar. Una botella con cinco recortes sigue
siendo una sola unidad independiente. Un video de ocho botellas es solamente
una demostración técnica y no constituye un dataset suficiente.

La partición futura sugerida es 70/15/15 por sesión/lote y botella física,
nunca por fotogramas aleatorios. El mismo video, sesión o botella no puede
cruzar particiones. Reservar capturas de otro día para prueba independiente.
Los IDs de sesión y botella física deben ser únicos en todo el dataset.

## Cierre de sesión

Registrar incidencias, visibilidad de cada región, responsables y discrepancias.
Versionar manifiestos y taxonomía. No sobrescribir originales ni una extracción
anterior. Las repeticiones de extracción tienen UUID diferente: no mezclar sus
recortes como nuevas botellas ni asumir que los IDs de seguimiento son estables.

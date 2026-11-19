# Anotación manual de detección EPP v002

Esta herramienta prepara cajas humanas de **objetos**, no etiquetas de defectos. No importa resultados de YOLO ni ByteTrack, no carga clasificadores y no entrena. Las clases exportadas son `0 ENVASE` y `1 TAPA`; `TAPA` no significa `TAPA_DEFECTUOSA`. RAYADURA y DEFORMACION siguen NO DISPONIBLE.

## Abrir y empezar

Desde `C:\Users\Usuario\sistema_epp`, ejecutar en PowerShell:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py serve --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset --port 8792
```

Abrir **http://127.0.0.1:8792/**. El servidor es local y permanece en esa terminal; detener con Ctrl+C. No abrir index.html con doble clic: el guardado requiere el servidor. No ejecutar dos servidores sobre el mismo dataset. Autor es un identificador declarado por quien anota; esta herramienta local no autentica personas ni certifica una revisión independiente.

1. Escribir su autor real y elegir un fotograma. El dataset inicial tiene 25 imágenes, sin cajas ni IDs físicos precargados.
2. Elegir ENVASE o TAPA en «Clase nueva». Arrastrar sobre la imagen para crear un rectángulo. Las coordenadas se guardan en píxeles originales, independientemente del tamaño de visualización.
3. Seleccionar el objeto en la lista. Modificar X1/Y1/X2/Y2 para redimensionar, o elegir «Seleccionar / mover» y arrastrar. La ampliación 100%/200% permite revisar tapas pequeñas; el área tiene desplazamiento.
4. Resolver «Parcialmente visible», «Ocluido» y «No evaluable» solo cuando haya evidencia. Inicialmente son **null**, sin valores humanos inventados. Un borrador admite desconocidos; para finalizar hay que decidir estos atributos.
5. ID físico es opcional. Mantener vacío si no se sabe cuál es la botella real. Nunca copiar automáticamente un ID de seguimiento temporal como identidad física. Una tapa puede asociarse opcionalmente a la caja ENVASE del mismo fotograma; puede quedar sin asociación si está suelta o no se conoce la correspondencia.
6. Pulsar **Aplicar cambios al objeto** después de editar sus campos. El guardado se bloquea si hay campos de objeto editados sin aplicar.
7. Añadir observaciones. Pulsar **Guardar borrador** para continuar posteriormente. Cada guardado crea una revisión nueva: no reemplaza la anterior. Al reabrir se recupera la última revisión. La eliminación de una caja solo afecta la nueva revisión; su historial permanece.
8. Al terminar, confirmar explícitamente que se revisaron todos los objetos objetivo del fotograma y pulsar **Guardar como revisado**. Esto registra exhaustividad del anotador, no aprobación de un segundo revisor. Si se edita una caja, debe confirmarse nuevamente la exhaustividad.
9. Una imagen sin cajas no es una negativa automática. Solo se puede finalizar vacía confirmando que realmente no hay ENVASE ni TAPA visibles. No usar esta opción para escenas ilegibles o donde se desconoce si faltan objetos.
10. Usar Siguiente para avanzar. La herramienta avisa antes de descartar cambios sin guardar. Si otra ventana guardó antes, se rechaza la versión obsoleta: conservar sus notas y volver a cargar para reconciliar; no se fusionan cajas silenciosamente.

## Convención de cajas

- **ENVASE**: caja ajustada al cuerpo y cuello observables del recipiente plástico. La tapa se anota por separado. En envases parcialmente fuera del fotograma u ocultos se delimita la extensión visible; no se reconstruye la silueta oculta. Marcar `partial=true` si no se ve completo, `occluded=true` si otro objeto lo oculta. Esta convención de extensión visible debe mantenerse en futuras incorporaciones.
- **TAPA**: caja ajustada al objeto tapa visible, colocado o suelto. No extenderla arbitrariamente sobre el cuello. No dibujar una tapa ausente ni una caja vacía de «posible colocación». El asiento sin tapa no es una tercera clase; describirlo si interesa. La relación de colocación se registra con la asociación humana a ENVASE cuando sea verificable.
- Maquinaria, guías, aros o piezas amarillas no son tapas por su color. La clase debe determinarla una persona. Un envase aplastado no genera automáticamente una etiqueta DEFORMACION.
- Si se localiza un objeto pero es ambiguo o no puede delimitarse con seguridad, marcar `not_evaluable=true` y explicar. Si no puede localizarse, dejar el fotograma como borrador y describir la zona; no inventar su caja.
- Evitar duplicar el mismo objeto. Cajas de una misma clase con IoU > 0,85 se señalan para revisión, sin borrarlas. Un ENVASE y una TAPA pueden solaparse legítimamente.

## Qué se guarda

```text
detection_manual_v001/
  annotate.py, index.html, app.js, style.css
  COMENZAR.md, INFORME_TECNICO.md, test_manual.py, run_tests.py
  dataset/
    manifest.json                 # videos, fuentes, hashes, PTS reales, muestreo
    images/*.png                  # fotogramas derivados completos, sin sobrescritura
    revisions/<sample_id>/000001.json, 000002.json, ...
    grouping_revisions/000001.json, ...  # solo al declarar sesión/partición
    exports/<fecha_UUID>/
      labels/<partición>/<sample_id>.txt
      traceability.json
  output/                         # informes, pruebas y capturas de interfaz
```

Las imágenes PNG son originales de la **extracción**, no los bytes del MP4. El manifiesto registra ambos hashes. El frame index comienza en cero. `pts_seconds` procede de ffmpeg; `timestamp_seconds` es PTS menos el PTS inicial, no tiempo de procesamiento. No se inventaron fecha de captura, licencia, propietario, sesión ni material: siguen desconocidos. La fecha UTC de preparación y la de cada anotación son fechas de operaciones reales.

El JSON de revisión conserva autor, fecha, coordenadas, atributos, observaciones y copia de la trazabilidad del fotograma. El hash de la revisión anterior permite detectar alteraciones de la cadena. Los archivos son locales: los hashes no sustituyen un respaldo ni una firma de identidad.

## YOLO y validación

El botón de exportación y este comando producen una **instantánea nueva**, sin mover imágenes:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py export --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset
```

Formato: `class_id centro_x centro_y ancho alto`, normalizado por las dimensiones originales. JSON conserva lo que YOLO no representa: autor, atributos, identidades opcionales, asociaciones y grupos. Incluye ruta absoluta de imagen, hash del label, fuentes de video y revisión de agrupación. No crea YAML de entrenamiento, no copia imágenes a train/test y no ejecuta entrenamiento.

Solo exporta fotogramas revisados exhaustivamente. **Si hay algún objeto no evaluable, omite todo el fotograma**: eliminar solo esa caja lo convertiría incorrectamente en fondo para YOLO estándar. También omite borradores y SHA duplicados. Una imagen vacía requiere confirmación humana explícita. Las particiones pendientes se exportan bajo `UNASSIGNED`, nunca como entrenamiento autorizado. La exportación es para inspección técnica, no certifica derechos ni suficiencia.

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py report --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset
```

El informe verifica videos y PNG, historial, hashes, dimensiones, cajas, clases, exhaustividad y componentes. Separa conteos revisados de conteos que incluyen borradores y señala regiones pequeñas, solapamientos y posibles problemas técnicos. `--output` permite guardar un JSON **nuevo**, dentro de este experimento; nunca sobrescribe informes anteriores.

## Particiones, sesiones e incorporación futura

No dividir al azar por imagen. Un componente une todos los fotogramas de un video, sesiones compartidas, IDs físicos declarados, SHA idénticos y candidatos dHash a distancia ≤4. Las sesiones desconocidas se unen conservadoramente entre sí. La semejanza es una alerta y una unión preventiva, no prueba de identidad física; puede pasar por alto duplicados con distinto encuadre. Si un nuevo ID físico conectara train y test, el guardado se rechaza hasta corregir la planificación de particiones.

Los dos videos de referencia **ya se usaron para desarrollar la canalización**: no son un test independiente final, aunque se declaren sesiones diferentes. Hacen falta nuevas grabaciones reservadas y botellas/sesiones realmente distintas para evaluar generalización.

Cuando se conozca una sesión real, se declara explícitamente (sustituir los valores en mayúsculas por información real; no ejecutarlos como metadatos ficticios):

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py assign --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset --video-id VIDEO_ID_DEL_MANIFIESTO --author SU_AUTOR_REAL --session-id SESION_REAL_CONFIRMADA
```

Solo después de revisar grupos, se puede asignar **un componente completo**. El resultado muestra los videos afectados. Si todavía comparten sesión desconocida, ambos se asignarían juntos; no se puede conseguir tres particiones independientes con un único componente:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py assign --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset --video-id VIDEO_ID_DEL_MANIFIESTO --author SU_AUTOR_REAL --split train
```

También admite `validation`, `test` y `UNASSIGNED`. Esta fase no ejecutó ninguna asignación. Para agregar grabaciones, preparar una versión nueva, conservando la existente. Repetir `--input` para incluir TODOS los videos que deban compararse y agruparse juntos. No combinar exports de distintas versiones sin recalcular grupos por video, sesión, identidad física y semejanza.

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py prepare --output datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset_v002 --input RUTA_REAL_VIDEO_1.mp4 --input RUTA_REAL_VIDEO_2.mp4 --interval 1.0
```

La salida debe ser nueva. El muestreo temporal recorre todo el video sin detecciones; no garantiza representatividad semántica ni objetos independientes. Acepta MP4 H.264/MPEG-4 bajo los límites del validador existente. Los derechos de nuevas fuentes requieren confirmación documentada antes de entrenar; esta herramienta no atribuye licencias automáticamente.

## Pruebas

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/test_manual.py
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/run_tests.py
```

El segundo comando ejecuta las regresiones existentes con SQLite en memoria, medios temporales y migraciones desactivadas. Guarda logs separados en `output/tests/`. Las cajas de prueba se usan únicamente en fixtures temporales y se eliminan después; no se incorporan al dataset real.

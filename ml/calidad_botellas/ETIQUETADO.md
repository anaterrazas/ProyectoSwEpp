# Revisión y etiquetado local, sin cambiar la extracción

## Inicio

Desde la raíz del proyecto:

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.label_dataset `
  --dataset datasets/calidad_botellas/v001/runs/referencia_a3 `
  --workspace datasets/calidad_botellas/v001/labeling/revision_humana_001
```

Abrir **http://127.0.0.1:8766**. Para detener el servidor, Ctrl+C. No necesita
levantar Django, iniciar sesión en Django ni instalar dependencias nuevas.
Usar el mismo comando para reanudar: carga las revisiones existentes. El servidor
solo escucha en localhost; no publicarlo ni abrir el puerto a la red.

La herramienta verifica integridad y duplicados de las 19 imágenes. La galería
muestra botella, fotograma y estado, y permite ampliar cada imagen y filtrar
pendientes/borradores/cerradas. La referencia de track solo es válida dentro de
su ejecución de seguimiento. Las imágenes se sirven en su forma original.

## Etiquetar sin inventar información

1. Escribir el nombre o identificador de la persona que realiza la acción.
   Es una identidad declarada para trabajo local, no autenticación de Django.
2. Revisar imagen, ID y fotograma. Consultar el video original por separado si
   es necesario; la herramienta no sirve videos ni permite acceder a media.
3. Indicar si cuerpo y tapa son suficientemente evaluables. Dejar desconocido
   si todavía no se tomó esa decisión.
4. Para RAYADURA, DEFORMACIÓN y TAPA_DEFECTUOSA seleccionar presente, ausente o
   desconocido. Varios defectos pueden ser positivos. Ausente requiere región
   evaluable. No interpretar reflejos, costuras o perspectiva como daño.
5. Completar otros defectos y la conclusión humana. CONFORME solo se permite si
   ambos componentes son evaluables, todos los defectos están ausentes, no hay
   otros defectos y NO_EVALUABLE es No. NO_EVALUABLE puede coexistir con un
   defecto visible; explicar el motivo y mantener desconocidos los atributos
   no visibles. No se etiqueta automáticamente al abrir o navegar.
6. Guardar borrador. El servidor asigna autor y fecha UTC; las modificaciones
   posteriores conservan el autor inicial y registran quién y cuándo corrigió.
7. Un revisor distinto del anotador inicial verifica la muestra, cambia el
   nombre de persona y pulsa Revisar y cerrar. Las correcciones se guardan
   antes como borrador. El cierre exige decidir categorías y evaluabilidad;
   si queda incertidumbre, debe indicarse NO_EVALUABLE, nunca CONFORME.
8. Una muestra cerrada queda bloqueada. Para corregirla, Reabrir para corregir,
   editar, guardar y revisar de nuevo. Las decisiones anteriores permanecen
   en las versiones previas y en el historial de acciones.

El formulario avisa al navegar o cerrar con cambios sin guardar. En conflicto
de pestañas, no reemplaza los datos guardados ni borra lo escrito del formulario;
copiar las observaciones necesarias y recargar para reconciliar manualmente.

### Campos que exige el cierre del supervisor

No hay atributos ocultos ni se deben crear nuevas etiquetas. La sección
«Requisitos para cerrar esta muestra» enumera exactamente las decisiones pendientes
y permite enfocar el campo correspondiente. El servidor también devuelve los
nombres concretos si se intenta cerrar con una decisión sin completar.

| Campo JSONL | Control visible | Decisión necesaria para cerrar |
| --- | --- | --- |
| `evaluable.body` | Cuerpo evaluable | Sí o No |
| `evaluable.cap` | Tapa evaluable | Sí o No |
| `other_defect` | Otros defectos visibles fuera de taxonomía | Sí o No |
| `categories.CONFORME` | CONFORME | Sí o No |
| `categories.NO_EVALUABLE` | NO_EVALUABLE | Sí o No |

Los defectos individuales sí pueden conservar `null` cuando no sean evaluables,
con NO_EVALUABLE=Sí y una justificación. «Desconocido» en los cinco campos de la
tabla permite conservar el borrador, pero no cerrarlo; no se rellena ningún valor
automáticamente. El mensaje anterior usaba términos internos («evaluabilidad» y
«categorías») y no señalaba cuál faltaba, aunque sus controles ya existían.

Si el supervisor completa o corrige un campo, debe pulsar **Guardar borrador** y
después **Revisar y cerrar**. El anotador inicial y su fecha se conservan; la
corrección añade al supervisor como autor de la acción y el cierre lo registra
como revisor. No se reescriben versiones JSONL anteriores.

Después de actualizar el código, guardar primero cualquier edición pendiente y
reiniciar el servidor con el MISMO `--workspace`; recargar la página. No iniciar
un espacio vacío ni sustituir los borradores para resolver un problema de interfaz.

## Almacenamiento

```text
datasets/calidad_botellas/v001/
├── runs/referencia_a3/             # intacto, fuente de imágenes y procedencia
│   ├── run.json
│   ├── samples.jsonl
│   └── images/unlabeled/*.png
└── labeling/revision_humana_001/
    ├── workspace.json             # fuentes y sus hashes + versión de taxonomía
    └── revisions/
        ├── 000001.jsonl            # foto completa de las 19 muestras al guardar
        ├── 000002.jsonl            # nueva versión; nunca sobrescribe la anterior
        └── ...
```

Antes del primer guardado no hay archivos de revisión ni etiquetas asignadas.
Se preserva el JSONL original y todos sus campos de procedencia. Las versiones
añaden `categories` (CONFORME/NO_EVALUABLE), `notes`, `annotated_at`, `reviewed_at`,
`updated_by`, `updated_at` y `annotation_history`. Se conserva la clave estable
`DEFORMACION` sin acento; la interfaz presenta DEFORMACIÓN. Los desconocidos
se guardan como `null`. `annotation_status` usa PENDING/ANNOTATED/REVIEWED.

Cada guardado escribe un JSONL completo en un temporal, sincroniza el archivo y
lo publica mediante renombrado. Un bloqueo exclusivo impide escritores simultáneos
y una revisión esperada detecta pestañas desactualizadas. No mezclar manualmente
revisiones ni modificar fuentes mientras el servidor está abierto.

La descarga JSONL produce la versión actual completa sin modificar archivos.
Las rutas `image` siguen siendo relativas a la extracción correspondiente: para
resolverlas usar el `run_id` y el registro de fuentes de `workspace.json`, no la
carpeta de descargas. Los identificadores de sesión/botella física y las
particiones de entrenamiento siguen pendientes; cerrar una muestra no habilita
entrenamiento ni certifica la identidad física del track.

No hay cifrado ni autenticación de personas en esta utilidad local, ni firmas
criptográficas contra edición externa de las revisiones. Proteger la carpeta
mediante permisos del sistema y respaldarla con todas sus versiones. Si se corta
el proceso mientras guarda, no borra revisiones previas; puede quedar un `.tmp`
o `.write.lock`. Confirmar que no haya otro servidor activo y respaldar antes de
retirar manualmente un bloqueo residual. Nunca borrar un JSONL para resolverlo.

Para comprobar una carpeta sin abrir el navegador:

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.label_dataset `
  --dataset datasets/calidad_botellas/v001/runs/referencia_a3 `
  --workspace datasets/calidad_botellas/v001/labeling/revision_humana_001 --check
```

## Incorporar nuevas imágenes

1. Capturar originales reales con el protocolo y extraer en una NUEVA carpeta
   mediante `extract_crops`, con el análisis correcto. No añadir ni reemplazar
   PNG directamente en una extracción ya registrada.
2. Validar todas las ejecuciones a combinar con `validate_dataset`, para detectar
   duplicados exactos y fugas entre particiones. Revisar visualmente los casi
   duplicados entre videos/ejecuciones; el hash no detecta todos esos casos.
3. Etiquetar cada ejecución nueva en un espacio independiente. Así no se pierden
   ni se reinician las anotaciones de las imágenes anteriores.
4. Alternativamente crear un espacio NUEVO pasando varias carpetas tras
   `--dataset`. La herramienta rechaza IDs e imágenes exactas duplicadas.
   No cambia el registro de fuentes de un espacio existente. Un espacio combinado
   nuevo parte de las fuentes originales: NO importa automáticamente las etiquetas
   de otros espacios. Conservar las revisiones anteriores; no reetiquetar ni
   combinarlas como muestras nuevas. La consolidación de anotaciones de varios
   espacios requerirá un paso posterior explícito con resolución de conflictos.

No cambiar la taxonomía existente durante una revisión: cualquier ampliación
requiere nueva versión y criterios de anotación acordados.

## Pruebas

```powershell
.\venv\Scripts\python.exe -B -m unittest ml.calidad_botellas.test_label_dataset -v
```

Los guardados de prueba y sus etiquetas ficticias se realizan exclusivamente
sobre copias temporales de imágenes; nunca sobre las 19 muestras originales.
También se ejecuta la suite previa en memoria y temporales, sin migraciones.

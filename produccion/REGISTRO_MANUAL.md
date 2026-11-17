# Registro manual de cajas y bolsas

## Implementación

La pantalla `/produccion/nuevo/` selecciona el procedimiento según el tipo real del
producto del lote. El servidor vuelve a validarlo, independientemente del navegador.

- BOTELLA: exige video y mantiene el conteo YOLO11n/ByteTrack, su regla de cruces,
  la línea central y la conversión H.264 existentes.
- CAJA y BOLSA: solicitan cantidad entera positiva; no requieren video ni ejecutan IA.
  Admiten entre 1 y 10.000 unidades por registro para limitar la creación y edición
  de inspecciones en una petición. No se admiten cero, negativos ni decimales.

El registro manual crea un análisis COMPLETADO, con origen MANUAL, y unidades 1..N
en REVISION, sin criterio ni confianza de IA. COMPLETADO indica que el registro de
producción terminó; el lote permanece EN_PROCESO mientras haya revisiones pendientes.
Se reutilizan la clasificación y validación del CU-10 y `actualizar_lote`.

Las operaciones se realizan en una transacción. Una clave UUID única identifica
la solicitud manual: reenviarla devuelve el análisis ya creado sin duplicar sus
unidades ni alterar clasificaciones. Cambiar lote o cantidad con esa misma clave
se rechaza. Para una medición nueva se debe abrir otro formulario. El análisis
completado más reciente sigue siendo el vigente; los anteriores no se acumulan.

El origen se muestra en el resultado, historial de análisis, detalle y panel de
lotes, y en la columna «Origen unidades» del CSV. Los gráficos y porcentajes usan
las mismas reglas de CU-11 tanto para IA como para registros manuales.

## Migración necesaria

`0006_analisisproduccion_origen_and_more`:

1. Añade `AnalisisProduccion.origen`, inicialmente IA para los análisis anteriores.
2. Añade `solicitud_manual`, UUID único y opcional; los registros anteriores quedan
   con NULL y no se asignan claves compartidas por defecto.
3. Permite dejar vacío `video_original`; el formulario sigue exigiéndolo para botellas.

No modifica migraciones aplicadas, archivos multimedia, cantidades ni clasificaciones.
La migración se valida en la base de pruebas y queda pendiente en la base real.
Antes de aplicarla, respaldar SQLite y `media`, siguiendo el procedimiento ya usado.

```powershell
.\venv\Scripts\python.exe manage.py migrate --plan
# Aplicar solamente después de revisar y autorizar 0006:
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test --verbosity 1
.\venv\Scripts\python.exe manage.py runserver
```

## Demostración manual

1. En `/admin/`, registrar productos de tipo CAJA y BOLSA y sus respectivos lotes.
2. Configurar criterios activos para cada producto, por ejemplo:
   - Botellas: Sin daños superficiales, Sin deformaciones.
   - Cajas: Sin roturas, Sin deformaciones.
   - Bolsas: Sin perforaciones, Sin rasgaduras.
   Los criterios se configuran desde el administrador; no se insertan datos reales
   ni catálogos obligatorios durante las pruebas o la migración.
3. En «Nuevo análisis», elegir un lote de cajas. Aparece cantidad y se oculta video.
   Registrar 10. Comprobar origen manual y diez unidades pendientes.
4. Clasificar una unidad conforme, otra defectuosa con criterio activo del producto
   y dejar las restantes pendientes. El lote muestra 10 producidas, 1 conforme,
   1 defectuosa y 8 pendientes: conformidad y defectos son 10 % cada uno.
5. Terminar las clasificaciones: el lote pasa a FINALIZADO. Devolver una unidad a
   REVISION vuelve a dejarlo EN_PROCESO.
6. Repetir para un lote de bolsas, sin cargar video.
7. Consultar `/produccion/resultados/`, filtrar por tipo y descargar CSV. Verificar
   el origen manual y que las mediciones históricas no se sumen a las actuales.
8. Para botellas, seleccionar su lote, cargar `pruebas_ia/produccion.mp4` y ejecutar
   el análisis habitual. La referencia sigue siendo ocho botellas en 434 fotogramas.

## Pruebas

`test_registro_manual.py` cubre ambos tipos, generación individual, estados,
criterios, porcentajes, historial, reenvíos, ausencia de IA, transacciones y CSRF.
La prueba existente con video real verifica el conteo, H.264, reproducción por
decodificación, conservación de clasificaciones y ausencia de duplicados.
La inspección visual de los formularios dinámicos y del reproductor corresponde
a la demostración en el navegador.

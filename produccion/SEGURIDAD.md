# Autorización y videos de producción

Se reutilizan usuarios, grupos y permisos estándar de Django. En la base revisada
ya existen los grupos `Administrador` y `Supervisor`, sin permisos asignados.
El nombre del grupo y `is_staff` no conceden autorización sobre las operaciones.
No se crean grupos ni se asignan permisos automáticamente.

| Operación | Permiso requerido |
| --- | --- |
| Registrar producción manual o subir video | `produccion.add_analisisproduccion` |
| Procesar o reprocesar video | `produccion.change_analisisproduccion` |
| Clasificar calidad (CU-10) | `produccion.change_inspeccioncalidad` |
| Gestionar lotes en Django admin | `produccion.view_loteproduccion`, `add_loteproduccion`, `change_loteproduccion`, según la tarea |

El administrador puede asignar los tres primeros permisos al grupo Supervisor
existente y agregar los usuarios autorizados. Para gestionar lotes desde el admin
también se necesita `is_staff` y permisos de consulta de los productos asociados.
No conceder eliminación salvo necesidad explícita. Los superusuarios activos
conservan acceso completo; los usuarios autenticados sin permiso reciben HTTP 403.
Las consultas CU-11 mantienen su comportamiento actual.

## Videos

Solo `.mp4`, firma MP4 admitida, video H.264 o MPEG-4. No se confía en el MIME
declarado por el navegador. Límites: 100 MiB, 120 segundos, 1920x1080 píxeles
(también orientación vertical), 60 FPS y 7200 fotogramas. El archivo se copia
a un temporal acotado y FFmpeg comprueba metadatos y decodifica el video.
Se limitan protocolos a archivos locales/tuberías, hilos, asignaciones individuales
de memoria y tiempo (10 segundos de inspección, 30 de decodificación).
No constituye un antivirus ni un límite total de memoria de proceso.

La validación se ejecuta al cargar desde producción o admin y antes de procesar
archivos guardados. El cursor se restaura; no se transforma el video original,
no se altera YOLO11n/ByteTrack y no se borran archivos multimedia existentes.
El manejador de cargas corta archivos que excedan el límite durante su recepción;
el navegador puede mostrar un error de conexión en ese caso. Configurar además
un límite de cuerpo de petición en el servidor HTTP/proxy para proteger la entrada.
Para exposición a usuarios no confiables, ejecutar decodificación e IA con cuotas
de CPU/memoria del sistema operativo y limitar solicitudes simultáneas en el servidor.

## Despliegue y restricciones

Este cambio no requiere migraciones nuevas ni modifica registros. La migración
0006 preexistente continúa pendiente y debe revisarse/aplicarse por separado con
autorización y respaldo: el código actual requiere sus columnas para operar.
Los permisos deben asignarse explícitamente después por un administrador.

La configuración de secretos/DEBUG, el acceso privado a `/media/` y la coherencia
de edición directa de inspecciones en admin siguen siendo tareas separadas.

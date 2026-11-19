# Auditoría y recuperación de acceso del laboratorio

18/11/2026 · America/La_Paz. Se consultaron el proceso real, ambas bases en modo lectura y la configuración. La comprobación Chrome utilizó la cuenta existente del laboratorio, sin publicar contraseñas ni hashes de credenciales.

## Causa encontrada

El servidor del puerto 8010 utiliza una base distinta a la base seleccionada por defecto por manage.py. En el laboratorio no existen supervisor ni admin. Ambos sí existen en la base operativa. El laboratorio tiene la cuenta piloto, activa, staff, con contraseña utilizable y permisos de consulta de ambos módulos.

Cambiar una contraseña en la base operativa no cambia la cuenta del laboratorio. Además, no es posible restablecer supervisor en el laboratorio mediante changepassword: no hay tal usuario allí. El formulario del administrador Django requiere una cuenta activa y staff de su propia base; no comparte usuarios automáticamente con otra base.

## Proceso y configuración comprobados

- PID que atiende 127.0.0.1:8010: 18104 al inicio de esta auditoría.
- Ejecutado mediante el entorno venv de C:\Users\Usuario\sistema_epp.
- Línea real: `venv\Scripts\python.exe -B -m django runserver 127.0.0.1:8010 --noreload --settings=experimentos.pilotos.settings`.
- Proyecto: C:\Users\Usuario\sistema_epp.
- Configuración seleccionada explícitamente: `experimentos.pilotos.settings`.
- SQLite del servidor: `output/experimental_pilotos/laboratorio.sqlite3`.
- Configuración predeterminada de manage.py: `config.settings`; SQLite: `db.sqlite3`.
- No se encontró DJANGO_SETTINGS_MODULE definido en la consola de auditoría. No se puede reconstruir el entorno histórico de la consola donde se ejecutaron los cambios previos. El argumento --settings del servidor determina su selección, independientemente del valor heredado de esa variable.

No se dispone del historial de comandos ni de la configuración efectiva de la consola original del usuario. Por ello no se afirma haber observado directamente qué base modificó cada comando anterior. Sí se demuestra la separación de bases, el valor predeterminado de manage.py y la ausencia de esos usuarios en laboratorio. Ejecutar los comandos indicados sin override selecciona la base operativa.

## Cuentas y sistema de autenticación

| Base | Usuario | Activo | Staff | Superusuario |
|---|---|---|---|---|
| Laboratorio | piloto | Sí | Sí | No |
| Laboratorio | supervisor | No existe | No aplica | No aplica |
| Laboratorio | admin | No existe | No aplica | No aplica |
| Operativa, solo consultada | supervisor | Sí | Sí | No |
| Operativa, solo consultada | admin | Sí | Sí | Sí |

Backend: `django.contrib.auth.backends.ModelBackend`. Ruta `/admin/login/` del administrador estándar. Middleware de sesión, autenticación y CSRF de Django, más navegación exclusiva del laboratorio; no se encontró un backend personalizado.

Sesiones en la base del laboratorio, cookie `epp_lab_session` y CSRF `epp_lab_csrf`. Son distintas de las cookies operativas predeterminadas. La contraseña local de piloto fue comprobada mediante authenticate sin imprimirse y funcionó. No hubo motivo para restablecerla.

## Recuperación aplicada y límite respecto de supervisor

Se identificó y probó el acceso correcto mediante piloto, la cuenta ya existente de laboratorio y la credencial guardada en `output/experimental_pilotos/acceso_local.json`. Abrir http://127.0.0.1:8010/ y utilizar esa cuenta; el formulario de Administración es la entrada de autenticación esperada.

No se crearon cuentas duplicadas, copiaron hashes operativos, modificaron permisos ni cambiaron contraseñas. Se solicitó elegir entre utilizar piloto y necesitar una cuenta independiente supervisor en laboratorio. Esa segunda opción no se ejecuta sin resolver la restricción de no crear usuarios duplicados. No se declara autenticación exitosa de supervisor: ese usuario no existe en esta base.

Para una futura recuperación interactiva de la cuenta EXISTENTE del laboratorio, únicamente si fuera necesaria:

```powershell
.\venv\Scripts\python.exe -B manage.py changepassword piloto --settings=experimentos.pilotos.settings
```

Ese comando no se ejecutó durante la auditoría, porque la credencial actual funciona. La contraseña se introduciría mediante el prompt interactivo, nunca en argumentos, informes ni mensajes. No usar un changepassword sin settings explícitos para recuperar el laboratorio.

## Pruebas reales completadas

Chrome real, en un contexto de navegación aislado, sin limpiar cookies o sesiones de otros usuarios:

1. Formulario estándar disponible y token CSRF presente.
2. Inicio de sesión con piloto: redirección exitosa a `/admin/`, sin mensaje de rechazo.
3. Navegación autenticada a inicio, EPP, Calidad, historial y de regreso al administrador: sesión conservada.
4. Solicitud POST de prueba sin token CSRF: 403, comportamiento esperado. La sesión continúa funcionando después de esa prueba.
5. Autenticación Django directa de piloto: exitosa; permisos EPP y Calidad presentes.

No hay evidencia de que cookies, middleware o CSRF causen el rechazo descrito. No se cambiaron sus configuraciones.

El proceso existente fue iniciado fuera de esta auditoría y no se dispone de un archivo histórico de su consola. No se inventa una revisión de logs de los intentos previos. La prueba nueva registró desde Chrome redirección exitosa, ausencia de error de formulario y 403 únicamente en la petición deliberadamente sin CSRF; no prueba qué contraseña se escribió en intentos anteriores.

Evidencia reproducible: `output/auditoria_acceso_v002/verificacion_chrome.json`.

## Integridad y archivos

Solo se añadió este informe y los registros de auditoría bajo `output/auditoria_acceso_v002/`. Ningún código, configuración o credencial fue modificado.

La base operativa conserva su contenido respecto de la captura realizada al iniciar esta auditoría. Ya difería del manifiesto de la entrega anterior al empezar; no se revirtió ni se atribuye esa diferencia a una causa no comprobada. Los otros 816 archivos protegidos coinciden con aquel manifiesto, incluidos modelos, evaluaciones y datos originales.

La prueba de login actualiza normalmente last_login de piloto y crea su propia sesión en la base de laboratorio. No se alteraron otros usuarios ni se eliminaron sesiones ajenas. No hubo flush, migrate, eliminación/recreación de SQLite, entrenamiento ni inferencia.

Detalle de conservación: `output/auditoria_acceso_v002/verificacion_integridad.json`.

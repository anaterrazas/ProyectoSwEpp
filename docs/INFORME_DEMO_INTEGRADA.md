# Demostración integrada · implementación y pruebas

18/11/2026 · America/La_Paz. Entrega limitada a presentación, navegación y acceso de lectura a artefactos. No se entrenó, descargó modelos ni ejecutó inferencia.

## Implementación

Entrada: http://127.0.0.1:8010/. Portal profesional con navegación lateral en escritorio, navegación adaptable en móvil, tarjetas por módulo, reproductores con controles y nombres accesibles, métricas, galerías y documentación. Diseño local sin dependencias CSS/JS externas nuevas.

Rutas añadidas:

| Ruta | Uso |
|---|---|
| `/` | Página principal y documentación |
| `/demo/epp/` | Originales, comparación base/candidata, métricas, evidencia y enlaces al monitoreo existente |
| `/demo/calidad/` | Capacidades disponibles/pendientes, fuentes, simulación, capturas, ENVASE y trazabilidad |
| `/demo/historial/` | Consulta de ejecuciones/paquetes y sección independiente de revisiones humanas |
| `/artefactos/<ruta de catálogo>` | Lectura autenticada de galerías, informes y medios aprobados |

Se conservan `/monitoreo/`, su revisión de reportes y `/calidad/` como visor heredado. Un middleware exclusivo del laboratorio añade navegación de retorno sin editar las vistas o plantillas de esos módulos. La página principal sustituye solo la redirección inicial del laboratorio.

Los resultados se consultan desde archivos existentes. El historial muestra seis paquetes/manifiestos, algunos con varias configuraciones, sin contabilizarlos como muestras independientes. Las decisiones humanas se leen de los reportes del laboratorio; no se crean registros ni se copian datos operativos. Las anotaciones de evaluación se identifican aparte y no se presentan como revisiones de alertas.

La selección de videos es de fuentes existentes, mediante reproductores de referencia; no se añadió subida de archivos ni una nueva ejecución de IA. El botón de análisis del monitoreo heredado permanece como funcionalidad previa; no se utilizó en esta entrega ni forma parte del guion.

## Acceso y protección de archivos

La autenticación reutiliza Django. EPP requiere `seguridad.view_deteccionepp`; el portal y artefactos de Calidad requieren `produccion.view_analisisproduccion`. Las cuentas con solo Calidad no acceden a artefactos EPP. Se asignó permiso de consulta de Calidad únicamente al usuario local de demostración, en SQLite de laboratorio; el inicializador conserva esa asignación para futuras preparaciones.

Los medios heredados conservan acceso EPP por compatibilidad; una cuenta de Calidad puede leer únicamente las fuentes de Calidad de ese servicio. El visor heredado `/calidad/` conserva su permiso histórico EPP; la entrada recomendada de Calidad es `/demo/calidad/`, con permisos propios.

El nuevo catálogo permite seis directorios específicos de evaluaciones/simulación y cinco documentos concretos. No permite todo output, datasets ni el proyecto. Rechaza rutas absolutas, traversal, rutas Windows, destinos fuera de la raíz aprobada, extensiones ajenas y manifiestos internos de protección. Las rutas resueltas se comprueban también para impedir escapes por enlaces/junctions. No se publican credenciales, SQLite, pesos ni código.

Los MP4 e imágenes reutilizan la respuesta de medios existente, incluyendo MIME, Range/206 y búsqueda temporal. Informes JSON/JSONL/CSV/Markdown se presentan como texto escapado y con rutas absolutas locales ocultas; los originales no se modifican. Es una vista de consulta, no una API JSON nueva ni una exportación que sustituya al archivo original.

Las galerías reciben navegación y CSS adaptable solo en la respuesta HTTP. CSP bloquea scripts salvo el hash del filtro original conocido de auditoría; permite la sesión necesaria para cargar imágenes protegidas. No se permite enviar formularios desde las galerías. Se desactivó DEBUG solo en settings experimentales para no mostrar trazas/rutas en errores; los estáticos de acceso se sirven por el buscador de Django en este laboratorio local.

## Arquitectura preparada para continuar Calidad

`catalogo.py` separa capacidades, estado, permisos y manifiestos de cada módulo. El inicio recorre ese catálogo: para incorporar capacidades posteriores de Calidad no necesita cambiar su plantilla ni modificar EPP. `portal.py` mantiene las lecturas y enlaces del panel Calidad separados de los de EPP; los motores actuales no se importan ni se invocan desde el portal. El servicio de artefactos es común y usa raíces con propietario de módulo.

El catálogo es de presentación: añadir una etiqueta no implementa un detector. Una futura integración de TAPA, RAYADURA, DEFORMACION o asociación deberá aportar su ejecución y evidencia reales, registrar resultados versionados y actualizar los recursos/capacidades de Calidad. No hay descubrimiento arbitrario de nuevos directorios ni activación automática de pesos. El diseño no bloquea ese trabajo ni lo declara terminado.

## Verificación

38 pruebas aprobadas con base de pruebas independiente; Django sin incidencias. Incluyen autenticación, GET/HEAD y rechazo de escrituras, permisos separados, métricas por módulo, medios y rangos inválidos, traversal y destinos resueltos fuera de raíz, errores sin rutas, estáticos de login, escape de observaciones, historial sin escritura y retorno desde pantallas previas. También regresiones de evaluación, referencias EPP, asociación, incertidumbre y persistencia. No se usó SQLite operativo para pruebas.

Revisión de 1.088 enlaces locales de galerías: destinos existentes y admitidos por el catálogo, cero errores de resolución.

Chrome real, escritorio 1440 × 1000 y viewport móvil 390 × 844:

- Seis páginas recorridas: inicio, EPP, Calidad, historial, monitoreo y visor heredado; sin expresiones Django sin renderizar.
- Diez videos reproducidos con duración positiva y avance temporal: dos comparativos EPP, dos originales EPP, simulación Calidad y cinco originales Calidad. Esto verifica reproducción, no nueva inferencia ni validación industrial.
- Cuatro galerías: 132 + 99 + 251 + 50 = 532 imágenes cargadas, sin imágenes rotas. Filtro de CASCO: 20 casos visibles de la auditoría.
- Inicio, EPP, Calidad e historial a 390 px: ancho de contenido 390 px, sin desbordamiento horizontal de página; las tablas permiten desplazamiento interno.
- Evidencia: `output/demo_integrada_v002/verificacion_chrome.json` y capturas PNG de escritorio/móvil.

La primera comprobación detectó que el aislamiento de origen impedía enviar cookies a las imágenes. Se corrigió la política CSP, manteniendo scripts limitados al hash del filtro conocido. La segunda comprobación completa aprobó. El registro inicial se conserva como `verificacion_chrome_inicial.json` para trazabilidad.

La comprobación final de integridad y el registro de hashes de archivos cambiados se guardan en `output/demo_integrada_v002/verificacion_integridad.json` y `archivos_modificados.json`. El manifiesto previo cubre 817 archivos protegidos: no se permite cambiar ninguno para esta entrega. Solo se autorizaron código/documentación del laboratorio y la cuenta/sesión local en su propia base.

## Archivos de esta entrega

Modificados:

- `experimentos/pilotos/media.py`: extraer la respuesta de medios reutilizable y permitir consulta de fuentes Calidad con su permiso.
- `experimentos/pilotos/settings.py`: plantillas/middleware exclusivos del portal y errores sin DEBUG.
- `experimentos/pilotos/urls.py`: inicio, paneles, historial, artefactos y estáticos locales.
- `scripts/laboratorio_pilotos.py`: permiso de consulta Calidad para la cuenta de laboratorio.

Añadidos:

- `experimentos/pilotos/catalogo.py`, `portal.py`, `artefactos.py`, `navegacion.py`, `test_portal.py`.
- `experimentos/pilotos/templates/demo/`: `base.html`, `estilos.html`, `inicio.html`, `modulo.html`, `historial.html`.
- `scripts/verificar_demo_integrada.mjs`.
- `docs/GUION_DEMO_INTEGRADA.md` y este informe.
- `output/demo_integrada_v002/`: manifiestos de verificación, capturas y registro del navegador. El perfil local de Chrome usado para pruebas puede contener sesiones y no debe publicarse.

Los cambios previos que ya aparecen en git status no se atribuyen a esta entrega ni se revierten. No se editaron módulos operativos, evaluaciones, videos, anotaciones, pesos ni SQLite operativo.

## Limitaciones que permanecen visibles

EPP: candidata CHALECO 0,15 experimental; recall 58,11 % y 31 FN en referencias conocidas; cobertura de asociación limitada; pérdidas de ID; sin validación temporal de infracciones ni falsas alarmas/minuto; revisión independiente pendiente.

Calidad: detección ENVASE provisional por siete conflictos semánticos; TAPA sin detector evaluado; asociación tapa-envase pendiente; defectos NO EVALUABLE en simulación; RAYADURA/DEFORMACION NO DISPONIBLE. No hay demostración validada de tapa correcta, ausente o mal colocada, ni rechazo automático, ni cobertura validada de cajas u otros perfiles.

Este portal es una demostración local con resultados históricos, no una plataforma desplegada de cámaras en vivo, un planificador de inferencia ni una validación industrial. El guion mantiene esas diferencias explícitas.

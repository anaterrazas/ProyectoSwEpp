# Corrección y laboratorio aislado — 17/11/2026

## Causa y corrección

El síntoma de etiquetas Django visibles se reproduce al abrir directamente
`monitoreo/templates/monitoreo/piloto.html`: el navegador recibe la plantilla fuente,
sin ejecutar `render()`, construir contexto ni generar CSRF. En ese modo las rutas
con variables también quedan literales y los medios no se encuentran. No había
un servidor experimental preparado como entrada de uso. La ruta Django existente
sí renderizaba etiquetas en las pruebas; no se encontró un error de sintaxis del
motor de plantillas. No se dispone de la URL original del fallo del usuario para
afirmar qué previsualizador concreto lo sirvió.

Se añadió un aviso al abrir las plantillas directamente y un enlace a la aplicación
real. La revisión ahora incluye original y resultado, comprueba existencia de
evidencias/resultados y evita etiquetas de imagen o video con archivos ausentes.
Conserva revisión, historial, permisos y CSRF, con una acción POST explícita.
La cobertura se calcula sobre observaciones equipo/persona, nunca personas únicas.

El laboratorio sirve medios autenticados, con MIME correcto y peticiones Range
(206) para reproducción y búsqueda. Los originales se resuelven mediante alias
de lectura; no se copian ni se sobrescriben. Los resultados y revisiones viven en
`output/experimental_pilotos/media/` y la base es
`output/experimental_pilotos/laboratorio.sqlite3`.

## Uso

Archivos de esta entrega:

- `monitoreo/piloto.py`: contexto de revisión, disponibilidad de medios y cobertura.
- `monitoreo/templates/monitoreo/piloto.html` y `camaras.html`: entrada por Django,
  original/resultado, evidencias, decisiones e historial.
- `monitoreo/templates/monitoreo/calidad_laboratorio.html`: reproducción de calidad.
- `experimentos/pilotos/`: configuración aislada, rutas, medios con Range,
  almacenamiento de lectura, panel, preparación/comparación, ejecutores y pruebas.
- `scripts/laboratorio_pilotos.py`: inicialización y servidor de laboratorio.
- `scripts/verificar_navegador_pilotos.mjs`: prueba de navegador local.
- `.gitignore`: excluye SQLite, acceso local y perfil del navegador experimentales.

No se modificaron módulos de producción, configuración operativa, modelos ni
migraciones en esta entrega. No se ejecutaron migraciones contra SQLite operativo.

```powershell
.\venv\Scripts\python.exe -B scripts/laboratorio_pilotos.py --init
.\venv\Scripts\python.exe -B scripts/laboratorio_pilotos.py --serve
```

Abrir **http://127.0.0.1:8010/monitoreo/**, no el archivo HTML ni Live Server.
El usuario de laboratorio y su clave generada están en
`output/experimental_pilotos/acceso_local.json`. No se reutilizan cuentas ni
sesiones operativas. `--init` es repetible: no sobrescribe reportes/revisiones
copiados ni cambia la clave de una cuenta existente. Calidad se abre en `/calidad/`.

EPP puede ejecutar los dos videos desde la interfaz: las detecciones, los reportes
y las revisiones se escriben solo en el laboratorio. El video largo se usa una vez;
`trabajador_prueba.mp4` no se incorpora como otra muestra independiente.

Para ejecutar opcionalmente un video de calidad, en una salida nueva:

```powershell
.\venv\Scripts\python.exe -B -m experimentos.pilotos.ejecutar_calidad --video prueba2.mp4 --salida output/experimental_pilotos/resultados/calidad_prueba2_v001
```

Este baseline localiza únicamente ENVASE con YOLO11s preentrenado y registra
observaciones y seguimiento por frame, evidencia y video H.264. El detector de
TAPA y los defectos no están habilitados en ese baseline. Las tapas requieren
un detector específico validado; no se sustituyen por una ROI geométrica.
No se ejecutó este comando ni se entrenó ningún modelo en esta entrega.

## Preparación de la comparación

Se congelaron las 25 últimas revisiones humanas y sus hashes en
`output/experimental_pilotos/evaluacion_25/referencias.json`, con procedencia en
`plan.json`. No se alteró ninguna revisión original. Se conservaron también las
regiones no evaluables del frame 405 de prueba2: el export YOLO contiene solo 24
frames porque excluye ese frame, pero la evaluación JSON puede tratarlo mediante
regiones ignoradas. «Reviewed» refleja anotación exhaustiva del autor y no acredita
una segunda revisión independiente de calidad.

Inferencia opcional de localización sobre esos frames:

```powershell
.\venv\Scripts\python.exe -B -m experimentos.pilotos.detectar_calidad --referencias output/experimental_pilotos/evaluacion_25/referencias.json --salida output/experimental_pilotos/evaluacion_25/predicciones_v001.json
.\venv\Scripts\python.exe -B -m experimentos.pilotos.evaluacion comparar --referencias output/experimental_pilotos/evaluacion_25/referencias.json --predicciones output/experimental_pilotos/evaluacion_25/predicciones_v001.json --salida output/experimental_pilotos/evaluacion_25/comparacion_v001.json
```

El comparador exige hash de imagen coincidente y referencia exhaustiva. Empareja
una detección por caja de la misma clase, en orden de score, con IoU >=0,5.
Duplicados cuentan como FP; cajas evaluables sin detección, como FN. Detecciones
en regiones ignoradas se documentan aparte. Un frame no ejecutado no se transforma
en una omisión. Las clases no ejecutadas tienen métricas null, nunca ceros fingidos.
La falta de predicciones o positivos deja los cocientes correspondientes en null.

Las cuatro evaluaciones permanecen separadas:

| Evaluación | Preparación / límite |
|---|---|
| Personas y casco/chaleco | Ejecución EPP aislada disponible; falta referencia humana temporal |
| ENVASE/TAPA | Referencia JSON conservada, comparador probado; baseline disponible solo para ENVASE |
| Defectos de tapa | Sin referencia estructurada por unidad, etapa y colocación; métricas no disponibles |
| Seguimiento | Se registran IDs temporales; faltan trayectorias humanas para medir cambios y pérdidas de ID |

RAYADURA y DEFORMACION permanecen **NO DISPONIBLE**. No se generaron métricas
de IA nuevas, ni predicciones inventadas, ni anotaciones de defectos derivadas de
las cajas de ENVASE/TAPA.

## Verificación realizada

- 21 pruebas automatizadas aprobadas con SQLite en memoria y medios temporales.
  Incluyen contexto, plantillas renderizadas, evidencia JPEG, medios ausentes,
  formulario, CSRF real, permisos, historial y revisión concurrente/desactualizada,
  Range, protección de fuentes y casos matemáticos del comparador.
- Chrome headless reprodujo los siete videos fuente y el resultado EPP existente:
  metadatos cargados, readyState=4, duración positiva y avance de reproducción.
  Se comprobó el listado, el reporte y la pantalla experimental de calidad.
- El reporte real conserva cero candidatos. No se inventaron eventos para mostrar
  fotografías. Evidencia y decisiones se verificaron con fixtures técnicos en
  pruebas, separados de datos/predicciones de IA.
- Cobertura del reporte existente: 191/524 observaciones evaluables, **36,45 %**.
  No es precisión de detección ni porcentaje de trabajadores que cumplen.
- Evidencia de navegador: `output/playwright/monitoreo_navegador.json` y
  `output/playwright/monitoreo_corregido.png`.
- Playwright CLI no estaba disponible localmente; se usó Chrome/CDP sin instalar
  dependencias. El navegador requirió ejecución fuera del sandbox por bloqueo de IPC.

Las duraciones HTML pueden diferir ligeramente de frame/FPS por los timestamps
del contenedor. La comprobación de reproducción avanzó un segmento de cada video;
no sustituye la decodificación completa ya realizada en el inventario anterior.

## Pendientes

Anotar EPP presente/ausente/ocluido y episodios temporales; confirmar tapa obligatoria
y etapa posterior al tapado; completar etiquetas estructuradas de colocación y
asociación tapa–envase; revisar exhaustividad de cajas y ampliar referencia temporal.
Solo después ejecutar las comparaciones habilitadas y documentar sus límites.
No hay test industrial independiente ni detector de tapa validado en este baseline.

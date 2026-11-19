# Guion de demostración · Sistema de Inspección IA

18/11/2026 · America/La_Paz. Duración sugerida: 8–10 minutos. Solo resultados previamente calculados; no entrenar ni pulsar «Analizar video con IA» en el monitoreo heredado.

## Acceso y preparación

Abrir http://127.0.0.1:8010/ con la cuenta local del laboratorio. Sus datos están en `output/experimental_pilotos/acceso_local.json`; no compartir ese archivo ni mostrar la contraseña durante la presentación. La página raíz es la entrada común; las plantillas no se abren desde el explorador de archivos o Live Server.

Si el servidor no está iniciado:

```powershell
.\venv\Scripts\python.exe -B scripts/laboratorio_pilotos.py --serve
```

El laboratorio existente ya está preparado. Para instalarlo en otra copia se utiliza `--init` antes de `--serve`, siempre con los settings experimentales; no es necesario repetirlo para esta presentación. Inicializa únicamente SQLite y medios del laboratorio, nunca la base operativa. La cuenta local tiene consulta de EPP y Calidad.

## 1. Vista general · 1 minuto

Mostrar las tarjetas Seguridad EPP y Control de Calidad. Explicar que son dos motores independientes bajo una navegación común. EPP es un piloto supervisado; Calidad continúa en desarrollo. Los estados pendientes son parte del resultado, no errores que se oculten.

## 2. Seguridad EPP · 3 minutos

1. Entrar en Seguridad EPP. Identificar explícitamente CHALECO 0,15 como candidata experimental, frente a la base 0,30.
2. Reproducir ambos videos comparativos: base a la izquierda y candidata a la derecha. Los originales se abren en «Videos de referencia». Las cajas e IDs provienen de inferencias existentes.
3. Mostrar la tabla de las 33 referencias del procesamiento continuo: F1 CHALECO 57,14 % → 72,88 %, con 31 omisiones restantes. No son métricas sobre los 374 fotogramas completos sin anotar.
4. Abrir la galería comparativa y después la auditoría. Mostrar TP/FP/FN y el filtro de CASCO/CHALECO/PERSONA. Regresar al portal mediante el enlace superior.
5. Señalar que la cadena chaleco-persona pasa de 20/74 a 31/74 enlaces correctos. Mostrar los registros temporales para explicar pérdidas de IDs y que el seguimiento se reutilizó idéntico en ambas configuraciones.
6. Abrir «Monitoreo existente» para enseñar el recorrido de reportes y reproducción. Utilizar la navegación superior para volver. No generar inferencias nuevas. Si no hay candidatos, no simularlos como alertas reales; el historial vacío es correcto.

Frase de alcance: «Es una mejora exploratoria en videos conocidos. No demuestra cumplimiento, validación independiente ni tasa de falsas alarmas».

## 3. Control de Calidad · 3 minutos

1. Abrir Calidad desde el menú. Mostrar ENVASE disponible experimentalmente y TAPA sin detector evaluado. RAYADURA y DEFORMACION permanecen NO DISPONIBLE; asociación tapa-envase pendiente.
2. Reproducir la simulación existente. Mostrar seguimiento, evidencia y sus tres capturas. El resultado es NO EVALUABLE: hubo 399 fotogramas, 1.087 observaciones, 39 IDs temporales y cero llamadas al clasificador. No son 39 envases únicos ni defectos confirmados.
3. Abrir un original en «Videos de referencia»; no se sube ni se sobrescribe archivo alguno.
4. Abrir la galería de 25 referencias y la trazabilidad. Precisión ENVASE 71,74 % y recall 92,52 % son concordancia mecánica provisional, no aceptación: existen siete conflictos entre clase y nota humana.
5. Señalar que una región geométrica del cuello no es una tapa detectada y que el nombre botellasSinTapa no demuestra defecto posterior al tapado.

Frase de alcance: «Esta plataforma permite continuar Calidad. Aún no demuestra tapa correcta, ausente o mal colocada; no ejecuta rechazo automático».

## 4. Historial y cierre · 1–2 minutos

Mostrar ejecuciones/paquetes y consultar sus manifiestos. Algunos agrupan configuraciones: seis entradas de consulta no significan seis muestras independientes. Abrir la sección separada de decisiones humanas; si no tiene registros, explicar que no se fabrican. Las anotaciones de referencia son otra fuente y la segunda revisión independiente sigue pendiente.

Finalizar en Documentación. Resumir la próxima decisión: completar capacidades de Calidad y mejorar la cobertura/asociación EPP, conservando sus motores y métricas separados. No comprometer entrenamiento ni despliegue industrial como parte de esta entrega.

## Comprobación previa a presentar

- Inicio, módulos, historial y documentación accesibles tras autenticación.
- Videos originales y procesados reproducibles, sin activar análisis nuevos.
- Galerías cargadas; etiquetas experimental/pendiente/NO EVALUABLE visibles.
- No mostrar credenciales ni usar cuentas de producción.
- Mantener accesibles los informes y explicar los límites de referencia y generalización.

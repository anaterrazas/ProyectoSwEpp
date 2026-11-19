# Prototipo experimental EPP — ensayo 1

Se preparó un ensayo reproducible de **TAPA_DEFECTUOSA** y una demostración local para fotografías y MP4. **No es un sistema de rechazo industrial ni un detector multiclase completo.** Rayadura y deformación aparecen explícitamente sin modelo porque faltan negativos humanos válidos. Las imágenes y decisiones originales permanecen intactas.

## Abrir la demostración

Desde `C:\Users\Usuario\sistema_epp`:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/day1_v001/demo.py serve --port 8790
```

Abrir `http://127.0.0.1:8790`. Si ya está ejecutándose en ese puerto, usar la instancia existente. La aplicación solo escucha en localhost.

1. Cargar una fotografía JPEG/PNG o MP4 real. El MP4 debe cumplir los límites existentes: 100 MiB, Full HD, 60 FPS, 120 s, 7200 fotogramas y H.264/MPEG-4.
2. Seleccionar con el ratón una ROI fija o confirmar explícitamente escena completa. No se detectan ni siguen envases automáticamente.
3. Pulsar Procesar archivo. La demo ejecuta el modelo experimental de tapa, muestra score y predicción, y mantiene RAYADURA/DEFORMACION sin predicción. El score sigmoid no es una confianza calibrada.
4. Descargar el JSON de trazabilidad. Cada fotograma tiene índice, PTS, tiempo relativo y estado de cada clase. Un resultado 0 no acredita conformidad global ni ausencia de defectos de otras clases.

Las cargas y resultados se guardan solo en `runs/`; no se agregan al entrenamiento ni crean muestras oficiales, sesiones o botellas. La selección de una ROI no acredita que contenga exactamente un envase o su tapa; el operador debe comprobarlo. El modelo se entrenó con escenas cercanas de tapas sobre fondo oscuro: otras vistas y la línea EPP son dominio no validado.

## Procesamiento por PowerShell sin navegador

El siguiente comando ya se ejecutó con el MP4 real de referencia; usar otra salida nueva para repetirlo:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/day1_v001/demo.py process `
  --input media/produccion/videos/produccion.mp4 `
  --output datasets/calidad_botellas/v002/experiments/day1_v001/runs/mi_demostracion_v001 `
  --whole-frame
```

Para una región real elegida por el usuario, usar `--roi x y ancho alto` en lugar de `--whole-frame`, reemplazando esos cuatro valores por enteros medidos en la imagen original. No usar coordenadas inventadas como si fueran una localización automática. Las salidas requieren nombre nuevo y se restringen a `day1_v001/runs/`.

Resultados de referencia ya disponibles: `runs/reference_demo/result.mp4`, `result.jpg` y `report.json`. Se procesaron **434 fotogramas** sin modificar el MP4 de entrada. El video visual se codifica a FPS nominal; los PTS originales, incluidos los variables, se conservan en el JSON. No se midió exactitud de calidad del video: no hay etiquetas temporales de referencia.

## Datos y modelo

- Dataset experimental: `dataset/manifest.jsonl`, 50 referencias a imágenes públicas originales sin copiar ni cambiar sus bytes, con SHA-256, licencia, atribución, clase conocida, evidencia humana, componente y partición.
- Plan previo al entrenamiento: `dataset/plan.json`; 18 train, 15 validation y 17 test, sin componentes compartidos. Las únicas etiquetas objetivo utilizadas son las decisiones humanas de tapa 0/1; RAYADURA y DEFORMACION permanecen null.
- Modelo: `artifacts/cap_model.pt`, TinyCapCNN desde cero en CPU, sin descargar pesos ni paquetes. Parámetros fijados antes del ajuste: semilla 20261116, 120 épocas, Adam 0,003, entrada 96×96, umbral 0,5. El test no se usó para elegir umbral, arquitectura ni checkpoint.
- Métricas: `artifacts/metrics.json`; resultados individuales: `artifacts/predictions.json`; curva de pérdida: `artifacts/training_history.json`.

| Test reservado por origen | Resultado |
|---|---:|
| Imágenes / grupos de origen | 17 / 1 |
| Positivas / negativas | 10 / 7 |
| TP / TN / FP / FN | 7 / 3 / 4 / 3 |
| Exactitud | 58,82 % |
| Precisión positiva | 63,64 % |
| Recall | 70,00 % |
| F1 | 66,67 % |
| Tasa de falsos negativos | 30,00 % |
| Exactitud del baseline mayoritario | 58,82 % |

**No superó al baseline en exactitud.** Entrenamiento perfecto frente a test débil indica sobreajuste/cambio de dominio; no se oculta ni se intenta arreglar ajustando sobre el test. Validación tiene 15 positivos y cero negativos: no permite calibrar especificidad ni el umbral. El test está separado del entrenamiento por grupo de origen, pero ya se había visto durante revisión humana histórica y no prueba independencia física de cada fotografía. No es un test industrial ciego ni demuestra generalización a todos los envases.

La cobertura solo justifica este ensayo mínimo de ejecución (ambas clases conocidas, grupos separados y licencias acreditadas), no preparación científica o industrial del dataset completo. Se conservó un único ajuste, incluso al observar sus errores.

## Auditoría y exclusiones

Consultar `INFORME_FINAL.md`, `inspection/source_audit.json`, `inspection/exclusions.json` y `inspection/additional_review.html`.

- Las 15 imágenes adicionales se inspeccionaron individualmente y quedan excluidas por licencia/procedencia desconocida; tres muestran Getty Images y otra una marca tenue aparente. Las botellas aplastadas no se etiquetan automáticamente como defecto de fabricación.
- Las 11 fotografías propias siguen en preimportación con cuatro envases físicos: BOT-001 incluye la antigua BOT-003. No se inventaron fecha, cámara, sesión o evaluabilidad para incorporarlas.
- Los 19 recortes anteriores se mantuvieron separados. Su última revisión marca NO_EVALUABLE global y no aporta positivos de defectos EPP. No se usaron para rellenar negativos ni como test completo.
- Las nueve decisiones parcialmente revisadas no se promovieron a nuevas etiquetas.

## Repetir comprobaciones

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/day1_v001/test_prototype.py
& .\venv\Scripts\python.exe -B -m unittest discover -s datasets/calidad_botellas/v002/tools -p 'test_*.py' -v
```

No volver a ejecutar `prepare.py` o `model.py train` sobre estas salidas: rechazan sobrescrituras. Para otro ensayo se necesita una versión experimental nueva y una política de evaluación que no convierta el test actual en datos de ajuste. La demo no reentrena.

El siguiente paso es reunir un test EPP realmente reservado por sesión/lote y negativos humanos por clase, resolver los metadatos de las fotos propias y ampliar los positivos/negativos de tapa en sesiones diferentes. Hasta entonces este prototipo solo demuestra auditoría, ajuste experimental, inferencia y trazabilidad.

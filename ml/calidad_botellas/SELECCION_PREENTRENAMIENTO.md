# Selección humana y particiones propuestas

Abrir con el navegador:
`datasets/publicos_calidad_botellas/selections/pretrain_v001/index.html`.
Son 100 imágenes, 50 por fuente, sin copiar ni modificar imágenes o anotaciones.
Los enlaces usan las miniaturas de auditoría y abren los originales en otra pestaña.

La propuesta procesa TODOS los grupos visuales y une transitivamente sus miembros
con hashes iguales, nombres de origen y fechas de captura inferidas de WIN_YYYYMMDD.
Los 202 componentes resultantes no se rompen entre particiones. Esto controla
fugas conocidas, no certifica que se haya identificado cada botella física.
Los grupos excesivamente grandes pueden contener objetos diferentes y requieren
revisión antes de relajar enlaces. No dividirlos automáticamente por conveniencia.

Las 945 imágenes con alguna región <16 px siguen disponibles. Se informa si tienen
otra región objetivo mayor, una región estrecha y alargada, solo regiones pequeñas,
problemas técnicos o clases sin equivalencia. El tamaño proyectado a entrada de
384 px es solo análisis de escenarios; no se transforman las imágenes.

Good Cap da candidatos a revisar la tapa, nunca conformidad global confirmada.
Las vistas completas técnicamente adecuadas dan candidatos de evaluabilidad
conjunta, nunca confirmación de que se puedan observar las tres familias de defectos.
Todas esas confirmaciones permanecen null. La galería no guarda anotaciones.

`split_proposal.jsonl` y `origin_components.jsonl` contienen NUEVAS propuestas;
los manifiestos originales conservan su split y etiquetas. Roboflow tiene solo
cuatro fechas y la partición propuesta de validación contiene tres positivos de
tapa: debe ampliarse antes de calibrar. Las 19 muestras EPP no se incluyen.

Para otra propuesta reproducible, elegir siempre salida nueva:

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.select_review `
  --output datasets/publicos_calidad_botellas/selections/pretrain_v002
```

Pruebas:

```powershell
.\venv\Scripts\python.exe -B -m unittest ml.calidad_botellas.test_select_review -v
```

No se ha autorizado ni ejecutado entrenamiento. Revisar etiquetas, identidad de
origen, visibilidad, cobertura y limitaciones antes de congelar una partición.

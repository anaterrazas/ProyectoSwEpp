# Auditoría visual de solo lectura

Abrir `datasets/publicos_calidad_botellas/audits/visual_v002/index.html` con doble
clic en el navegador. Es un HTML local autónomo: no necesita iniciar Django ni
instalar un servidor. Mantenerlo junto a sus miniaturas y archivos JS/CSS.

La galería ofrece ejemplos por categoría y estado positivo/negativo/desconocido,
con muestreo aleatorio reproducible estratificado por fuente. Un grupo vacío se
muestra como vacío: no se fabrican negativos ni etiquetas. Permite filtrar por
fuente y alerta técnica/semántica, regenerar la muestra y abrir grupos visuales.
Cada tarjeta conserva nombre original, clases fuente, etiquetas, autores,
licencia, procedencia y enlace de solo lectura a la imagen original. Las
miniaturas son derivados de visualización, nunca nuevos datos de entrenamiento.

El informe y las métricas incluyen las 8477 imágenes públicas y, separadas,
las 19 referencias EPP. Para EPP se leen las últimas anotaciones del espacio
existente; no se modifica ni se copia una decisión a otra imagen. No se atribuye
licencia pública a los recortes internos.

Alertas técnicas: decodificación, SHA-256, dimensiones declaradas, tamaño,
nitidez mediante varianza Laplaciana normalizada y exposición/fondo. No miden
visibilidad semántica de cuerpo/tapa ni garantizan resolución de una rayadura.
Un fondo oscuro o uniforme puede producir un aviso sin que la imagen sea inútil.

Semejanzas: búsqueda global BK-tree sobre pHash, verificación dHash y color.
Los grupos son candidatos de revisión, no duplicados certificados. Un grupo
puede conectar objetos distintos del mismo producto. No se fusionan etiquetas,
no se eliminan imágenes y no se sustituyen particiones de origen. Para comparar
pares, usar su ID de grupo en la galería; todos los índices constan en JSON.

Las incompatibilidades semánticas se señalan como riesgos: etiqueta de escena
frente a recorte individual, clases condicionales, abrasión/scuff frente a
rayadura y regiones anotadas de tamaño muy pequeño. No se decide automáticamente
que una etiqueta humana sea incorrecta.

Reproducir en una NUEVA carpeta:

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.audit_visual `
  --output datasets/publicos_calidad_botellas/audits/visual_v003
```

No sobrescribe una auditoría anterior. Para probar:

```powershell
.\venv\Scripts\python.exe -B -m unittest ml.calidad_botellas.test_audit_visual -v
```

Los fixtures artificiales de esas pruebas permanecen en temporales; no forman
parte de la galería real. No se ejecutan entrenamiento, migraciones ni escrituras
en SQLite. No se cambia YOLO11n, ByteTrack ni el conteo.

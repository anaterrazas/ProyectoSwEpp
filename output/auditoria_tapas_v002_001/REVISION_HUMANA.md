# Revisión humana de los siete conflictos

El anotador existente está disponible en **http://127.0.0.1:8792/** y usa exclusivamente:

`datasets/calidad_botellas/v002/experiments/detection_manual_v001/revision_tapa_fase21_001`

Es una copia de los 25 originales y todas sus revisiones, preservadas byte a byte. No está conectado al dataset original ni a SQLite. La herramienta escucha solo en localhost; el autor es declarado, no autenticación de identidad. No considera automáticamente independiente a un revisor.

Si necesita iniciarse de nuevo:

```powershell
.\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/detection_manual_v001/annotate.py serve --dataset datasets/calidad_botellas/v002/experiments/detection_manual_v001/revision_tapa_fase21_001 --port 8792
```

No inicie otro servidor sobre esa misma copia si ya está funcionando. No cambie el argumento al directorio `dataset` original.

## Procedimiento

1. Abra index.html de esta auditoría y el anotador en otra pestaña. Seleccione el sample_id del conflicto en el listado de fotogramas y localice la caja por box_id.
2. Introduzca el identificador real de quien revisa; no deje el autor anterior como si fuera una segunda revisión. Para independencia debe revisar otra persona, no otro nombre del mismo anotador.
3. Revise contexto original, clase, coordenadas y nota. Decida si la caja es ENVASE, TAPA o no evaluable. No decida solo por el texto «tapa». Verifique si ya hay otra caja del mismo objeto.
4. Si corrige clase o geometría, aplique cambios al objeto. No dibuje una tapa en una boca vacía. No asigne propietario si es suelta o desconocido. La condición colocada/suelta no equivale a tapa correcta/defectuosa.
5. Añada una observación explícita, por ejemplo «Adjudicación del conflicto [box_id]: decisión [...], motivo [...], condición de colocación conocida/desconocida [...]». Solo escriba lo que permita la evidencia; no prellenar decisiones automáticas. Mantenga atributos desconocidos como desconocidos o borrador.
6. Guarde una **nueva revisión**. El anotador conserva autor, fecha, secuencia, hash padre y rechaza versiones obsoletas. No edite directamente JSON anteriores.
7. Si marca reviewed/exhaustive, revise todos los objetos objetivo del fotograma, no solo la caja en conflicto. Un frame ilegible no es un negativo confirmado.

## Casos

- prueba2: frames 120, 240, 330; identificador de video comienza `vid_557eef7acddd10c7439ddd8f`.
- tapas: frames 100, 250, 300, 350; identificador de video comienza `vid_8a2b94bcf49a24212a443df0`.
- Los box_id completos y notas están en la galería y en procedencia_conflictos.json.

## Después de adjudicar

No se importan cambios de la copia al original automáticamente ni se sobreescriben evaluaciones. Primero revisar las nuevas versiones, conflictos restantes y coherencia de enlaces. Preparar después una instantánea nueva con hashes para una futura comparación. No entrenar ni exportar train/validation/test hasta resolver procedencia, sesiones y suficiencia.

No se ha guardado ninguna adjudicación durante esta auditoría. El conjunto revisado de entrenamiento aún no está aprobado.

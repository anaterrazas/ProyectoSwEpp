# Preparación de detector TAPA · Auditoría v002

18/11/2026 · America/La_Paz. No se entrenó ni ejecutó inferencia. Se revisaron los originales, las últimas revisiones, sus hashes, las 136 cajas TAPA y seis hojas de contacto. La inspección visual del agente es diagnóstico, no adjudicación humana independiente ni nuevas etiquetas.

## Dictamen

**Los datos sirven para adjudicación y desarrollo exploratorio, pero todavía no constituyen un conjunto confiable de entrenamiento, validación y prueba independientes.** No autorizar entrenamiento a partir de estas 25 imágenes sin resolver conflictos, procedencia y particiones. Los 136 registros son observaciones repetidas, no 136 tapas físicas distintas.

Los siete conflictos se muestran en `index.html`; cada caso incluye original sin modificar, caja superpuesta, clase registrada, coordenadas, ID y nota humana. `tapas.html` permite revisar individualmente las 136 cajas, contexto, recorte, enlace, atributos humanos y medidas. La copia de revisión está disponible con el anotador existente en http://127.0.0.1:8792/; instrucciones en `REVISION_HUMANA.md`.

## Distribución comprobada

| Fuente | Imágenes | Cajas TAPA | Con enlace humano | Sin enlace |
|---|---:|---:|---:|---:|
| prueba2.mp4 | 15 | 122 | 59 | 63 |
| tapas.mp4 | 10 | 14 | 0 | 14 |
| Total | 25 | 136 | 59 | 77 |

89,71 % de las cajas proceden de prueba2. Resoluciones originales: 1920×1080 en 15 imágenes y 1280×720 en 10. Ambos session_id son null, sin fecha de captura documentada. Las licencias y titulares también están pendientes; USER_SUPPLIED_REFERENCE_RIGHTS_UNCONFIRMED no acredita derechos de entrenamiento. Deben confirmarse con el responsable de los videos.

El agrupador conservador existente mantiene los 25 frames y ambos videos en **un único componente UNASSIGNED**, porque no se acreditan sesiones independientes. No repartirlos por fotograma ni asignar sesiones ficticias. Todos los physical_id de las tapas son null; no puede medirse cantidad de tapas físicas, seguimiento humano ni fuga entre identidades con estos datos.

## Condiciones: evidencia frente a desconocidos

| Condición | Evidencia disponible | Límite |
|---|---|---|
| Parcialmente visible | 135 partial=true; 1 false | Atributo humano; revisar criterio por su frecuencia muy alta, sin corregir automáticamente |
| Ocluida | 8 occluded=true; 128 false | Puede coexistir con partial; no sumar como categorías excluyentes |
| No evaluable | 136 not_evaluable=false | Es lo registrado; avisos técnicos no cambian esta etiqueta automáticamente |
| Suelta o separada | 29 notas humanas contienen «suelta» o «separada» | Son menciones textuales, no 29 objetos físicos ni campo de condición adjudicado |
| Colocada | Hay notas descriptivas y ejemplos visuales sobre cuello; 59 enlaces humanos | Un enlace no certifica colocación ni corrección; no se publica un conteo estructurado de colocadas |
| Ausente después del tapado | Sin referencia confirmada de etapa/obligación | NO EVALUABLE; no se contabilizan bocas vacías como TAPAS ni ausencias confirmadas |

Las 77 tapas sin enlace no son automáticamente sueltas. Una tapa colocada puede carecer de asociación anotada. Una tapa en el cuello no demuestra TAPA_CORRECTA ni geometría de cierre aceptable.

La revisión de las seis hojas muestra variedad limitada: tapas rojas, amarillas y blancas, superficies vistas por arriba/lateral, asas y roscas, tapas sueltas y objetos sobre cuellos. En prueba2 se repiten los mismos arreglos y fondos; en tapas predomina la tapa amarilla con máquina/fondo oscuro. Estas observaciones visuales no se convierten en etiquetas nuevas ni conteos por color. La asociación fuerte de apariencia con fuente puede sesgar el aprendizaje.

## Calidad geométrica, resolución y duplicados

Se verificaron las 25 imágenes por SHA-256 y dimensiones. Las últimas revisiones originales coinciden con la instantánea evaluada; los siete conflictos continúan pendientes. Cada una de las 136 cajas es finita, no vacía y está dentro de su imagen. Sus enlaces apuntan a ENVASE del mismo frame; no hay dos tapas asociadas al mismo padre en un frame.

Medidas nativas de TAPA:

- Ancho: 51,36–328,01 px; mediana 167,74 px.
- Alto: 51,33–218,84 px; mediana 114,78 px.
- Lado mínimo proyectado a entrada 640: 17,11–106,07 px; mediana 37,14 px. Ninguna queda por debajo de 16 px; falta cobertura de tapas muy pequeñas/distantes.
- Cero avisos de aspecto extremo (<0,1 o >10). Validez geométrica no acredita caja semánticamente ajustada ni objeto correcto.
- 11 crops con varianza Laplaciana nativa <50, todos en tapas.mp4. Es un aviso técnico de posible desenfoque dependiente de escala/textura, no causa demostrada ni regla para eliminar datos. No comparar este indicador directamente con el control de ROI reescalada del pipeline anterior.

Duplicados: cero SHA-256 de imagen repetidos; cero recortes con píxeles exactamente repetidos; cero parejas de imagen con dHash ≤4; cero parejas TAPA del mismo frame con IoU ≥0,80. No se eliminó nada. Estos umbrales no detectan todas las cajas duplicadas ni escenas correlacionadas; la continuidad temporal y los objetos repetidos siguen siendo un problema de independencia. En particular, ausencia de dHash cercano no transforma videos relacionados en sesiones distintas.

## Adjudicación pendiente

Siete cajas ENVASE describen tapas en sus notas: prueba2 frames 120, 240, 330; tapas frames 100, 250, 300, 350. La galería permite verlas; el revisor debe decidir objeto, clase, extensión y evaluabilidad. No cambiar solo la clase por el texto de la nota. Revisar si ya existe una caja TAPA para ese objeto para no introducir un duplicado.

También conviene adjudicar la caja ENVASE mínima registrada en la evaluación anterior y la convención partial/visible de las tapas. Toda corrección futura será nueva revisión de la copia, con autor, comentario y hash padre; los originales y resultados anteriores permanecen congelados. La segunda revisión independiente todavía no ocurrió.

## Ejemplos adicionales a grabar/anotar

1. **Sesiones identificables:** línea/SKU, cámara/vista, fecha, sesión, autorización y hash; clips de sesiones de captura realmente distintas. Registrar reaparición de los mismos envases físicos cuando se conozca.
2. **Tapas colocadas:** frontal, lateral, oblicua y posterior; cambios de color, material, diámetro, rosca, asa y reflejos; una tapa visible se anota TAPA independientemente de que su colocación sea aceptable.
3. **Tapas sueltas:** vistas interior/exterior, apoyadas o giradas, próximas a envases y aisladas; conservar SUELTA/INDETERMINADA cuando no hay propietario conocido.
4. **Escala y dificultad:** tapas con lado mínimo <16, 16–32 y >32 px al tamaño de entrada; desenfoque de movimiento, sombra, brillo, oclusiones por asa/mano/máquina y varios envases próximos. Mantener regiones ignoradas cuando no sea identificable el objeto.
5. **Confusores y negativos revisados:** cuellos, bocas, asas, anillos, etiquetas, reflejos y piezas de máquina. Una boca vacía no es una tapa. No convertir ausencia de anotación en negativo. Para afirmar TAPA_AUSENTE en inspección, exigir etapa posterior al tapado y obligación de tapa confirmadas por humano.
6. **Evidencia de asociación:** caja TAPA y ENVASE, enlace correcto conocido o desconocido, condición colocada/suelta/indeterminada y visibilidad. No copiar IDs de ByteTrack como identidad física.

Como primera campaña, reservar bloques de sesiones completos para desarrollo, validación y test antes de seleccionar imágenes o umbrales. Buscar más de una sesión real por bloque y diversidad de condiciones en cada uno. La cantidad final debe decidirse por cobertura y curvas de rendimiento; no existe un número de cajas que por sí solo garantice suficiencia. No extraer más fotogramas casi iguales para inflar el conteo.

## Plan concreto de entrenamiento y evaluación, todavía no ejecutado

**Puerta de datos.** Adjudicar conflictos; confirmar procedencia/derechos; documentar visibilidad y regiones ignoradas; verificar nuevamente hashes y cajas; fijar agrupación por sesión/video/objeto conocido. Congelar un manifiesto por partición con revisión y hash. Estos 25 frames conocidos permanecen como desarrollo, no test independiente después de ajustes.

**Objetivo inicial.** Detector independiente de una clase física TAPA, con ENVASE proporcionado por el baseline actual congelado. Así se pueden localizar tapas sueltas y colocadas sin reconstruir EPP ni confundir defectos con objetos. No crear cajas para TAPA_AUSENTE. El clasificador TinyCapCNN binario no se usa como detector ni como verdad de referencia.

**Configuración propuesta para revisar al autorizar entrenamiento.** Partir de pesos COCO locales de YOLO11s, crear pesos nuevos con cabeza TAPA y salida experimental propia. Registrar hash de inicialización, semilla, librerías y presupuesto de entrenamiento; fijar épocas/early stopping antes de ejecutar. Comenzar con tamaño 640; comparar 960 solo en validación si la cobertura de objetos pequeños lo justifica. Los pesos originales quedan intactos. La política de exportación debe admitir regiones ignoradas; el export YOLO plano actual excluye frames con no evaluables, y no debe transformarlos silenciosamente en fondo.

**Selección.** Revisar recall/FP y costo de inferencia en validación; elegir confianza/NMS allí, congelarlos y conservar todos los ensayos. No seleccionar por apariencia visual del test. No ajustar con pseudoetiquetas derivadas de predicciones anteriores.

**Prueba reservada.** Evaluar localización TAPA con coincidencia única por clase a IoU ≥0,50; TP/FP/FN, precisión/recall/F1 y PR/AP cuando haya soporte suficiente. Reportar resultados por sesión/video, tamaño, colocación y visibilidad adjudicados, con intervalos agrupados por sesión cuando la cantidad lo permita. No usar las 136 cajas como 136 muestras independientes. Objetos desconocidos/regiones ignoradas no son negativos.

**Puerta de asociación.** Evaluar después los enlaces tapa-envase con referencia humana específica, separando localización, enlace correcto, abstención y enlace incorrecto. No asignar por fuerza una tapa suelta al envase más próximo. Seguimiento y falsos eventos necesitan referencia temporal independiente; no se deducen de métricas de detección.

**Integración.** Solo incorporar el detector como capacidad experimental en Calidad tras evaluación trazable y revisión; defectos y asociación seguirán pendientes hasta su propia evaluación. No afirmar validación industrial ni activar rechazo automático.

## Verificación y archivos

Se añadieron un generador de auditoría y tres pruebas técnicas en `experimentos/pilotos/`; no se editaron los motores existentes. Pasaron 48 pruebas del laboratorio/contrato/portal/EPP y 21 del anotador existente: **69 pruebas**. Las pruebas de guardado e historial usan fixtures temporales, nunca los casos humanos reales.

Chrome: galería de siete conflictos con 14 imágenes y auditoría de 136 cajas con 272 imágenes, sin imágenes rotas. Se cargaron en el anotador los siete frames y sus box_id, sin guardar ninguna decisión. Los hashes de imágenes y revisiones de la copia importada se verificaron; no se añadieron etiquetas.

Artefactos: `auditoria_tapas.json`, `distribucion_condiciones.json`, `cajas_tapa.csv`, `procedencia_conflictos.json`, seis hojas en `contactos/`, evidencia Chrome y verificación final. Los indicadores y la galería son herramientas de revisión, no predicciones ni una adjudicación completada.

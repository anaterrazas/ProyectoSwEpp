"""Evaluación EPP independiente de Calidad y Django/SQLite.

Preparar referencias pendientes no crea anotaciones humanas. Ejecutar utiliza
los modelos locales y conserva sus observaciones sin convertirlas en referencia.
"""
import argparse
from collections import Counter
import hashlib
import html
from importlib.metadata import version
import json
import math
from pathlib import Path
import subprocess

import cv2
from seguridad.piloto import asociar, estados, Persistencia, CLASES

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = {"epp_corto": ROOT / "media/videos/trabajadores.mp4",
          "epp_largo": ROOT / "pruebas_ia/trabajadores.mp4"}
PESOS = {"epp": ROOT / "Modelos/best.pt", "personas": ROOT / "yolo11n.pt"}
EQUIPOS = ["CASCO", "CHALECO"]


def sha(path):
    with Path(path).open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def guardar(path, datos):
    with Path(path).open("x", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)


def leer(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def preparar(salida):
    salida.mkdir(parents=True, exist_ok=True)
    protegidos = {str(p.relative_to(ROOT)): sha(p) for p in [*VIDEOS.values(), *PESOS.values(), ROOT / "db.sqlite3"]}
    for carpeta in [ROOT / "produccion", ROOT / "config", ROOT / "datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset/revisions"]:
        for p in carpeta.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protegidos[str(p.relative_to(ROOT))] = sha(p)
    # Conservar también los artefactos de Calidad existentes sin mezclarlos con EPP.
    for p in (ROOT / "output/experimental_pilotos/evaluacion_deteccion_v002_001").rglob("*"):
        if p.is_file():
            protegidos[str(p.relative_to(ROOT))] = sha(p)
    guardar(salida / "protegidos_antes.json", protegidos)
    referencias = {"estado": "PENDIENTE_ANOTACION_HUMANA", "author": None, "reviewer": None,
                  "frames": [], "videos": [], "eventos": [], "eventos_exhaustivos": False,
                  "nota": "Listas vacías pendientes no son negativos ni ausencia de personas/EPP. No contiene predicciones."}
    for nombre, ruta in VIDEOS.items():
        carpeta = salida / nombre
        carpeta.mkdir(exist_ok=False)
        (carpeta / "originales").mkdir()
        captura = cv2.VideoCapture(str(ruta))
        n, fps = int(captura.get(cv2.CAP_PROP_FRAME_COUNT)), captura.get(cv2.CAP_PROP_FPS)
        indices = sorted({min(n-1, round(t * fps / 2)) for t in range(math.ceil(n / fps * 2))} | {n-1})
        for indice in indices:
            captura.set(cv2.CAP_PROP_POS_FRAMES, indice)
            ok, imagen = captura.read()
            if not ok:
                raise ValueError("No se pudo obtener un fotograma original.")
            path = carpeta / "originales" / f"frame_{indice:06d}.png"
            if not cv2.imwrite(str(path), imagen):
                raise OSError("No se guardó el PNG original.")
            referencias["frames"].append({"sample_id": f"{nombre}_{indice:06d}", "video_id": nombre,
                "frame_index": indice, "tiempo_nominal_s": indice/fps, "image": str(path.relative_to(salida)).replace('\\','/'),
                "image_sha256": sha(path), "width": imagen.shape[1], "height": imagen.shape[0],
                "status": "PENDING", "exhaustive": False, "objects": [], "personas": []})
        captura.release()
        referencias["videos"].append({"video_id": nombre, "path": str(ruta.relative_to(ROOT)),
            "video_sha256": protegidos[str(ruta.relative_to(ROOT))], "frames": n, "fps_nominal": fps,
            "tiempo_exhaustivamente_revisado_s": None, "sesion_independiente_confirmada": False})
    guardar(salida / "referencia_pendiente.json", referencias)
    generar_anotador(salida, referencias)
    print(json.dumps({"frames_para_anotar": len(referencias['frames']), "estado": referencias['estado']}), flush=True)


def generar_anotador(salida, referencias):
    plantilla = (Path(__file__).parent / "anotador_epp.html").read_text(encoding="utf-8")
    (salida / "anotar_referencia.html").write_text(plantilla.replace("__REFERENCE__", json.dumps(referencias, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")


def umbral_experimental(tipo, configuracion='base'):
    if configuracion not in ('base', 'candidata'):
        raise ValueError('Configuración experimental desconocida.')
    return .15 if configuracion == 'candidata' and tipo == 'Safety Vest' else .30


def estados_experimentales(personas, detecciones, configuracion='base'):
    if configuracion == 'base':
        return estados(personas, detecciones, EQUIPOS)
    evidencia={(track,equipo):set() for track in personas for equipo in EQUIPOS}
    for tipo,score,caja in detecciones:
        if not math.isfinite(score) or score < umbral_experimental(tipo,configuracion):
            continue
        for equipo,(positivo,negativo) in CLASES.items():
            if equipo not in EQUIPOS or tipo not in (positivo,negativo):
                continue
            track=asociar(caja,personas,equipo)
            if track is not None:
                evidencia[track,equipo].add('CUMPLE' if tipo==positivo else 'INCUMPLIMIENTO')
    return {k:next(iter(v)) if len(v)==1 else 'NO_EVALUABLE' for k,v in evidencia.items()}


def ejecutar_video(nombre, ruta, salida, referencias, epp, configuracion='base', personas_precalculadas=None):
    import imageio_ffmpeg
    from ultralytics import YOLO
    personas_modelo = YOLO(str(PESOS["personas"])) if personas_precalculadas is None else None
    carpeta = salida / nombre
    config = next(v for v in referencias["videos"] if v["video_id"] == nombre)
    fps = config["fps_nominal"]
    seleccionados = {f["frame_index"] for f in referencias["frames"] if f["video_id"] == nombre}
    persistencia = Persistencia()
    cobertura, clases, asociaciones = Counter(), Counter(), Counter()
    tracks = {}
    resultados = epp.predict(source=str(ruta), conf=.15 if configuracion=='candidata' else .30, imgsz=640, iou=.50, stream=True, save=False,
                             device="cpu", verbose=False)
    proceso = None
    fotogramas = 0
    estado = "ERROR"
    try:
        with (carpeta / "observaciones.jsonl").open("x", encoding="utf-8") as archivo:
            for resultado in resultados:
                original = resultado.orig_img
                personas, observaciones_persona = {}, []
                if personas_precalculadas is not None:
                    fila=personas_precalculadas[fotogramas]
                    if fila['frame_index']!=fotogramas or fila['video_id']!=nombre:
                        raise ValueError('Seguimiento base desalineado con el video.')
                    observaciones_persona=fila['personas']
                else:
                    personas_res = personas_modelo.track(original, classes=[0], conf=.30, imgsz=640,
                        tracker="bytetrack.yaml", persist=True, device="cpu", verbose=False)[0]
                    cajas_persona=personas_res.boxes if personas_res.boxes is not None else []
                    for caja in cajas_persona:
                        track = int(caja.id.item()) if caja.id is not None else None
                        bbox = caja.xyxy[0].tolist()
                        observaciones_persona.append({"class_name": "PERSONA", "bbox_xyxy": bbox,
                            "score": float(caja.conf[0]), "track_id": track})
                for observacion in observaciones_persona:
                    track=observacion['track_id'];bbox=observacion['bbox_xyxy']
                    if track is not None:
                        personas[track] = bbox
                        resumen = tracks.setdefault(track, {"primer_frame": fotogramas, "ultimo_frame": fotogramas,
                            "observaciones": 0, "saltos_de_observacion": 0, "max_gap_frames": 0})
                        gap = fotogramas - resumen["ultimo_frame"]
                        if resumen["observaciones"]:
                            resumen["max_gap_frames"] = max(resumen["max_gap_frames"], gap)
                            resumen["saltos_de_observacion"] += gap > 1
                        resumen["ultimo_frame"] = fotogramas
                        resumen["observaciones"] += 1
                epp_boxes = []
                for caja in resultado.boxes:
                    tipo = epp.names[int(caja.cls[0])]
                    bbox = caja.xyxy[0].tolist()
                    if float(caja.conf[0]) < umbral_experimental(tipo, configuracion):
                        continue
                    equipo = "CASCO" if tipo in ("Hardhat", "NO-Hardhat") else "CHALECO" if tipo in ("Safety Vest", "NO-Safety Vest") else None
                    track = asociar(bbox, personas, equipo) if equipo else None
                    epp_boxes.append({"class_name": tipo, "bbox_xyxy": bbox, "score": float(caja.conf[0]),
                        "equipo": equipo, "persona_track_id": track,
                        "asociacion": "ASIGNADA_HEURISTICA" if track is not None else "NO_ASIGNADA" if equipo else "FUERA_ALCANCE"})
                    clases[tipo] += 1
                    if equipo:
                        asociaciones[f"{equipo}_{'asignada' if track is not None else 'sin_asignar'}"] += 1
                estado_por_equipo = estados_experimentales(personas, [(b["class_name"], b["score"], b["bbox_xyxy"]) for b in epp_boxes], configuracion)
                cobertura.update(estado_por_equipo.values())
                nuevos = persistencia.observar(fotogramas/fps, estado_por_equipo)
                predicha = original.copy()
                for b in epp_boxes:
                    if not b["equipo"]:
                        continue
                    x1,y1,x2,y2 = map(round,b["bbox_xyxy"])
                    color = (0,100,255) if b["class_name"].startswith('NO-') else (60,220,60)
                    cv2.rectangle(predicha,(x1,y1),(x2,y2),color,2)
                    texto=f"{b['class_name']} {b['score']:.2f} -> ID {b['persona_track_id']}"
                    cv2.putText(predicha,texto,(max(0,x1),max(18,y1)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
                for b in observaciones_persona:
                    x1,y1,x2,y2=map(round,b['bbox_xyxy'])
                    cv2.rectangle(predicha,(x1,y1),(x2,y2),(255,180,0),2)
                    cv2.putText(predicha,f"PERSONA ID {b['track_id']}",(max(0,x1),max(20,y1+22)),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,180,0),2)
                for evento in nuevos:
                    evidencia = f"candidato_{len(persistencia.eventos)}_{evento['track_id']}_{evento['equipo']}.jpg"
                    if not cv2.imwrite(str(carpeta/evidencia),predicha):
                        raise OSError("No se guardó evidencia del candidato.")
                    evento["evidencia"]=evidencia
                    evento["evidencia_sha256"]=sha(carpeta/evidencia)
                frame_log = {"video_id": nombre, "frame_index": fotogramas, "tiempo_nominal_s": fotogramas/fps,
                    "personas": observaciones_persona, "epp": epp_boxes,
                    "estado_por_persona_equipo": [{"track_id": k[0], "equipo": k[1], "estado": v} for k,v in estado_por_equipo.items()],
                    "candidatos_nuevos": len(nuevos), "referencia_humana": "EXISTENTE_SOLO_EN_33_FRAMES" if fotogramas in seleccionados else "SIN_REFERENCIA_CONTINUA"}
                archivo.write(json.dumps(frame_log)+"\n")
                if fotogramas in seleccionados:
                    if not cv2.imwrite(str(carpeta/f"prediccion_{fotogramas:06d}.jpg"),predicha):
                        raise OSError("No se guardó la vista de predicción.")
                panel = cv2.hconcat([cv2.resize(original,(960,540)),cv2.resize(predicha,(960,540))])
                cv2.putText(panel,"ORIGINAL - GT SOLO EN 33 FRAMES EXISTENTES",(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2)
                cv2.putText(panel,"PREDICCIONES REALES - NO SON VERDAD HUMANA",(970,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,255),2)
                if proceso is None:
                    proceso=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-n','-v','error','-f','rawvideo','-pix_fmt','bgr24',
                        '-s','1920x540','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(carpeta/'comparativo.mp4')],stdin=subprocess.PIPE)
                proceso.stdin.write(panel.tobytes())
                fotogramas += 1
                if fotogramas % 100 == 0:
                    print(nombre, fotogramas, flush=True)
        if proceso is None:
            raise ValueError("No se procesaron fotogramas.")
        proceso.stdin.close()
        if proceso.wait()!=0 or fotogramas!=config['frames']:
            raise RuntimeError("Procesamiento incompleto.")
        estado="COMPLETADO"
    finally:
        resultados.close()
        if proceso and proceso.poll() is None:
            proceso.kill(); proceso.wait()
        resumen={"video_id":nombre,"estado":estado,"fotogramas":fotogramas,"frames_esperados":config['frames'],
            "configuracion":configuracion,"tracking_reutilizado":personas_precalculadas is not None,
            "clases_modelo_epp_observaciones":dict(clases),"observaciones_persona":sum(t['observaciones'] for t in tracks.values()),
            "ids_temporales":tracks,"asociaciones_heuristicas":dict(asociaciones),"observaciones_por_estado":dict(cobertura),
            "candidatos":persistencia.eventos,"persistencia_s":persistencia.segundos,"gap_max_s":persistencia.max_intervalo,
            "precision":None,"recall":None,"falsas_alarmas_por_minuto":None,
            "motivo_metricas":"Sin referencia humana exhaustiva revisada. Cero candidatos no prueba cero falsas alarmas ni cumplimiento.",
            "personas_unicas_reales":None,"id_switches":None,
            "nota":"CUMPLE en el motor significa evidencia positiva del equipo asociado, no conformidad global. NO_EVALUABLE nunca se convierte en negativo."}
        guardar(carpeta/'resumen.json',resumen)
    return resumen


def ejecutar(salida):
    from ultralytics import YOLO
    import ultralytics
    refs=leer(salida/'referencia_pendiente.json')
    epp=YOLO(str(PESOS['epp']))
    guardar(salida/'modelos_y_parametros.json',{'pesos':{k:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for k,p in PESOS.items()},
        'catalogo_epp':epp.names,'personas_clase_coco':0,'conf':.30,'imgsz':640,'device':'cpu','tracker':'bytetrack.yaml',
        'tracker_sha256':sha(Path(ultralytics.__file__).parent/'cfg/trackers/bytetrack.yaml'),
        'versiones':{p:version(p) for p in ['ultralytics','torch','opencv-python','numpy']}})
    resumenes=[ejecutar_video(nombre,ruta,salida,refs,epp) for nombre,ruta in VIDEOS.items()]
    guardar(salida/'resultados.json',{'videos':resumenes,'referencia_estado':'PENDIENTE_ANOTACION_HUMANA','metricas_ia':None})
    cards=[]
    for f in refs['frames']:
        sid=f['sample_id'];nombre=f['video_id'];indice=f['frame_index']
        cards.append(f'<article><h2>{html.escape(sid)} · {f["tiempo_nominal_s"]:.2f}s</h2><div class="paneles"><figure><figcaption>Original sin anotación humana todavía</figcaption><a href="{f["image"]}"><img loading="lazy" src="{f["image"]}"></a></figure><figure><figcaption>Predicción real, no referencia</figcaption><a href="{nombre}/prediccion_{indice:06d}.jpg"><img loading="lazy" src="{nombre}/prediccion_{indice:06d}.jpg"></a></figure></div></article>')
    videos=''.join(f'<h2>{r["video_id"]}</h2><video controls preload="metadata" src="{r["video_id"]}/comparativo.mp4"></video>' for r in resumenes)
    pagina='<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Seguridad ocupacional EPP · v002</title><style>body{font:16px system-ui;max-width:1500px;margin:25px auto;padding:15px}video{width:100%}.paneles{display:flex;gap:12px}figure{width:50%;margin:0}img{width:100%}article{border-top:1px solid #aaa;padding:15px 0}</style></head><body><h1>Seguridad ocupacional EPP · evaluación experimental</h1><p>Solo dos clips, sin duplicado adicional. Personas, casco, chaleco y asociaciones heurísticas. No hay referencia humana cerrada; precisión, recall y falsas alarmas por minuto no calculables.</p><p>Etiquetas CUMPLE del motor indican evidencia positiva del equipo, no cumplimiento global. IDs temporales no identifican trabajadores.</p>'+videos+''.join(cards)+'</body></html>'
    (salida/'index.html').write_text(pagina,encoding='utf-8')
    verificar(salida)


def verificar(salida):
    protegidos=leer(salida/'protegidos_antes.json')
    cambios=[p for p,h in protegidos.items() if sha(ROOT/p)!=h]
    if cambios:
        raise RuntimeError(f'Entradas modificadas: {cambios}')
    guardar(salida/'verificacion_inferencia.json',{'entradas_protegidas':len(protegidos),'cambios':cambios,
        'entrenamiento':False,'calidad_modificada':False,'sqlite_modificado':False,
        'artefactos':{str(p.relative_to(salida)):sha(p) for p in salida.rglob('*') if p.is_file()}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion',choices=['preparar','ejecutar'])
    parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args();salida=args.salida.resolve()
    if not salida.is_relative_to(ROOT/'output/experimental_pilotos'):
        raise ValueError('Salida fuera del laboratorio.')
    (preparar if args.accion=='preparar' else ejecutar)(salida)


if __name__=='__main__':
    main()

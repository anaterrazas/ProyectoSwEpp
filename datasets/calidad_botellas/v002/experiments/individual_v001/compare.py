"""Comparación previa a integración: todas las cajas provienen de modelos reales."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import time
import cv2
from detectors import BASE,ROOT,Detector,draw

NAMES=('yolo11n640','yolo11n1280','yolo11s640','yolo11s960','fasterrcnn320')


def main():
    target=BASE/'comparison/results.json'
    if target.exists():raise FileExistsError('Comparación existente; no sobrescribir')
    frames=[]
    for name in ('prueba2','tapas'):
        path=ROOT/'pruebas_ia'/(name+'.mp4');cap=cv2.VideoCapture(str(path));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        for index in sorted({round((count-1)*fraction/6) for fraction in range(7)}):
            cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,image=cap.read();assert ok
            frames.append((name,index,image))
        cap.release()
    rows=[]
    for name in NAMES:
        detector=Detector(name)
        detector.detect(frames[0][2])  # calentamiento excluido de tiempos comparativos
        folder=BASE/'comparison'/name;folder.mkdir(exist_ok=False)
        for video,index,image in frames:
            found,seconds=detector.detect(image)
            path=folder/f'{video}_{index}.jpg'
            cv2.imwrite(str(path),draw(image,found,f'{name} | {video} frame {index} | {len(found)} observaciones reales'))
            rows.append({'detector':name,'video':video,'frame_index':index,'detections':found,
                         'seconds':seconds,'image':path.relative_to(BASE).as_posix()})
        print(name,{video:sum(len(r['detections']) for r in rows if r['detector']==name and r['video']==video) for video in ('prueba2','tapas')},flush=True)
    summary={name:{video:{'sampled_frames':len(part),'detections':sum(len(r['detections']) for r in part),
                              'frames_with_detection':sum(bool(r['detections']) for r in part),
                              'mean_seconds_per_frame':statistics.mean(r['seconds'] for r in part)}
                    for video in ('prueba2','tapas') for part in [[r for r in rows if r['detector']==name and r['video']==video]]}
             for name in NAMES}
    data={'confidence_threshold':.3,'frames':rows,'summary':summary,
          'ground_truth_available':False,'detection_precision':None,'detection_recall':None,'map':None,
          'warning':'Más cajas no equivale a mayor exactitud. Revisar las imágenes; no hay anotación independiente.'}
    with target.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    with (BASE/'weights/sources.json').open('x',encoding='utf-8') as f:
        json.dump({'yolo11s':{'url':'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt','sha256':hashlib.sha256((BASE/'weights/yolo11s.pt').read_bytes()).hexdigest(),'license_reference':'https://docs.ultralytics.com/models/yolo11/'},
                   'fasterrcnn320':{'url':'https://download.pytorch.org/models/fasterrcnn_mobilenet_v3_large_320_fpn-907ea3f9.pth','sha256':hashlib.sha256((BASE/'weights/fasterrcnn_mobilenet_v3_large_320_fpn-907ea3f9.pth').read_bytes()).hexdigest()},
                   'existing_yolo11n_sha256':hashlib.sha256((ROOT/'yolo11n.pt').read_bytes()).hexdigest()},f,indent=2)


if __name__=='__main__':main()

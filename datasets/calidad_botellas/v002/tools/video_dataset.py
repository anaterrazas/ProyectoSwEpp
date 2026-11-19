"""Extensión aditiva de v002. Reutiliza capture_dataset; nunca carga modelos."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

import cv2
import imageio_ffmpeg
import numpy as np

import capture_dataset as photo

MODES=('recorded-real','conveyor-real','webcam-real')
MATERIALS=('PET','HDPE','PP','PVC','PE','OTHER','UNKNOWN')
MAX_BYTES=100*1024*1024


def inspect_video(path):
    path=Path(path).resolve()
    if path.suffix.lower()!='.mp4' or not 0<path.stat().st_size<=MAX_BYTES:
        raise ValueError('MP4 requerido, máximo 100 MiB')
    with path.open('rb') as handle:header=handle.read(64)
    if header[4:8]!=b'ftyp' or not any(brand in header[8:] for brand in (b'isom',b'iso2',b'mp41',b'mp42',b'avc1',b'M4V ')):
        raise ValueError('Contenido no compatible con MP4')
    cap=cv2.VideoCapture(str(path))
    try:
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps=cap.get(cv2.CAP_PROP_FPS);declared=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if not cap.isOpened() or not 1<=width<=1920 or not 1<=height<=1080 or not math.isfinite(fps) or not 0<fps<=60 or not 0<declared<=7200 or declared/fps>120.1:
            raise ValueError('Límites: 1920x1080, 60 FPS, 120 s, 7200 fotogramas')
    finally:cap.release()
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-nostdin','-copyts','-threads','2','-i',str(path),
             '-map','0:v:0','-an','-filter_threads','1','-vf','showinfo','-fps_mode','passthrough',
             '-frames:v','7202','-f','null','-']
    run=subprocess.run(command,capture_output=True,timeout=180)
    log=run.stderr.decode('utf-8',errors='replace')
    if run.returncode or not re.search(r'Video: (h264|mpeg4)\b',log):
        raise ValueError('Video ilegible o códec no permitido (H.264/MPEG-4)')
    entries=re.findall(r'\bn:\s*(\d+)\s+pts:\s*[-\d]+\s+pts_time:([-\d.eE+]+)',log)
    entries=[(int(n),float(t)) for n,t in entries]
    if not entries or len(entries)!=declared or len(entries)>7200 or [n for n,t in entries]!=list(range(len(entries))):
        raise ValueError('Decodificación incompleta o recuento de fotogramas inconsistente')
    pts=[t for n,t in entries]
    if not all(math.isfinite(t) for t in pts) or any(b<a for a,b in zip(pts,pts[1:])) or pts[-1]-pts[0]>120:
        raise ValueError('Tiempos de presentación inválidos o duración excesiva')
    # No usar n/fps como tiempo real: conservar PTS y origen incluso en VFR.
    return {'width':width,'height':height,'fps_nominal':fps,'frames':len(pts),
            'pts_seconds':pts,'time_origin_pts_seconds':pts[0],
            'duration_last_frame_seconds':pts[-1]-pts[0],
            'timestamp_method':'ffmpeg_showinfo_pts_first_video_stream',
            'codec':'h264' if re.search(r'Video: h264\b',log) else 'mpeg4'}


def decoded_frame(path,index):
    cap=cv2.VideoCapture(str(path))
    try:
        for number in range(index+1):
            ok,image=cap.read()
            if not ok:raise ValueError('No se pudo decodificar el fotograma exacto')
        return image
    finally:cap.release()


class VideoDataset(photo.Dataset):
    def profile(self,bottle_id,material,container_type,shape,color,cap_type,author):
        self.record('bottles',bottle_id)
        if material not in MATERIALS:raise ValueError('Material no reconocido; usar OTHER o UNKNOWN')
        identity=str(uuid4())
        record={'profile_id':identity,'bottle_id':bottle_id,'material':material,
                'container_type':photo.required(container_type),'shape':photo.required(shape),
                'color':photo.required(color),'cap_type':photo.required(cap_type),
                'author':photo.required(author),'recorded_at_utc':photo.now()}
        with self.lock():photo.write_new(self.root/'metadata/container_profiles'/(identity+'.json'),record)
        return record

    def video(self,path,session_id,captured_at,mode,own_capture,capture_offsets=None):
        if not own_capture or mode not in MODES:raise ValueError('Declarar captura real y modalidad válida')
        session=self.record('sessions',session_id);photo.timestamp(captured_at)
        path=Path(path).resolve();signature=photo.sha(path);metadata=inspect_video(path)
        if capture_offsets is not None and (len(capture_offsets)!=metadata['frames'] or any(not math.isfinite(t) or t<0 for t in capture_offsets) or any(b<a for a,b in zip(capture_offsets,capture_offsets[1:]))):raise ValueError('Reloj de captura inconsistente')
        with self.lock():
            if any(v['video_sha256']==signature for v in self.records('videos')):raise ValueError('Video duplicado SHA-256')
            identity=str(uuid4());relative='videos/originals/'+identity+'.mp4'
            target=self.root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(path.read_bytes())
            if photo.sha(target)!=signature:raise ValueError('Cambió el video durante la copia')
            result={'video_id':identity,'session_id':session_id,'video':relative,'video_sha256':signature,
                    'source_path_at_registration':str(path),'original_filename':path.name,
                    'captured_at':captured_at,'registered_at_utc':photo.now(),'capture_operator':session['operator'],
                    'origin':'OWN_REAL_CAPTURE','mode':mode,'synthetic_content_allowed':False,
                    'camera_capture_offsets_seconds':capture_offsets,
                    'camera_timing_note':'MP4 20 FPS; offsets monotónicos de recepción de cámara, no tiempo de exposición' if mode=='webcam-real' else None,**metadata}
            photo.write_new(self.root/'metadata/videos'/(identity+'.json'),result)
        return result

    def frame(self,video_id,bottle_id,profile_id,index,bbox=None,single_container=False):
        video=self.record('videos',video_id);self.record('bottles',bottle_id)
        profile=self.record('container_profiles',profile_id)
        if profile['bottle_id']!=bottle_id:raise ValueError('Perfil de otro envase')
        if type(index) is not int or not 0<=index<video['frames']:raise ValueError('Fotograma fuera de rango; índice comienza en cero')
        if bbox is None and not single_container:raise ValueError('Seleccionar ROI o confirmar un único envase en toda la imagen')
        path=(self.root/video['video']).resolve()
        if not path.is_relative_to(self.root/'videos/originals') or photo.sha(path)!=video['video_sha256']:raise ValueError('Video o ruta alterados')
        image=decoded_frame(path,index)
        if bbox is not None:
            if len(bbox)!=4 or any(type(v) is not int for v in bbox):raise ValueError('ROI: x y ancho alto enteros')
            x,y,w,h=bbox
            if min(x,y)<0 or min(w,h)<=0 or x+w>image.shape[1] or y+h>image.shape[0]:raise ValueError('ROI fuera de imagen')
            image=image[y:y+h,x:x+w]
        ok,encoded=cv2.imencode('.png',image)
        if not ok:raise ValueError('No se pudo codificar PNG')
        data=encoded.tobytes();signature=hashlib.sha256(data).hexdigest()
        if signature in self.forbidden_hashes():raise ValueError('Coincide con una muestra de público/v001')
        with self.lock():
            samples=self.records('samples')
            if any(s['image_sha256']==signature for s in samples):raise ValueError('Fotograma visualmente idéntico por SHA-256')
            if any(s.get('video_id')==video_id and s.get('frame_index')==index and s['bottle_id']==bottle_id for s in samples):raise ValueError('Ya se registró ese envase/fotograma')
            identity=str(uuid4());relative='images/originals/'+identity+'.png'
            target=self.root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(data)
            result={'sample_id':identity,'bottle_id':bottle_id,'session_id':video['session_id'],
                    'captured_at':video['captured_at'],'captured_at_scope':'video_start; use timestamp_seconds for frame',
                    'registered_at_utc':photo.now(),'origin':'OWN_REAL_CAPTURE','capture_operator':video['capture_operator'],
                    'original_filename':video['original_filename'],'source_path_at_registration':video['source_path_at_registration'],
                    'image':relative,'image_sha256':signature,'width':image.shape[1],'height':image.shape[0],
                    'format':'PNG','split':'UNASSIGNED','quality_warnings':[],
                    'license':'INTERNAL_NOT_PUBLICLY_LICENSED','video_id':video_id,'video_sha256':video['video_sha256'],
                    'frame_index':index,'pts_seconds':video['pts_seconds'][index],
                    'timestamp_seconds':video['pts_seconds'][index]-video['time_origin_pts_seconds'],
                    'timestamp_method':video['timestamp_method'],'bbox_xywh_pixels':bbox,
                    'single_container_confirmed':single_container,'profile_id':profile_id,
                    'profile_sha256':photo.sha(self.root/'metadata/container_profiles'/(profile_id+'.json')),
                    'derivation':'lossless PNG of decoded frame; optional human-selected ROI; no label inference'}
            photo.write_new(self.root/'metadata/samples'/(identity+'.json'),result)
        return result

    def event(self,video_id,bottle_id,start,end,defect,author,notes):
        video=self.record('videos',video_id);self.record('bottles',bottle_id)
        if defect not in photo.LABELS or type(start) is not int or type(end) is not int or not 0<=start<=end<video['frames']:raise ValueError('Clase o intervalo inválidos')
        if not any(s.get('video_id')==video_id and s['bottle_id']==bottle_id and start<=s['frame_index']<=end for s in self.records('samples')):raise ValueError('Registrar al menos un fotograma ancla del envase en el intervalo')
        identity=str(uuid4())
        result={'event_id':identity,'video_id':video_id,'video_sha256':video['video_sha256'],
                'bottle_id':bottle_id,'start_frame':start,'end_frame_inclusive':end,
                'start_timestamp_seconds':video['pts_seconds'][start]-video['time_origin_pts_seconds'],
                'end_timestamp_seconds':video['pts_seconds'][end]-video['time_origin_pts_seconds'],
                'defect_class':defect,'author':photo.required(author),'notes':photo.required(notes),
                'recorded_at_utc':photo.now(),'status':'HUMAN_ASSOCIATION_UNREVIEWED',
                'propagates_frame_labels':False,'supersedes_event_id':None}
        with self.lock():photo.write_new(self.root/'metadata/temporal_events'/(identity+'.json'),result)
        return result

    def components(self):
        samples=self.records('samples');parent={}
        def find(key):
            parent.setdefault(key,key)
            if parent[key]!=key:parent[key]=find(parent[key])
            return parent[key]
        for sample in samples:
            keys=['bottle:'+sample['bottle_id'],'session:'+sample['session_id']]
            if sample.get('video_id'):keys.append('video:'+sample['video_id'])
            for key in keys[1:]:parent[find(key)]=find(keys[0])
        groups={}
        for sample in samples:groups.setdefault(find('bottle:'+sample['bottle_id']),[]).append(sample['sample_id'])
        return [sorted(g) for g in groups.values()]

    def validate(self,proposal=None):
        report=super().validate(proposal);videos={v['video_id']:v for v in self.records('videos')}
        hashes=set()
        for identity,video in videos.items():
            photo.uid(identity);self.record('sessions',video['session_id']);photo.timestamp(video['captured_at'])
            path=(self.root/video['video']).resolve()
            if not path.is_relative_to(self.root/'videos/originals') or photo.sha(path)!=video['video_sha256']:raise ValueError('Hash/ruta de video alterados')
            if video['video_sha256'] in hashes:raise ValueError('Video duplicado')
            hashes.add(video['video_sha256'])
            measured=inspect_video(path)
            if any(video[k]!=measured[k] for k in measured):raise ValueError('Metadatos/timestamps del video alterados')
            if video['mode'] not in MODES or video['origin']!='OWN_REAL_CAPTURE':raise ValueError('Modalidad/procedencia inválida')
            offsets=video.get('camera_capture_offsets_seconds')
            if offsets is not None and (len(offsets)!=video['frames'] or any(not math.isfinite(t) or t<0 for t in offsets) or any(b<a for a,b in zip(offsets,offsets[1:]))):raise ValueError('Tiempos de recepción de cámara inconsistentes')
        known_paths={(self.root/v['video']).resolve() for v in videos.values()}
        if any(p.is_file() and p.resolve() not in known_paths for p in (self.root/'videos/originals').glob('*')):raise ValueError('Video sin metadatos')
        samples=self.records('samples');framed=[s for s in samples if s.get('video_id')]
        for sample in framed:
            video=videos[sample['video_id']];index=sample['frame_index'];profile=self.record('container_profiles',sample['profile_id'])
            if type(index) is not int or not 0<=index<video['frames']:raise ValueError('Índice inválido')
            if sample['video_sha256']!=video['video_sha256'] or sample['session_id']!=video['session_id']:raise ValueError('Referencia video/sesión inconsistente')
            if sample['pts_seconds']!=video['pts_seconds'][index] or abs(sample['timestamp_seconds']-(video['pts_seconds'][index]-video['time_origin_pts_seconds']))>1e-9:raise ValueError('Tiempo de fotograma inconsistente')
            if profile['bottle_id']!=sample['bottle_id'] or photo.sha(self.root/'metadata/container_profiles'/(sample['profile_id']+'.json'))!=sample['profile_sha256']:raise ValueError('Perfil de envase alterado')
            if profile['material'] not in MATERIALS:raise ValueError('Material inválido')
            image=decoded_frame(self.root/video['video'],index);roi=sample['bbox_xywh_pixels']
            if roi is not None:
                x,y,w,h=roi
                if any(type(v) is not int for v in roi) or min(x,y)<0 or min(w,h)<=0 or x+w>image.shape[1] or y+h>image.shape[0]:raise ValueError('ROI inválida')
                image=image[y:y+h,x:x+w]
            elif sample['single_container_confirmed'] is not True:raise ValueError('Falta asociación humana con el envase')
            ok,encoded=cv2.imencode('.png',image)
            if not ok or hashlib.sha256(encoded.tobytes()).hexdigest()!=sample['image_sha256']:raise ValueError('Derivación de fotograma no reproducible')
        for event in self.records('temporal_events'):
            video=videos[event['video_id']];self.record('bottles',event['bottle_id'])
            if event['defect_class'] not in photo.LABELS or event['video_sha256']!=video['video_sha256'] or not 0<=event['start_frame']<=event['end_frame_inclusive']<video['frames'] or event['propagates_frame_labels'] is not False:raise ValueError('Asociación temporal inválida')
            if event['start_timestamp_seconds']!=video['pts_seconds'][event['start_frame']]-video['time_origin_pts_seconds'] or event['end_timestamp_seconds']!=video['pts_seconds'][event['end_frame_inclusive']]-video['time_origin_pts_seconds']:raise ValueError('Tiempo del evento inconsistente')
            if event['status']!='HUMAN_ASSOCIATION_UNREVIEWED':raise ValueError('Estado temporal no autorizado')
            photo.required(event['author']);photo.required(event['notes'])
        report.update(videos=len(videos),video_hashes_verified=len(videos),video_frames_as_samples=len(framed),
                      individual_photos=len(samples)-len(framed),temporal_associations=len(self.records('temporal_events')),
                      materials=dict(Counter(self.record('container_profiles',s['profile_id'])['material'] for s in framed)),
                      automatic_quality_model='NOT_AVAILABLE',automatic_defects=None,automatic_confidence=None)
        report['warnings'].append('Fotogramas correlacionados: contar unidades físicas, videos y sesiones, no imágenes independientes')
        return report


def overlay(frame,index,seconds,region=None):
    display=frame.copy()
    if region is not None:
        x,y,w,h=region;cv2.rectangle(display,(x,y),(x+w,y+h),(0,255,255),2)
    lines=[f'Frame: {index} | tiempo: {seconds:.3f} s','Defectos: N/D | confianza: N/D',
           'Resultado: NO DISPONIBLE - sin modelo de calidad','Vista humana; Q o ESC para salir']
    for line,text in enumerate(lines):cv2.putText(display,text,(12,25+line*25),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),1)
    return display


def preview_video(dataset,video_id,delay_ms=None,roi=None):
    video=dataset.record('videos',video_id);path=dataset.root/video['video']
    if photo.sha(path)!=video['video_sha256']:raise ValueError('Hash de video alterado')
    cap=cv2.VideoCapture(str(path));index=0
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            image=overlay(frame,index,video['pts_seconds'][index]-video['time_origin_pts_seconds'],roi)
            cv2.imshow('EPP v002 - video real',image)
            if delay_ms is None:
                delay=round(1000*(video['pts_seconds'][index+1]-video['pts_seconds'][index])) if index+1<video['frames'] else 20
            else:delay=delay_ms
            index+=1
            if cv2.waitKey(max(1,delay))&255 in (27,ord('q')):break
    finally:cap.release();cv2.destroyAllWindows()
    return {'frames_shown':index,'automatic_result':None,'model_available':False}


def camera(dataset,device,seconds,session_id=None,record=False,own_capture=False,roi=None):
    if not 0<seconds<=120:raise ValueError('Duración entre 0 y 120 segundos')
    if record and (not own_capture or session_id is None):raise ValueError('Para grabar: sesión real y --own-capture')
    if record:dataset.record('sessions',session_id)
    cap=cv2.VideoCapture(device);writer=None;path=None;start=time.monotonic();captured=photo.now();index=0;offsets=[]
    try:
        if not cap.isOpened():raise ValueError('No se pudo abrir la cámara; no se creó una captura')
        while time.monotonic()-start<seconds:
            ok,frame=cap.read()
            if not ok:raise ValueError('La cámara dejó de entregar imágenes')
            if record and writer is None:
                height,width=frame.shape[:2]
                if width>1920 or height>1080:raise ValueError('Configurar cámara hasta 1920x1080')
                path=dataset.root/'incoming'/('webcam_'+str(uuid4())+'.mp4');path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb'):pass
                writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),20,(width,height))
                if not writer.isOpened():raise ValueError('No se pudo iniciar grabación MP4')
            if writer is not None:
                writer.write(frame);offsets.append(time.monotonic()-start)
            cv2.imshow('EPP v002 - camara real',overlay(frame,index,time.monotonic()-start,roi))
            index+=1
            if cv2.waitKey(50)&255 in (27,ord('q')):break
    finally:
        cap.release()
        if writer is not None:writer.release()
        cv2.destroyAllWindows()
    if path is not None:
        return dataset.video(path,session_id,captured,'webcam-real',True,capture_offsets=offsets)
    return {'frames_shown':index,'recorded':False,'automatic_result':None,'model_available':False}


def main():
    # Reutilizar literalmente los comandos fotográficos y el formato de revisión existente.
    if len(sys.argv)>1 and sys.argv[1] in ('session','bottle','capture','annotate','review'):
        return photo.main()
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    register=sub.add_parser('video')
    for key in ('file','session','captured-at'):register.add_argument('--'+key,required=True)
    register.add_argument('--mode',choices=MODES,required=True);register.add_argument('--own-capture',action='store_true')
    profile=sub.add_parser('container')
    for key in ('bottle','material','type','shape','color','cap-type','author'):profile.add_argument('--'+key,required=True)
    frame=sub.add_parser('frame')
    for key in ('video','bottle','profile'):frame.add_argument('--'+key,required=True)
    frame.add_argument('--index',type=int,required=True);frame.add_argument('--roi',nargs=4,type=int);frame.add_argument('--single-container',action='store_true')
    event=sub.add_parser('temporal-event')
    for key in ('video','bottle','author','notes'):event.add_argument('--'+key,required=True)
    event.add_argument('--defect',choices=photo.LABELS,required=True)
    event.add_argument('--start',type=int,required=True);event.add_argument('--end',type=int,required=True)
    preview=sub.add_parser('preview');preview.add_argument('--video',required=True);preview.add_argument('--roi',nargs=4,type=int)
    live=sub.add_parser('camera');live.add_argument('--device',type=int,default=0);live.add_argument('--seconds',type=float,default=10)
    live.add_argument('--record',action='store_true');live.add_argument('--session');live.add_argument('--own-capture',action='store_true')
    live.add_argument('--roi',nargs=4,type=int)
    for name in ('validate','coverage','propose-splits'):
        part=sub.add_parser(name);part.add_argument('--output',type=Path);part.add_argument('--proposal',type=Path)
    args=parser.parse_args();dataset=VideoDataset()
    if args.command=='video':result=dataset.video(args.file,args.session,args.captured_at,args.mode,args.own_capture)
    elif args.command=='container':result=dataset.profile(args.bottle,args.material,args.type,args.shape,args.color,args.cap_type,args.author)
    elif args.command=='frame':result=dataset.frame(args.video,args.bottle,args.profile,args.index,args.roi,args.single_container)
    elif args.command=='temporal-event':result=dataset.event(args.video,args.bottle,args.start,args.end,args.defect,args.author,args.notes)
    elif args.command=='preview':result=preview_video(dataset,args.video,roi=args.roi)
    elif args.command=='camera':result=camera(dataset,args.device,args.seconds,args.session,args.record,args.own_capture,args.roi)
    else:
        result=dataset.validate(photo.read(args.proposal) if args.proposal else None)
        if args.command=='propose-splits':result=dataset.propose()
        if args.output:
            allowed=photo.BASE/('splits' if args.command=='propose-splits' else 'reports')
            if not args.output.resolve().is_relative_to(allowed):raise ValueError('Salida fuera del directorio permitido de v002')
            photo.write_new(args.output.resolve(),result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired,cv2.error) as error:
        print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

"""Demo local experimental de foto/MP4; no escribe en Django ni en datasets fuente."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4,UUID

import cv2
import numpy as np
from PIL import Image,ImageOps
import torch

import model as quality
BASE=quality.BASE
sys.path.insert(0,str(BASE.parents[1]/'tools'))
import video_dataset as video


def write(path,data):
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def crop_image(image,roi):
    if roi is None:return image
    if len(roi)!=4 or any(type(v) is not int for v in roi):raise ValueError('ROI requiere cuatro enteros')
    x,y,w,h=roi
    if min(x,y)<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:raise ValueError('ROI fuera de imagen')
    return image.crop((x,y,x+w,y+h))


def annotation(frame,result,index,seconds,roi):
    frame=frame.copy()
    if roi is not None:
        x,y,w,h=roi;cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,255),2)
    cap=result['TAPA_DEFECTUOSA'];text=f"TAPA: score {cap['score']:.3f} / pred {cap['prediction']}" if cap['available'] else 'TAPA: MODELO NO DISPONIBLE'
    lines=[f'Frame {index} | {seconds:.3f} s | PROTOTIPO EXPERIMENTAL',text,
           'RAYADURA: SIN MODELO | DEFORMACION: SIN MODELO',
           'Score no calibrado. No acredita conformidad global.',
           'ROI fija/escena; sin localizar ni seguir envases.']
    for n,line in enumerate(lines):
        cv2.putText(frame,line,(12,25+24*n),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),3)
        cv2.putText(frame,line,(12,25+24*n),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,255),1)
    return frame


def process(input_path,output,roi=None,whole_frame=False,checkpoint=None):
    input_path=Path(input_path).resolve();output=Path(output).resolve()
    if not output.is_relative_to(BASE/'runs'):raise ValueError('Guardar resultados solo dentro de day1_v001/runs')
    if not whole_frame and roi is None:raise ValueError('Seleccione ROI o confirme explícitamente escena completa')
    if output.exists():raise FileExistsError('La salida ya existe; no se sobrescribe')
    torch.set_num_threads(2)
    checkpoint=Path(checkpoint) if checkpoint else BASE/'artifacts/cap_model.pt'
    classifier=quality.load_model(checkpoint) if checkpoint.exists() else None
    model_hash=hashlib.sha256(checkpoint.read_bytes()).hexdigest() if checkpoint.exists() else None
    before=hashlib.sha256(input_path.read_bytes()).hexdigest();start=time.perf_counter()
    is_video=input_path.suffix.lower()=='.mp4'
    if is_video:
        info=video.inspect_video(input_path)
        first=video.decoded_frame(input_path,0)
        crop_image(Image.fromarray(cv2.cvtColor(first,cv2.COLOR_BGR2RGB)),roi)
    else:
        with Image.open(input_path) as original:
            original.load()
            if original.format not in ('JPEG','PNG'):raise ValueError('Foto JPEG/PNG requerida')
            image=ImageOps.exif_transpose(original).convert('RGB')
        crop_image(image,roi)
    output.mkdir(parents=True,exist_ok=False)
    predictions=[]
    if not is_video:
        result=quality.predict(classifier,crop_image(image,roi))
        predictions.append({'frame_index':None,'timestamp_seconds':None,'classes':result})
        image.save(output/'original_preview.jpg')
        rendered=annotation(cv2.cvtColor(np.array(image),cv2.COLOR_RGB2BGR),result,0,0,roi)
        cv2.imwrite(str(output/'result.jpg'),rendered)
        media='result.jpg'
    else:
        # MP4 se codifica sin audio a FPS nominal; JSON conserva los PTS originales.
        cap=cv2.VideoCapture(str(input_path));writer=cv2.VideoWriter(str(output/'intermediate.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),info['fps_nominal'],(info['width'],info['height']))
        if not writer.isOpened():cap.release();raise ValueError('Codificador MP4 no disponible')
        index=0
        try:
            while True:
                ok,frame=cap.read()
                if not ok:break
                if index>=info['frames']:raise ValueError('Recuento no coincide con los PTS')
                seconds=info['pts_seconds'][index]-info['time_origin_pts_seconds']
                pil=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                result=quality.predict(classifier,crop_image(pil,roi))
                predictions.append({'frame_index':index,'pts_seconds':info['pts_seconds'][index],
                                    'timestamp_seconds':seconds,'classes':result})
                rendered=annotation(frame,result,index,seconds,roi);writer.write(rendered)
                if index==0:cv2.imwrite(str(output/'result.jpg'),rendered)
                index+=1
        finally:cap.release();writer.release()
        if index!=info['frames']:raise ValueError('Video incompleto; no afirmar procesamiento total')
        run=subprocess.run([video.imageio_ffmpeg.get_ffmpeg_exe(),'-n','-v','error','-i',str(output/'intermediate.mp4'),
                            '-c:v','libx264','-pix_fmt','yuv420p','-crf','23','-an',str(output/'result.mp4')],capture_output=True,timeout=180)
        if run.returncode:raise ValueError('No se pudo convertir el resultado a H.264')
        media='result.mp4'
    if hashlib.sha256(input_path.read_bytes()).hexdigest()!=before:raise ValueError('La fuente cambió')
    report={'experimental':True,'production_ready':False,'input_sha256':before,'model_sha256':model_hash,
            'model_available':classifier is not None,'kind':'video' if is_video else 'image','roi_xywh':roi,
            'inference_scope':'fixed human-selected ROI' if roi else 'whole scene; no object association',
            'not_an_object_detector':True,'not_global_conformity':True,'seconds':time.perf_counter()-start,
            'frames_processed':len(predictions) if is_video else None,'media':media,'preview':'result.jpg',
            'predictions':predictions,'ground_truth_available':False,'accuracy_measured_for_upload':None,
            'output_video_timing':'nominal FPS visualization; original PTS in predictions' if is_video else None,
            'warning':'Ensayo de tapas: test 17 imagenes/1 grupo; exactitud 58.8%, igual al baseline mayoritario. Sin modelo de rayadura/deformacion.'}
    write(output/'report.json',report)
    return report


class Handler(BaseHTTPRequestHandler):
    def response(self,data,status=200):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        name=self.path.split('?',1)[0]
        if name=='/':path=BASE/'web/index.html'
        elif name.startswith('/runs/'):
            path=(BASE/name.lstrip('/')).resolve()
            if not path.is_relative_to(BASE/'runs'):return self.response({'error':'Ruta no permitida'},403)
        else:return self.response({'error':'No encontrado'},404)
        if not path.is_file():return self.response({'error':'No encontrado'},404)
        content={'.html':'text/html; charset=utf-8','.jpg':'image/jpeg','.png':'image/png','.mp4':'video/mp4','.json':'application/json'}.get(path.suffix,'application/octet-stream')
        self.send_response(200);self.send_header('Content-Type',content);self.send_header('Content-Length',str(path.stat().st_size));self.end_headers()
        with path.open('rb') as f:
            while chunk:=f.read(1024*1024):self.wfile.write(chunk)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.response({'error':'Origen no permitido'},403)
            length=int(self.headers.get('Content-Length','0'))
            if self.path=='/api/upload':
                if not 0<length<=100*1024*1024:raise ValueError('Máximo 100 MiB')
                kind=self.headers.get('X-Media-Kind')
                if kind not in ('image','video'):raise ValueError('Tipo no permitido')
                identity=str(uuid4());directory=BASE/'runs'/identity;directory.mkdir(parents=True)
                path=directory/('input.mp4' if kind=='video' else 'input.image')
                data=self.rfile.read(length)
                if len(data)!=length:raise ValueError('Carga incompleta')
                with path.open('xb') as f:f.write(data)
                if kind=='video':
                    metadata=video.inspect_video(path);first=video.decoded_frame(path,0)
                    preview=Image.fromarray(cv2.cvtColor(first,cv2.COLOR_BGR2RGB))
                else:
                    with Image.open(path) as im:
                        im.load()
                        if im.format not in ('JPEG','PNG'):raise ValueError('Solo JPEG/PNG')
                        preview=ImageOps.exif_transpose(im).convert('RGB')
                    metadata={'width':preview.width,'height':preview.height}
                preview.thumbnail((960,960));preview.save(directory/'preview.jpg')
                write(directory/'upload.json',{'kind':kind,'input':path.name,'sha256':hashlib.sha256(data).hexdigest(),'metadata':metadata})
                return self.response({'job':identity,'width':metadata['width'],'height':metadata['height'],'preview':f'/runs/{identity}/preview.jpg'})
            if self.path=='/api/process':
                if not 0<length<=4096:raise ValueError('Solicitud inválida')
                request=json.loads(self.rfile.read(length));identity=str(UUID(request['job']))
                directory=BASE/'runs'/identity;upload=json.loads((directory/'upload.json').read_text(encoding='utf-8'))
                run_id=str(uuid4());output=directory/run_id
                result=process(directory/upload['input'],output,request.get('roi'),request.get('whole_frame') is True)
                prefix=f'/runs/{identity}/{run_id}/'
                return self.response({'result':result,'media_url':prefix+result['media'],'preview_url':prefix+'result.jpg','report_url':prefix+'report.json'})
            return self.response({'error':'No encontrado'},404)
        except (ValueError,KeyError,OSError,subprocess.TimeoutExpired,cv2.error) as exc:self.response({'error':str(exc)},400)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8790)
    cli=sub.add_parser('process');cli.add_argument('--input',type=Path,required=True);cli.add_argument('--output',type=Path,required=True)
    cli.add_argument('--roi',nargs=4,type=int);cli.add_argument('--whole-frame',action='store_true')
    args=parser.parse_args()
    if args.command=='serve':
        print(f'Demo experimental: http://127.0.0.1:{args.port}',flush=True)
        ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
    else:
        report=process(args.input,args.output,args.roi,args.whole_frame)
        print(json.dumps({k:v for k,v in report.items() if k!='predictions'},ensure_ascii=True,indent=2))

"""Inspección individual experimental: detector observado -> ByteTrack -> regiones -> gate."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML
import ultralytics

from detectors import BASE,ROOT,Detector
import quality_gate as gate
sys.path.insert(0,str(BASE.parents[1]/'tools'))
import video_dataset as video_tools


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


class ObservedTracker:
    """No devuelve posiciones predichas en fotogramas sin detección actual."""
    def __init__(self):
        self.path=Path(ultralytics.__file__).parent/'cfg/trackers/bytetrack.yaml'
        self.config=YAML.load(self.path);self.tracker=BYTETracker(SimpleNamespace(**self.config))

    def update(self,detections,image):
        array=np.asarray([[*d['bbox_xyxy'],d['score'],39] for d in detections],dtype=np.float32).reshape(-1,6)
        self.tracker.update(Boxes(array,image.shape[:2]).numpy(),image)
        mapping={}
        for track in self.tracker.tracked_stracks:
            if track.is_activated and track.frame_id==self.tracker.frame_id:
                index=int(track.idx)
                if 0<=index<len(detections):mapping[index]=int(track.track_id)
        return [{**d,'detection_index':i,'track_id':mapping.get(i),'observed_this_frame':True,
                 'tracking_status':'OBSERVED_TRACK' if i in mapping else 'OBSERVED_AWAITING_TRACK_CONFIRMATION',
                 'bbox_source':'CURRENT_DETECTOR_OBSERVATION_NOT_KALMAN_PREDICTION'} for i,d in enumerate(detections)]


def boxes_for_regions(box,shape):
    height,width=shape[:2];x1,y1,x2,y2=box
    x1=max(0,min(width-1,int(np.floor(x1))));y1=max(0,min(height-1,int(np.floor(y1))))
    x2=max(x1+1,min(width,int(np.ceil(x2))));y2=max(y1+1,min(height,int(np.ceil(y2))))
    split=max(y1+1,min(y2-1,y1+round((y2-y1)*.38)))
    return [x1,split,x2,y2],[x1,y1,x2,split]


def overlap_fraction(region,other):
    x1=max(region[0],other[0]);y1=max(region[1],other[1]);x2=min(region[2],other[2]);y2=min(region[3],other[3])
    return max(0,x2-x1)*max(0,y2-y1)/max(1,(region[2]-region[0])*(region[3]-region[1]))


def process(source,output,detector_name=None,approval=None):
    source=Path(source).resolve();output=Path(output).resolve()
    if not output.is_relative_to(BASE/'runs'):raise ValueError('Salida únicamente en individual_v001/runs')
    if output.exists():raise FileExistsError('No sobrescribir una ejecución previa')
    selection=json.loads((BASE/'comparison/selection.json').read_text(encoding='utf-8'))
    compared=json.loads((BASE/'comparison/results.json').read_text(encoding='utf-8'))
    detector_name=detector_name or selection['selected_detector']
    if detector_name not in compared['summary']:raise ValueError('Evaluar el detector antes de integrarlo')
    source_hash=sha(source);info=video_tools.inspect_video(source);run_id=str(uuid4())
    detector=Detector(detector_name);tracker=ObservedTracker();profile=gate.reference_profile()
    checkpoint=BASE.parent/'day1_v001/artifacts/cap_model.pt'
    classifier=gate.cap_model.load_model(checkpoint) if checkpoint.exists() else None
    output.mkdir(parents=True,exist_ok=False);(output/'crops').mkdir();(output/'screenshots').mkdir()
    write(output/'reference_domain_profile.json',profile)
    cap=cv2.VideoCapture(str(source));writer=cv2.VideoWriter(str(output/'intermediate.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),info['fps_nominal'],(info['width'],info['height']))
    if not writer.isOpened():cap.release();raise ValueError('No se pudo crear el video')
    summaries={};best={};reasons=Counter();observations=0;confirmed=0;calls=0;empty=0;multiple=0;detect_seconds=0;quality_seconds=0;reuse=0
    start=time.perf_counter();index=0;cached_bytes=0
    with (output/'frames.jsonl').open('x',encoding='utf-8') as frame_log:
        try:
            while True:
                ok,image=cap.read()
                if not ok:break
                if index>=info['frames']:raise ValueError('Más fotogramas que PTS')
                pts=info['pts_seconds'][index];timestamp=pts-info['time_origin_pts_seconds']
                detections,elapsed=detector.detect(image);detect_seconds+=elapsed
                detected=tracker.update(detections,image);observations+=len(detected)
                empty+=not bool(detected);multiple+=len(detected)>1
                drawn=image.copy();objects=[];t=time.perf_counter()
                for current in detected:
                    track_id=current['track_id'];body_box,cap_box=boxes_for_regions(current['bbox_xyxy'],image.shape)
                    body=image[body_box[1]:body_box[3],body_box[0]:body_box[2]]
                    neck=image[cap_box[1]:cap_box[3],cap_box[0]:cap_box[2]]
                    risk=any(overlap_fraction(cap_box,other['bbox_xyxy'])>.65 for other in detected if other['detection_index']!=current['detection_index'])
                    body_quality=gate.region_quality(body,body_box[3]>=image.shape[0]-2,False)
                    neck_quality=gate.region_quality(neck,cap_box[1]<=2 or cap_box[0]<=2 or cap_box[2]>=image.shape[1]-2,risk)
                    inspection=gate.classify(neck,neck_quality,profile,approval,source_hash,classifier)
                    calls+=inspection['classifier_called'];reasons.update(inspection['cap_gate']['reasons'])
                    object_record={**current,'video_sha256':source_hash,'run_id':run_id,'physical_container_id':None,
                        'frame_index':index,'pts_seconds':pts,'timestamp_seconds':timestamp,
                        'body_region':{'bbox_xyxy':body_box,'quality':body_quality,'method':'relative lower 62 percent; candidate body, not semantic segmentation'},
                        'cap_neck_region':{'bbox_xyxy':cap_box,'quality':neck_quality,'method':'relative upper 38 percent; UNCONFIRMED candidate, NOT a detected cap'},
                        **inspection}
                    objects.append(object_record)
                    if track_id is not None:
                        confirmed+=1
                        if track_id not in summaries:
                            summaries[track_id]={'track_id':track_id,'run_id':run_id,'video_sha256':source_hash,'physical_container_id':None,
                                'first_frame':index,'last_frame':index,'observed_frames':0,'consecutive_reuse_transitions':0,
                                'max_observation_gap_frames':0,'score_sum':0.,'inspection_result':'NO EVALUABLE','classifier_calls':0,
                                'rayadura':'NO DISPONIBLE','deformacion':'NO DISPONIBLE','cap_gate_reasons':Counter()}
                        record=summaries[track_id]
                        if record['observed_frames']:
                            gap=index-record['last_frame'];record['max_observation_gap_frames']=max(record['max_observation_gap_frames'],gap)
                            if gap==1:reuse+=1;record['consecutive_reuse_transitions']+=1
                        record['last_frame']=index;record['observed_frames']+=1;record['score_sum']+=current['score'];record['classifier_calls']+=inspection['classifier_called'];record['cap_gate_reasons'].update(inspection['cap_gate']['reasons'])
                        rank=neck_quality['laplacian_512']-1000*len(neck_quality['reasons'])
                        if track_id not in best or rank>best[track_id]['rank']:
                            ok1,png1=cv2.imencode('.png',body);ok2,png2=cv2.imencode('.png',neck)
                            if ok1 and ok2:
                                blobs=(png1.tobytes(),png2.tobytes());size=sum(map(len,blobs));previous=best.get(track_id,{}).get('size',0)
                                if cached_bytes-previous+size<=128*1024*1024:
                                    cached_bytes+=size-previous;best[track_id]={'rank':rank,'size':size,'images':blobs,'observation':object_record}
                    x1,y1,x2,y2=map(round,current['bbox_xyxy']);color=(0,220,0) if track_id is not None else (0,160,255)
                    cv2.rectangle(drawn,(x1,y1),(x2,y2),color,2)
                    label=f"ID {track_id}" if track_id is not None else 'OBS sin ID confirmado'
                    cv2.putText(drawn,f"{label} | obs {current['score']:.2f} | NO EVALUABLE",(max(0,x1),max(20,y1+20)),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),3)
                    cv2.putText(drawn,f"{label} | obs {current['score']:.2f} | NO EVALUABLE",(max(0,x1),max(20,y1+20)),cv2.FONT_HERSHEY_SIMPLEX,.48,color,1)
                    # ROI derivada visible distinta a la caja observada: no se declara detección de tapa.
                    cx1,cy1,cx2,cy2=cap_box;cv2.rectangle(drawn,(cx1,cy1),(cx2,cy2),(255,170,0),1)
                quality_seconds+=time.perf_counter()-t
                state='SIN ENVASES DETECTADOS - NO EVALUABLE' if not objects else f'{len(objects)} observaciones; {len(summaries)} IDs temporales (NO unidades fisicas)'
                for line,text in enumerate([f'{source.name} frame {index} | PTS {pts:.4f} | {detector_name}',state,
                    'RAYADURA / DEFORMACION: NO DISPONIBLE | nunca CONFORME',
                    'Verde: deteccion observada con ID; naranja: sin ID; azul: ROI candidata']):
                    cv2.putText(drawn,text,(10,image.shape[0]-90+line*22),cv2.FONT_HERSHEY_SIMPLEX,.53,(0,0,0),3)
                    cv2.putText(drawn,text,(10,image.shape[0]-90+line*22),cv2.FONT_HERSHEY_SIMPLEX,.53,(0,255,255),1)
                writer.write(drawn)
                if index in (0,info['frames']//2,info['frames']-1):cv2.imwrite(str(output/'screenshots'/f'frame_{index:06d}.jpg'),drawn)
                frame_log.write(json.dumps({'frame_index':index,'pts_seconds':pts,'timestamp_seconds':timestamp,
                    'inspection_result':'NO EVALUABLE','objects':objects,'detections_observed':len(detected)},ensure_ascii=False)+'\n')
                index+=1
                if index%100==0:print(source.name,index,'observaciones',observations,'IDs',len(summaries),flush=True)
        finally:cap.release();writer.release()
    if index!=info['frames']:raise ValueError('Procesamiento incompleto')
    inference_pipeline_seconds=time.perf_counter()-start;encode_start=time.perf_counter()
    run=subprocess.run([video_tools.imageio_ffmpeg.get_ffmpeg_exe(),'-n','-v','error','-i',str(output/'intermediate.mp4'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','23','-an',str(output/'processed.mp4')],capture_output=True,timeout=180)
    if run.returncode:raise ValueError('Fallo de codificación H.264')
    encode_seconds=time.perf_counter()-encode_start
    for track_id,record in summaries.items():
        record['mean_detector_score']=record.pop('score_sum')/record['observed_frames'];record['cap_gate_reasons']=dict(record['cap_gate_reasons'])
        if track_id in best:
            candidate=best[track_id];folder=output/'crops'/f'track_{track_id:04d}';folder.mkdir()
            saved=[]
            for name,blob in zip(('body.png','cap_neck_candidate.png'),candidate['images']):
                with (folder/name).open('xb') as handle:handle.write(blob)
                saved.append({'path':(folder/name).relative_to(output).as_posix(),'sha256':hashlib.sha256(blob).hexdigest()})
            write(folder/'observation.json',candidate['observation']);record['best_observation_frame']=candidate['observation']['frame_index'];record['saved_regions']=saved
        else:record['saved_regions']=[];record['crop_note']='No crop guardado: limite de memoria'
    if sha(source)!=source_hash:raise ValueError('Fuente modificada')
    report={'run_id':run_id,'source_video':str(source),'input_video_sha256':source_hash,'model_detector':detector_name,
        'detector_weights_sha256':sha(detector.path),'classifier_weights_sha256':sha(checkpoint) if checkpoint.exists() else None,
        'tracker':'ByteTrack unmodified installed implementation','tracker_config':tracker.config,'tracker_config_sha256':sha(tracker.path),
        'comparison_sha256':sha(BASE/'comparison/results.json'),'video_metadata':info,'frames_processed':index,
        'video_duration_estimate_seconds':info['duration_last_frame_seconds']+1/info['fps_nominal'],
        'processing_seconds':time.perf_counter()-start,'decode_detection_tracking_crop_seconds':inference_pipeline_seconds,
        'detector_seconds':detect_seconds,'quality_and_classification_seconds':quality_seconds,'h264_encode_seconds':encode_seconds,
        'observed_detections':observations,'observations_with_confirmed_track_id':confirmed,'frames_without_detection':empty,
        'frames_with_multiple_detections':multiple,'temporary_track_ids':len(summaries),'consecutive_id_reuse_transitions':reuse,
        'classifier_calls':calls,'cap_block_reasons':dict(reasons),'tracks':list(summaries.values()),
        'ground_truth_available':False,'precision':None,'recall':None,'map':None,'id_switches':None,'physical_container_count':None,
        'inspection_result':'NO EVALUABLE','global_conformity':None,'quality_models_unavailable':['RAYADURA','DEFORMACION'],
        'approval_used':approval,'labels_created':0,'training_performed':False,
        'warnings':['Cajas observadas del detector, no verdad humana','IDs temporales no prueban identidades físicas; puede haber fragmentación',
                    'Regiones de cuerpo/tapa son candidatas geométricas no confirmadas','El veto de dominio no es un clasificador de compatibilidad validado',
                    'Video visual a FPS nominal; PTS originales en frames.jsonl']}
    write(output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('frames_processed','observed_detections','temporary_track_ids','frames_without_detection','classifier_calls','processing_seconds')}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--detector');parser.add_argument('--approval',type=Path)
    args=parser.parse_args()
    process(args.input,args.output,args.detector,json.loads(args.approval.read_text(encoding='utf-8')) if args.approval else None)

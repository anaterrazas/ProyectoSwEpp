"""Controles técnicos y veto conservador de dominio. No generan etiquetas."""
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from detectors import BASE,ROOT

sys.path.insert(0,str(BASE.parent/'day1_v001'))
import model as cap_model


def appearance(image):
    small=cv2.resize(image,(96,96),interpolation=cv2.INTER_AREA)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    yellow=(hsv[:,:,0]>=18)&(hsv[:,:,0]<=38)&(hsv[:,:,1]>80)
    return np.array([gray.mean()/255.,np.mean(gray<60),np.mean(gray>180),np.mean(hsv[:,:,1]>80),np.mean(yellow)],dtype=float)


def reference_profile():
    manifest=BASE.parent/'day1_v001/dataset/train_manifest.jsonl'
    rows=[json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines()]
    vectors=[]
    for row in rows:
        path=ROOT/row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['expected_hash']:raise ValueError('Referencia de entrenamiento alterada')
        image=cv2.imread(str(path))
        if image is None:raise ValueError('Referencia ilegible')
        vectors.append(appearance(image).tolist())
    array=np.asarray(vectors);distances=np.linalg.norm(array[:,None,:]-array[None,:,:],axis=2)
    np.fill_diagonal(distances,np.inf)
    threshold=float(min(.25,max(.05,np.quantile(distances.min(axis=1),.95)*1.5)))
    return {'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'train_only_reference_vectors':vectors,'max_nearest_distance':threshold,
            'method':'unvalidated appearance veto; never sufficient to accept without explicit human domain approval',
            'labels_inferred':False}


def region_quality(image,clipped=False,occlusion_risk=False):
    height,width=image.shape[:2]
    scale=min(1,512/max(height,width));small=cv2.resize(image,(max(1,round(width*scale)),max(1,round(height*scale))))
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);sharp=float(cv2.Laplacian(gray,cv2.CV_64F).var())
    dark=float(np.mean(gray<=10));bright=float(np.mean(gray>=245));reasons=[]
    if width<64 or height<48:reasons.append('RESOLUCION_INSUFICIENTE')
    if sharp<50:reasons.append('POSIBLE_DESENFOQUE')
    if dark>.6 or bright>.6:reasons.append('EXPOSICION_EXTREMA')
    if clipped:reasons.append('REGION_EN_BORDE_DE_IMAGEN')
    if occlusion_risk:reasons.append('SOLAPAMIENTO_AMBIGUO_CON_OTRO_ENVASE')
    return {'width':width,'height':height,'laplacian_512':sharp,'dark_fraction':dark,'bright_fraction':bright,
            'technical_pass':not reasons,'visibility':'UNVERIFIED' if not reasons else 'INSUFFICIENT_OR_UNCERTAIN',
            'reasons':reasons,'not_a_human_evaluability_label':True}


def eligibility(image,technical,profile,approval,video_hash):
    reasons=list(technical['reasons']);vector=appearance(image)
    distance=float(np.linalg.norm(np.asarray(profile['train_only_reference_vectors'])-vector,axis=1).min())
    if distance>profile['max_nearest_distance']:reasons.append('FUERA_DEL_DOMINIO_VISUAL_DE_REFERENCIA')
    # Superar un veto heurístico no acredita dominio: exigir revisión explícita de escena y ROI.
    if not approval or approval.get('video_sha256')!=video_hash:reasons.append('SIN_APROBACION_DE_DOMINIO_PARA_ESTE_VIDEO')
    else:
        if not isinstance(approval.get('reviewer_id'),str) or not approval['reviewer_id'].strip():reasons.append('SIN_REVISOR_IDENTIFICADO')
        if approval.get('compatible_with_training_domain') is not True:reasons.append('DOMINIO_NO_CONFIRMADO')
        if approval.get('cap_neck_roi_assignment_verified') is not True:reasons.append('ROI_DE_TAPA_CUELLO_NO_CONFIRMADA')
        if approval.get('post_capping_inspection_stage_verified') is not True or approval.get('cap_required') is not True:reasons.append('ETAPA_Y_OBLIGACION_DE_TAPA_NO_CONFIRMADAS')
    return {'eligible':not reasons,'reasons':list(dict.fromkeys(reasons)),
            'appearance_distance':distance,'appearance_threshold':profile['max_nearest_distance'],
            'method':'technical checks + train-reference veto + explicit human scene/ROI/stage approval',
            'domain_check_calibrated':False}


def unavailable(reason):
    return {'available':False,'prediction':None,'score':None,'status':'NO DISPONIBLE','reason':reason}


def classify(image,quality,profile,approval,video_hash,classifier):
    gate=eligibility(image,quality,profile,approval,video_hash)
    result={'RAYADURA':unavailable('Sin modelo entrenado'),'DEFORMACION':unavailable('Sin modelo entrenado')}
    if gate['eligible'] and classifier is not None:
        from PIL import Image
        result['TAPA_DEFECTUOSA']=cap_model.predict(classifier,Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB)))['TAPA_DEFECTUOSA']
        result['TAPA_DEFECTUOSA']['status']='SOLO CLASIFICACION EXPERIMENTAL DE TAPA'
        called=True
    else:
        result['TAPA_DEFECTUOSA']=unavailable('NO EVALUABLE: '+', '.join(gate['reasons']) if not gate['eligible'] else 'Modelo ausente')
        called=False
    # Sin modelos de cuerpo no existe una inspección global completa, aun con tapa evaluada.
    return {'inspection_result':'NO EVALUABLE','classes':result,'cap_gate':gate,'classifier_called':called,
            'global_conformity':None,'scope':'partial cap evaluation only; no body quality models'}

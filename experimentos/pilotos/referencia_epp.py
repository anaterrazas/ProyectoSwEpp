"""Validación de referencias EPP, independiente de predicciones y Calidad."""
import math
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def validar_frame(frame):
    status = frame.get("status")
    if status not in ("PENDING", "DRAFT", "ANNOTATED", "REVIEWED"):
        raise ValueError("Estado de anotación desconocido.")
    if status in ("PENDING", "DRAFT"):
        return False
    if not frame.get("exhaustive") or not frame.get("author"):
        raise ValueError("Una anotación cerrada requiere autor y exhaustividad.")
    if status == "REVIEWED" and (not frame.get("reviewer") or frame["reviewer"] == frame["author"]):
        raise ValueError("Se requiere un revisor distinto del anotador.")
    objects = frame.get("objects", [])
    personas = {p["id"]: p for p in frame.get("personas", [])}
    if len(personas) != len(frame.get("personas", [])):
        raise ValueError("Identificador humano de persona repetido.")
    if not objects and not frame.get("empty_confirmed"):
        raise ValueError("Una lista vacía no es un negativo confirmado.")
    ids = set()
    for obj in objects:
        if obj["id"] in ids:
            raise ValueError("ID de objeto repetido.")
        ids.add(obj["id"])
        if obj["clase"] not in ("PERSONA", "CASCO", "CHALECO"):
            raise ValueError("Clase fuera del piloto.")
        x1,y1,x2,y2 = obj["bbox_xyxy"]
        if not all(math.isfinite(v) for v in [x1,y1,x2,y2]) or not (0 <= x1 < x2 <= frame["width"] and 0 <= y1 < y2 <= frame["height"]):
            raise ValueError("Caja fuera de imagen.")
        if obj.get("visibilidad") not in ("VISIBLE", "PARCIAL", "OCLUIDO", "NO_EVALUABLE"):
            raise ValueError("La visibilidad debe decidirse explícitamente.")
        owner = obj.get("persona_id")
        if owner and owner not in personas:
            raise ValueError("Asociación a una persona inexistente en el fotograma.")
    for pid, persona in personas.items():
        if not any(o["clase"] == "PERSONA" and o.get("persona_id") == pid for o in objects):
            raise ValueError("Persona sin caja de referencia.")
        for equipo in ("casco", "chaleco"):
            estado = persona.get(equipo + "_estado")
            positivos = [o for o in objects if o["clase"] == equipo.upper() and o.get("persona_id") == pid
                         and o.get("visibilidad") != "NO_EVALUABLE"]
            if estado not in ("PRESENTE", "AUSENTE", "NO_EVALUABLE"):
                raise ValueError("El estado de cada equipo debe decidirse explícitamente.")
            if estado == "AUSENTE" and (persona.get(equipo + "_region_visible") is not True or positivos):
                raise ValueError("Ausencia requiere región visible y no puede contradecir equipo presente.")
            if estado == "PRESENTE" and not positivos:
                raise ValueError("Presencia requiere equipo visible anotado y asociado.")
    return status == "REVIEWED"


def validar_documento(documento, base):
    originales={f['sample_id']:f for f in base['frames']}
    if len(documento['frames'])!=len(originales) or len({f['sample_id'] for f in documento['frames']})!=len(originales):
        raise ValueError('La copia debe conservar los mismos fotogramas, sin duplicados.')
    estados=Counter()
    revisados=0
    for frame in documento['frames']:
        original=originales.get(frame['sample_id'])
        if original is None or any(frame.get(k)!=original.get(k) for k in
            ['video_id','frame_index','image','image_sha256','width','height','tiempo_nominal_s']):
            raise ValueError('Se modificó la procedencia de un fotograma.')
        revisados+=validar_frame(frame)
        estados[frame['status']]+=1
    if documento.get('eventos_exhaustivos'):
        videos={v['video_id']:v for v in documento['videos']}
        for original in base['videos']:
            video=videos.get(original['video_id'])
            duracion=original['frames']/original['fps_nominal']
            if not video or video.get('video_sha256')!=original['video_sha256'] or video.get('tiempo_exhaustivamente_revisado_s')!=duracion:
                raise ValueError('No está confirmada la revisión temporal completa de cada video.')
        for e in documento['eventos']:
            video=videos.get(e['video_id'])
            if not video or not (0<=e['inicio_s']<e['fin_s']<=video['frames']/video['fps_nominal']):
                raise ValueError('Intervalo de evento inválido.')
            if e['equipo'] not in ('CASCO','CHALECO') or e['estado'] not in ('AUSENTE','NO_EVALUABLE'):
                raise ValueError('Evento fuera del alcance.')
            if not e.get('author') or not e.get('reviewer') or e['author']==e['reviewer'] or not e.get('persona_id'):
                raise ValueError('Evento sin identidad humana o revisión independiente declarada.')
    return {'frames':len(originales),'estados':dict(estados),'frames_revisados':revisados,
            'referencia_deteccion_disponible':revisados>0,
            'referencia_temporal_declarada_completa':documento.get('eventos_exhaustivos') is True,
            'precision':None,'recall':None,'falsas_alarmas_por_minuto':None,
            'nota':'Valida estructura y cierre; no certifica autoría ni verdad semántica y no compara predicciones.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--referencia',type=Path,required=True)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args()
    raiz=Path(__file__).resolve().parents[2]/'output/experimental_pilotos'
    if not args.salida.resolve().is_relative_to(raiz):raise ValueError('Salida fuera del laboratorio.')
    documento=json.loads(args.referencia.read_text(encoding='utf-8'));base=json.loads(args.base.read_text(encoding='utf-8'))
    resultado=validar_documento(documento,base)
    resultado['referencia_sha256']=hashlib.sha256(args.referencia.read_bytes()).hexdigest()
    resultado['base_sha256']=hashlib.sha256(args.base.read_bytes()).hexdigest()
    with args.salida.open('x',encoding='utf-8') as archivo:json.dump(resultado,archivo,ensure_ascii=False,indent=2)


if __name__=='__main__':main()

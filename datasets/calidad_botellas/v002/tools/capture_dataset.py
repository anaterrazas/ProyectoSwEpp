"""Captura propia EPP v002, offline, sin Django, modelos ni entrenamiento."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4, UUID

from PIL import Image

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
LABELS = ('RAYADURA', 'DEFORMACION', 'TAPA_DEFECTUOSA')
SPLITS = ('train', 'validation', 'test')


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def uid(value):
    if str(UUID(value)) != value:
        raise ValueError('UUID no canónico')
    return value


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('La fecha requiere zona horaria, por ejemplo -04:00')
    return value


def required(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Metadato obligatorio vacío')
    return value.strip()


def blank_annotation():
    return {'labels': dict.fromkeys(LABELS), 'evaluable': {'body': None, 'cap': None},
            'other_defect': None, 'categories': {'CONFORME': None, 'NO_EVALUABLE': None}, 'notes': ''}


def check_annotation(annotation):
    if set(annotation) != set(blank_annotation()):
        raise ValueError('Campos de anotación incompatibles con la plantilla')
    labels = annotation['labels']; regions = annotation['evaluable']; cats = annotation['categories']
    if set(labels) != set(LABELS) or any(v is not None and (type(v) is not int or v not in (0,1)) for v in labels.values()):
        raise ValueError('Etiquetas: únicamente 1, 0 o null; booleanos no permitidos')
    for values, keys in ((regions, {'body','cap'}), (cats, {'CONFORME','NO_EVALUABLE'})):
        if set(values) != keys or any(v is not None and type(v) is not bool for v in values.values()):
            raise ValueError('Evaluabilidad/categorías: true, false o null')
    if annotation['other_defect'] is not None and type(annotation['other_defect']) is not bool:
        raise ValueError('Otros defectos: true, false o null')
    if not isinstance(annotation['notes'], str) or len(annotation['notes']) > 4000:
        raise ValueError('Observaciones inválidas')
    for key, value in labels.items():
        if value == 0 and regions['cap' if key=='TAPA_DEFECTUOSA' else 'body'] is not True:
            raise ValueError('Un negativo requiere región evaluable')
    if cats['CONFORME'] is True and not (all(v==0 for v in labels.values()) and all(v is True for v in regions.values()) and annotation['other_defect'] is False and cats['NO_EVALUABLE'] is False):
        raise ValueError('CONFORME requiere evidencia completa y ausencia de otros defectos')
    if cats['NO_EVALUABLE'] is True and not annotation['notes'].strip():
        raise ValueError('Explique la insuficiencia de evidencia')


class Dataset:
    def __init__(self, root=BASE):
        self.root = Path(root).resolve()
        config = read(self.root/'dataset.json')
        if config['dataset_id'] != 'epp-own-v002' or config['origin'] != 'OWN_REAL_CAPTURE':
            raise ValueError('Versión/origen incorrectos')
        self.config = config

    @contextmanager
    def lock(self):
        path = self.root/'metadata'/'.write.lock'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as handle:
            handle.write(now())
        try:
            yield
        finally:
            path.unlink()  # Solo el bloqueo temporal creado por esta operación.

    def records(self, kind):
        return [read(p) for p in sorted((self.root/'metadata'/kind).glob('*.json'))]

    def record(self, kind, identity):
        uid(identity)
        return read(self.root/'metadata'/kind/(identity+'.json'))

    def session(self, operator, product, lot, stage, camera, position, lighting, cap_required):
        record = {k: required(v) for k,v in dict(operator=operator,product=product,lot=lot,stage=stage,camera=camera,position=position,lighting=lighting).items()}
        if type(cap_required) is not bool:
            raise ValueError('Indique si la tapa es obligatoria en esta etapa')
        identity = str(uuid4())
        record.update(session_id=identity,registered_at_utc=now(),cap_required=cap_required,
                      origin='OWN_REAL_CAPTURE',camera_fixed=True)
        with self.lock():
            write_new(self.root/'metadata/sessions'/(identity+'.json'),record)
        return record

    def bottle(self, inventory_reference):
        reference = required(inventory_reference)
        with self.lock():
            if any(r['inventory_reference']==reference for r in self.records('bottles')):
                raise ValueError('La referencia ya tiene ID; reutilícelo para la misma botella')
            identity = str(uuid4())
            result = {'bottle_id':identity,'inventory_reference':reference,'registered_at_utc':now()}
            write_new(self.root/'metadata/bottles'/(identity+'.json'),result)
        return result

    def forbidden_hashes(self):
        result = set()
        for path in (PROJECT/'datasets/publicos_calidad_botellas/imports').glob('*/samples.public.jsonl'):
            result.update(r['image_sha256'] for r in rows(path))
        for path in (PROJECT/'datasets/calidad_botellas/v001').rglob('samples.jsonl'):
            result.update(r['image_sha256'] for r in rows(path))
        return result

    def capture(self, image, session_id, bottle_id, captured_at, own_capture):
        if not own_capture:
            raise ValueError('Debe confirmar procedencia propia real con --own-capture')
        session=self.record('sessions',session_id); self.record('bottles',bottle_id)
        timestamp(captured_at)
        image=Path(image).resolve();data=image.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest in self.forbidden_hashes():
            raise ValueError('Coincide con dataset público o las muestras v001; no es una captura nueva')
        with Image.open(image) as photo:
            fmt=photo.format;photo.verify()
        with Image.open(image) as photo:
            photo.load();width,height=photo.size
        if fmt not in ('JPEG','PNG'):
            raise ValueError('Solo se admiten fotografías JPEG o PNG reales')
        with self.lock():
            if any(r['image_sha256']==digest for r in self.records('samples')):
                raise ValueError('Fotografía duplicada SHA-256')
            identity=str(uuid4());relative='images/originals/'+identity+('.jpg' if fmt=='JPEG' else '.png')
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as handle:handle.write(data)
            if sha(path)!=digest:
                raise ValueError('La copia no conserva el hash')
            result={'sample_id':identity,'bottle_id':bottle_id,'session_id':session_id,
                    'captured_at':captured_at,'registered_at_utc':now(),'origin':'OWN_REAL_CAPTURE',
                    'capture_operator':session['operator'],'original_filename':image.name,
                    'source_path_at_registration':str(image),'image':relative,'image_sha256':digest,
                    'width':width,'height':height,'format':fmt,'split':'UNASSIGNED',
                    'quality_warnings':['REVIEW_RESOLUTION'] if min(width,height)<224 else [],
                    'license':'INTERNAL_NOT_PUBLICLY_LICENSED'}
            write_new(self.root/'metadata/samples'/(identity+'.json'),result)
        return result

    def history(self, sample_id):
        uid(sample_id)
        result=[];previous=None
        for path in sorted((self.root/'reviews'/sample_id).glob('*.jsonl')):
            content=rows(path)
            if len(content)!=1:
                raise ValueError('Cada revisión inmutable contiene exactamente un registro')
            item=content[0]
            if item['sample_id']!=sample_id or item['parent_sha256']!=previous or item['revision']!=len(result)+1:
                raise ValueError('Cadena de revisiones inconsistente')
            check_annotation(item['annotation']);required(item['author']);timestamp(item['recorded_at_utc'])
            if item['role']=='REVIEWER':
                if not result or result[-1]['role']!='ANNOTATOR' or result[-1]['author']==item['author']:
                    raise ValueError('La revisión requiere anotador independiente')
            elif item['role']!='ANNOTATOR':
                raise ValueError('Rol de revisión inválido')
            result.append(item);previous=sha(path)
        return result,previous

    def annotate(self, sample_id, annotation, author, reviewer=False):
        self.record('samples',sample_id);check_annotation(annotation);required(author)
        with self.lock():
            history, parent=self.history(sample_id)
            if reviewer and (not history or history[-1]['role']!='ANNOTATOR' or history[-1]['author']==author):
                raise ValueError('Revisor distinto del anotador; requiere anotación previa')
            item={'sample_id':sample_id,'revision':len(history)+1,'parent_sha256':parent,
                  'author':author,'role':'REVIEWER' if reviewer else 'ANNOTATOR',
                  'recorded_at_utc':now(),'annotation':annotation}
            path=self.root/'reviews'/sample_id/(f"{len(history)+1:06d}.jsonl")
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('x',encoding='utf-8') as handle:handle.write(json.dumps(item,ensure_ascii=False)+'\n')
        return item

    def components(self):
        samples=self.records('samples');parent={}
        def find(key):
            parent.setdefault(key,key)
            if parent[key]!=key:parent[key]=find(parent[key])
            return parent[key]
        for sample in samples:
            a=find('bottle:'+sample['bottle_id']);b=find('session:'+sample['session_id']);parent[b]=a
        grouped={}
        for sample in samples:grouped.setdefault(find('bottle:'+sample['bottle_id']),[]).append(sample['sample_id'])
        return [sorted(ids) for ids in grouped.values()]

    def propose(self, seed=20261115):
        groups=self.components();sizes={k:0 for k in SPLITS};assignments={};targets=dict(zip(SPLITS,(.7,.15,.15)))
        total=sum(map(len,groups))
        for index,group in enumerate(sorted(groups,key=lambda g:(-len(g),hashlib.sha256((str(seed)+','.join(g)).encode()).hexdigest()))):
            split=SPLITS[index] if len(groups)>=3 and index<3 else max(SPLITS,key=lambda s:(targets[s]*total-sizes[s],-SPLITS.index(s)))
            for identity in group:assignments[identity]=split
            sizes[split]+=len(group)
        return {'proposal_only':True,'seed':seed,'assignments':assignments,'components':groups,
                'images_per_partition':sizes,'warning':'No implica aprobación para entrenar; no dividir botellas ni sesiones'}

    def validate(self, proposal=None):
        samples=self.records('samples');ids=set();hashes=set();forbidden=self.forbidden_hashes();counts={k:Counter() for k in LABELS};reviewed={k:Counter() for k in LABELS}
        warnings=[];review_count=0;regions={'body':Counter(),'cap':Counter()};positive_bottles={k:set() for k in LABELS};positive_sessions={k:set() for k in LABELS}
        for row in samples:
            identity=uid(row['sample_id'])
            if identity in ids or row['image_sha256'] in hashes:raise ValueError('Muestra o fotografía duplicada')
            ids.add(identity);hashes.add(row['image_sha256'])
            if row['image_sha256'] in forbidden:raise ValueError('Procedencia incompatible: público o v001')
            self.record('sessions',row['session_id']);self.record('bottles',row['bottle_id']);timestamp(row['captured_at'])
            if row['origin']!='OWN_REAL_CAPTURE' or row['split']!='UNASSIGNED':raise ValueError('Origen o partición base modificados')
            path=(self.root/row['image']).resolve()
            if not path.is_relative_to(self.root/'images/originals') or sha(path)!=row['image_sha256']:raise ValueError('Ruta o hash de imagen alterado')
            with Image.open(path) as photo:
                photo.load()
                if photo.size!=(row['width'],row['height']) or photo.format!=row['format']:raise ValueError('Formato/dimensiones incorrectos')
            history,_=self.history(identity);annotation=history[-1]['annotation'] if history else blank_annotation()
            check_annotation(annotation)
            is_reviewed=bool(history and history[-1]['role']=='REVIEWER');review_count+=is_reviewed
            for key,value in annotation['labels'].items():
                state='unknown' if value is None else 'positive' if value==1 else 'negative';counts[key][state]+=1
                if is_reviewed:reviewed[key][state]+=1
                if is_reviewed and value==1:
                    positive_bottles[key].add(row['bottle_id']);positive_sessions[key].add(row['session_id'])
            for region,value in annotation['evaluable'].items():regions[region]['unknown' if value is None else 'evaluable' if value else 'not_evaluable']+=1
        expected_paths={(self.root/r['image']).resolve() for r in samples}
        orphans=[str(p.relative_to(self.root)) for p in (self.root/'images/originals').glob('*') if p.is_file() and p.resolve() not in expected_paths]
        if orphans:raise ValueError('Fotografías sin metadatos; recuperar sin eliminar: '+str(orphans))
        for directory in (self.root/'reviews').glob('*'):
            if directory.is_dir() and directory.name not in ids:raise ValueError('Revisiones sin muestra registrada')
        if proposal is not None:
            assigned=proposal['assignments']
            if set(assigned)!=ids or any(v not in SPLITS for v in assigned.values()):raise ValueError('Partición incompleta/inválida')
            for group in self.components():
                if len({assigned[i] for i in group})!=1:raise ValueError('Fuga entre botella/sesión')
        if not samples:warnings.append('Dataset vacío: estructura preparada, no listo para entrenamiento')
        if len(self.components())<3:warnings.append('Menos de tres componentes independientes: no se pueden representar las tres particiones')
        if review_count<len(samples):warnings.append('Hay muestras sin revisión independiente vigente')
        return {'dataset_id':'epp-own-v002','images':len(samples),'bottles':len({r['bottle_id'] for r in samples}),
                'sessions':len({r['session_id'] for r in samples}),'origin_components':len(self.components()),
                'hashes_verified':len(hashes),'independently_reviewed_images':review_count,
                'latest_labels':{k:{s:counts[k][s] for s in ('positive','negative','unknown')} for k in LABELS},
                'reviewed_labels':{k:{s:reviewed[k][s] for s in ('positive','negative','unknown')} for k in LABELS},
                'bottles_with_reviewed_positive_evidence':{k:len(v) for k,v in positive_bottles.items()},
                'sessions_with_reviewed_positive_evidence':{k:len(v) for k,v in positive_sessions.items()},
                'evaluability':{k:dict(v) for k,v in regions.items()},'warnings':warnings,'training_authorized':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    session=sub.add_parser('session')
    for name in ('operator','product','lot','stage','camera','position','lighting'):session.add_argument('--'+name,required=True)
    session.add_argument('--cap-required',choices=('yes','no'),required=True)
    bottle=sub.add_parser('bottle');bottle.add_argument('--reference',required=True)
    capture=sub.add_parser('capture')
    for name in ('image','session','bottle','captured-at'):capture.add_argument('--'+name,required=True)
    capture.add_argument('--own-capture',action='store_true')
    for name in ('annotate','review'):
        part=sub.add_parser(name)
        for key in ('sample','file','author'):part.add_argument('--'+key,required=True)
    for name in ('validate','coverage'):
        part=sub.add_parser(name);part.add_argument('--proposal',type=Path);part.add_argument('--output',type=Path)
    split=sub.add_parser('propose-splits');split.add_argument('--seed',type=int,default=20261115);split.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dataset=Dataset()
    if args.command=='session':result=dataset.session(args.operator,args.product,args.lot,args.stage,args.camera,args.position,args.lighting,args.cap_required=='yes')
    elif args.command=='bottle':result=dataset.bottle(args.reference)
    elif args.command=='capture':result=dataset.capture(args.image,args.session,args.bottle,args.captured_at,args.own_capture)
    elif args.command in ('annotate','review'):result=dataset.annotate(args.sample,read(args.file),args.author,args.command=='review')
    elif args.command=='propose-splits':
        dataset.validate();result=dataset.propose(args.seed)
        output=args.output.resolve()
        if not output.is_relative_to(BASE/'splits'):raise ValueError('Guardar propuestas únicamente en v002/splits')
        write_new(output,result)
    else:
        result=dataset.validate(read(args.proposal) if args.proposal else None)
        if args.output:
            output=args.output.resolve()
            if not output.is_relative_to(BASE/'reports'):raise ValueError('Guardar informes únicamente en v002/reports')
            write_new(output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as error:
        print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

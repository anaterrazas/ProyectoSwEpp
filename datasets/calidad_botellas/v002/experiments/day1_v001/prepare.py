"""Preparación experimental trazable, sin modificar fuentes ni inventar etiquetas."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]
sys.path.insert(0,str(ROOT))
from ml.calidad_botellas.audit_visual import fingerprints
from PIL import Image
import cv2
import numpy as np

LABELS=('RAYADURA','DEFORMACION','TAPA_DEFECTUOSA')


def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,data):
    path=BASE/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def main():
    selection=ROOT/'datasets/publicos_calidad_botellas/selections/pretrain_v001'
    human=rows(selection/'human_review_v001.jsonl')
    source=rows(ROOT/'datasets/publicos_calidad_botellas/imports/roboflow_caps_v26_001/samples.public.jsonl')
    source_by_id={r['sample_id']:r for r in source}
    proof=json.loads((selection/'human_review_v001.provenance.json').read_text(encoding='utf-8'))
    if sha(selection/'human_review_v001.jsonl')!=proof['output_sha256']:raise ValueError('Capa humana modificada')
    selected=[]
    for record in human:
        value=record['labels']['TAPA_DEFECTUOSA']
        if not record['source'].startswith('roboflow') or value is None:continue
        if record['status']!='CONFIRMED_PARTIAL':raise ValueError('No promover decisiones pendientes')
        image=(selection/record['original_url']).resolve()
        if sha(image)!=record['expected_hash']:raise ValueError('Hash alterado')
        original=source_by_id[record['sample_id']]
        if original['license']!='CC-BY-4.0':raise ValueError('Licencia no aprobada')
        selected.append({'sample_id':record['sample_id'],'path':str(image.relative_to(ROOT)),
                         'expected_hash':record['expected_hash'],'source':record['source'],
                         'group_id':record['group_id'],'partition':record['proposed_partition'],
                         'labels':dict(record['labels']),'target':value,'license':record['license'],
                         'license_url':record['license_url'],'source_url':record['source_url'],
                         'creators':record['creators'],'original_classes':record['classes'],
                         'annotation_evidence_sha256':proof['output_sha256'],
                         'scope':'scene-level cap inspection; not whole-container conformity'})
    if len(selected)!=50 or len({r['sample_id'] for r in selected})!=50:raise ValueError('Selección no coincide')
    groups={}
    for r in selected:
        if r['group_id'] in groups and groups[r['group_id']]!=r['partition']:raise ValueError('Fuga de grupo')
        groups[r['group_id']]=r['partition']
    if len({r['expected_hash'] for r in selected})!=50:raise ValueError('Duplicados exactos')
    stats={part:{'images':len(sub),'positive':sum(r['target']==1 for r in sub),'negative':sum(r['target']==0 for r in sub),
                 'origin_groups':len({r['group_id'] for r in sub})}
           for part in ('train','validation','test') for sub in [[r for r in selected if r['partition']==part]]}
    # Umbral de viabilidad de ingeniería, fijado antes de ajustar el modelo; no garantía estadística.
    viable=stats['train']['images']>=10 and stats['test']['images']>=10 and all(stats[p][c]>=5 for p in ('train','test') for c in ('positive','negative'))
    if not viable:raise ValueError('Cobertura insuficiente incluso para el ensayo mínimo')
    excluded=[]
    inventory=json.loads((BASE/'inspection/additional_inventory.json').read_text(encoding='utf-8'))
    descriptions={
      1:'Imagen de producto sobre fondo azul; origen no acreditado; no inferir conformidad.',
      2:'Marca Getty Images / crédito CostinT visible.',
      3:'Marca Getty Images / crédito TokenPhoto visible; botella abierta no prueba defecto de tapa en fabricación.',
      4:'Marca Getty Images / crédito ALEAIMAGE visible; elemento de interfaz superpuesto.',
      5:'Imagen pequeña de botella etiquetada; procedencia desconocida y detalle reducido.',
      6:'Imagen pequeña de producto; no hay licencia ni autor acreditados.',
      7:'Envase fuertemente aplastado; no se acredita si es posconsumo, manipulación o defecto de fabricación.',
      8:'Envase aplastado; origen y mecanismo del daño desconocidos.',
      9:'Envase aplastado con tapa separada; no acredita rechazo de fabricación ni etapa de tapado.',
      10:'Envase aplastado horizontal; pocos píxeles y mecanismo de deformación no acreditado.',
      11:'Envase aplastado; marca de agua tenue aparente en el centro, sin atribución verificable.',
      12:'Envase aplastado y reflejo de estudio; autor/licencia desconocidos.',
      13:'Envase aplastado con fondo de colores; origen y causa de deformación no acreditados.',
      14:'Imagen pequeña de producto sin tapa; ausencia de tapa no acredita defecto en una etapa desconocida.',
      15:'Imagen de recipiente grande; origen, derechos y anotaciones no acreditados.'}
    known_hashes=set()
    for path in (ROOT/'datasets/publicos_calidad_botellas/imports').glob('*/samples.public.jsonl'):
        known_hashes.update(r['image_sha256'] for r in rows(path))
    own=rows(ROOT/'datasets/calidad_botellas/v002/reports/fotos_preimport_v001/v002_fotos_preparacion.grouped_v002.jsonl')
    if Counter(r['bottle_id_proposal'] for r in own)!=Counter({'BOT-001':5,'BOT-002':2,'BOT-004':2,'BOT-005':2}):raise ValueError('Agrupación física incorrecta')
    with zipfile.ZipFile('C:/Users/Usuario/Downloads/fotos.zip') as archive:
        for r in own:
            if hashlib.sha256(archive.read(r['source_path_in_archive'])).hexdigest()!=r['sha256']:raise ValueError('Hash propio alterado')
            known_hashes.add(r['sha256'])
            excluded.append({'sample_id':r['source_filename'],'source':'OWN_PREIMPORT','group_id':r['bottle_id_proposal'],
                             'labels_preserved':r['labels'],'reason':'Metadatos obligatorios incompletos; anotación preliminar, PET negativos sin evaluabilidad confirmada. No usar como evaluación independiente confirmada.'})
    visual=[]
    for n,r in enumerate(inventory,1):
        path=ROOT/r['inspection_copy']
        if sha(path)!=r['sha256']:raise ValueError('Copia de inspección modificada')
        with Image.open(path) as im:gray=np.array(im.convert('L'))
        phash,dhash=fingerprints(gray)
        visual.append((r['inspection_id'],phash,dhash))
        excluded.append({**r,'excluded':True,'visible_watermark':True if n in (2,3,4) else None,
                         'possible_faint_watermark':n==11,'duplicate_known_sha256':r['sha256'] in known_hashes,
                         'visual_observation':descriptions[n],'reason':'Licencia y procedencia no acreditadas; sin anotación humana válida para las clases objetivo'})
    pairs=[{'left':a,'right':b,'phash_distance':(p^q).bit_count(),'dhash_distance':(d^e).bit_count()}
           for i,(a,p,d) in enumerate(visual) for b,q,e in visual[i+1:] if (p^q).bit_count()<=6 and (d^e).bit_count()<=8]
    manifest=BASE/'dataset/manifest.jsonl';manifest.parent.mkdir(parents=True,exist_ok=True)
    with manifest.open('x',encoding='utf-8') as f:
        for r in selected:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    write('dataset/plan.json',{'task':'binary_experimental_cap_scene_classification','available_models':['TAPA_DEFECTUOSA'],
         'unavailable_models':{'RAYADURA':'Sin negativos humanos válidos de entrenamiento','DEFORMACION':'Sin negativos humanos válidos de entrenamiento'},
         'statistics':stats,'threshold_fixed_before_training':.5,'input_size':96,'epochs_fixed':120,'seed':20261116,
         'training_from_scratch':True,'architecture':'TinyCapCNN','validation_usage':'descriptive_only_no_threshold_tuning_no_checkpoint_selection',
         'evaluation_warning':'Test separado por grupo respecto al entrenamiento; un solo grupo y ya expuesto a revisión humana histórica. No test industrial ciego.',
         'not_production_ready':True,'manifest_sha256':sha(manifest)})
    write('inspection/exclusions.json',excluded)
    write('inspection/visual_candidates_additional.json',{'pairs':pairs,'exact_duplicate_groups':[[r['inspection_id'] for r in inventory if r['sha256']==h] for h,c in Counter(r['sha256'] for r in inventory).items() if c>1],
          'method':'pHash<=6 and dHash<=8; candidate evidence only, no physical identity inference'})
    write('inspection/input_hashes.json',{'human_review':proof['output_sha256'],'additional_zip':sha(Path('C:/Users/Usuario/Downloads/botellas (2).zip')),
         'own_zip':sha(Path('C:/Users/Usuario/Downloads/fotos.zip')),'own_grouped_manifest':sha(ROOT/'datasets/calidad_botellas/v002/reports/fotos_preimport_v001/v002_fotos_preparacion.grouped_v002.jsonl')})
    print(json.dumps({'selected':len(selected),'statistics':stats,'additional_excluded':15,'own_preimport_excluded':11,'models':['TAPA_DEFECTUOSA']}))


if __name__=='__main__':main()

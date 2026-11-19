"""Clasificador experimental de escena de tapa. Nunca infiere otras clases."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image,ImageOps
import torch
from torch import nn

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]


class TinyCapCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.Sequential(nn.Conv2d(3,12,5,padding=2),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(12,24,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(24,32,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((3,3)),
            nn.Flatten(),nn.Linear(288,1))
    def forward(self,x):return self.layers(x).flatten()


def tensor(image):
    # Mismo preprocesado en entrenamiento, evaluación, fotos y video. Sin cajas de etiqueta.
    image=ImageOps.pad(ImageOps.exif_transpose(image).convert('RGB'),(96,96),color=(0,0,0))
    return torch.from_numpy(np.asarray(image,dtype=np.float32).copy().transpose(2,0,1)/255.)


def metrics(labels,probabilities):
    labels=np.asarray(labels,dtype=int);prob=np.asarray(probabilities,dtype=float);pred=prob>=.5
    tp=int(np.sum((labels==1)&pred));tn=int(np.sum((labels==0)&~pred));fp=int(np.sum((labels==0)&pred));fn=int(np.sum((labels==1)&~pred))
    def div(a,b):return a/b if b else None
    precision=div(tp,tp+fp);recall=div(tp,tp+fn)
    return {'n':len(labels),'positive':int(sum(labels==1)),'negative':int(sum(labels==0)),
            'tp':tp,'tn':tn,'fp':fp,'fn':fn,'accuracy':div(tp+tn,len(labels)),
            'precision':precision,'recall':recall,'specificity':div(tn,tn+fp),'false_negative_rate':div(fn,tp+fn),
            'f1':div(2*tp,2*tp+fp+fn),'threshold':.5,
            'majority_baseline_accuracy':div(max(sum(labels==1),sum(labels==0)),len(labels)),
            'warning':'Descriptivo por imagen; vistas correlacionadas, no unidades físicas independientes.'}


def load_model(checkpoint=None):
    path=Path(checkpoint) if checkpoint else BASE/'artifacts/cap_model.pt'
    model=TinyCapCNN()
    model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True));model.eval()
    return model


def predict(model,image):
    result={'RAYADURA':{'available':False,'score':None,'prediction':None,'reason':'Sin modelo: faltan negativos válidos'},
            'DEFORMACION':{'available':False,'score':None,'prediction':None,'reason':'Sin modelo: faltan negativos válidos'}}
    if model is None:
        result['TAPA_DEFECTUOSA']={'available':False,'score':None,'prediction':None,'reason':'Modelo no disponible'}
    else:
        with torch.no_grad():p=float(torch.sigmoid(model(tensor(image).unsqueeze(0)))[0])
        result['TAPA_DEFECTUOSA']={'available':True,'score':p,'prediction':int(p>=.5),
          'score_type':'sigmoid_not_calibrated_probability','scope':'experimental cap scene only',
          'negative_is_global_conformity':False}
    return result


def train():
    output=BASE/'artifacts'
    if output.exists():raise FileExistsError('No sobrescribir el modelo/mediciones de un ensayo anterior')
    plan=json.loads((BASE/'dataset/plan.json').read_text(encoding='utf-8'))
    manifest=BASE/'dataset/manifest.jsonl'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=plan['manifest_sha256']:raise ValueError('Manifiesto cambiado')
    rows=[json.loads(s) for s in manifest.read_text(encoding='utf-8').splitlines()]
    groups={}
    for r in rows:
        path=ROOT/r['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=r['expected_hash']:raise ValueError('Imagen cambiada')
        if r['labels']['TAPA_DEFECTUOSA'] not in (0,1):raise ValueError('No entrenar desconocidos')
        if r['group_id'] in groups and groups[r['group_id']]!=r['partition']:raise ValueError('Fuga de origen')
        groups[r['group_id']]=r['partition']
    torch.set_num_threads(2);torch.manual_seed(plan['seed']);np.random.seed(plan['seed'])
    torch.use_deterministic_algorithms(True)
    tensors=[]
    for r in rows:
        with Image.open(ROOT/r['path']) as im:tensors.append(tensor(im))
    x=torch.stack(tensors);y=torch.tensor([r['target'] for r in rows],dtype=torch.float32)
    train_idx=[i for i,r in enumerate(rows) if r['partition']=='train']
    if len(set(int(y[i]) for i in train_idx))!=2:raise ValueError('Se requieren ambas clases en train')
    model=TinyCapCNN();optimizer=torch.optim.Adam(model.parameters(),lr=.003)
    pos=float(y[train_idx].sum());neg=len(train_idx)-pos
    loss_fn=nn.BCEWithLogitsLoss(pos_weight=torch.tensor(neg/pos))
    start=time.perf_counter();history=[]
    model.train()
    for epoch in range(plan['epochs_fixed']):
        optimizer.zero_grad();loss=loss_fn(model(x[train_idx]),y[train_idx]);loss.backward();optimizer.step()
        history.append({'epoch':epoch+1,'training_loss':float(loss.detach())})
    seconds=time.perf_counter()-start;model.eval()
    with torch.no_grad():scores=torch.sigmoid(model(x)).numpy().tolist()
    partitions={p:metrics([r['target'] for r in rows if r['partition']==p],[s for r,s in zip(rows,scores) if r['partition']==p]) for p in ('train','validation','test')}
    predictions=[{**r,'score':score,'prediction':int(score>=.5)} for r,score in zip(rows,scores)]
    output.mkdir()
    torch.save(model.state_dict(),output/'cap_model.pt')
    summary={'task':'TAPA_DEFECTUOSA_ONLY','partitions':partitions,'training_seconds':seconds,
             'epochs_fixed':plan['epochs_fixed'],'threshold_fixed':.5,'seed':plan['seed'],'optimizer':'Adam lr=.003',
             'architecture':'TinyCapCNN from scratch; no downloaded weights','input_size':96,
             'torch_version':str(torch.__version__),'manifest_sha256':plan['manifest_sha256'],
             'checkpoint_sha256':hashlib.sha256((output/'cap_model.pt').read_bytes()).hexdigest(),
             'validation_missing_negative_class':True,'calibrated':False,
             'test_groups':1,'test_blind_to_historical_review':False,'production_ready':False,
             'confidence_intervals_not_computed_reason':'Solo un grupo de origen en test; independencia física no acreditada'}
    for name,value in [('metrics.json',summary),('predictions.json',predictions),('training_history.json',history)]:
        with (output/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=True,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['train']);parser.parse_args();train()

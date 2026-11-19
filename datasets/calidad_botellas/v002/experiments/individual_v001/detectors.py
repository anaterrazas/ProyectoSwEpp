"""Adaptadores de detectores preentrenados reales; no entrenan ni crean cajas manuales."""
from pathlib import Path
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]


class Detector:
    def __init__(self,name='yolo11s640',confidence=.3):
        self.name=name;self.confidence=confidence
        torch.set_num_threads(2)
        if name.startswith('yolo'):
            self.size=int(name.split('s')[-1]) if name.startswith('yolo11s') else int(name.split('n')[-1])
            self.path=BASE/'weights/yolo11s.pt' if name.startswith('yolo11s') else ROOT/'yolo11n.pt'
            self.model=YOLO(str(self.path));self.label=39
        elif name=='fasterrcnn320':
            from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_320_fpn,FasterRCNN_MobileNet_V3_Large_320_FPN_Weights
            metadata=FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT.meta
            self.path=BASE/'weights/fasterrcnn_mobilenet_v3_large_320_fpn-907ea3f9.pth'
            self.model=fasterrcnn_mobilenet_v3_large_320_fpn(weights=None,weights_backbone=None)
            self.model.load_state_dict(torch.load(self.path,map_location='cpu',weights_only=True));self.model.eval()
            self.label=metadata['categories'].index('bottle')
        else:raise ValueError('Detector no disponible: '+name)

    def detect(self,frame):
        start=time.perf_counter()
        if self.name.startswith('yolo'):
            result=self.model.predict(frame,classes=[self.label],conf=self.confidence,imgsz=self.size,
                                      save=False,device='cpu',verbose=False)[0]
            detections=[{'bbox_xyxy':box,'score':score,'label':'bottle','class_id':self.label}
                        for box,score in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
        else:
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            tensor=torch.from_numpy(rgb.copy()).permute(2,0,1).float()/255.
            with torch.no_grad():result=self.model([tensor])[0]
            detections=[{'bbox_xyxy':box.tolist(),'score':float(score),'label':'bottle','class_id':self.label}
                        for box,score,label in zip(result['boxes'],result['scores'],result['labels'])
                        if int(label)==self.label and float(score)>=self.confidence]
        return detections,time.perf_counter()-start


def draw(frame,detections,title):
    image=frame.copy()
    for number,d in enumerate(detections):
        x1,y1,x2,y2=map(round,d['bbox_xyxy'])
        cv2.rectangle(image,(x1,y1),(x2,y2),(0,255,0),3)
        cv2.putText(image,f"obs {number} bottle {d['score']:.2f}",(x1,max(20,y1+20)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,0),3)
        cv2.putText(image,f"obs {number} bottle {d['score']:.2f}",(x1,max(20,y1+20)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,0),1)
    cv2.putText(image,title,(10,image.shape[0]-20),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2)
    return image

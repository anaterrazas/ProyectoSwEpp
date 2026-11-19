"""Notas de inspección visual del agente, no adjudicación ni nuevas etiquetas GT."""
from collections import Counter
from .evaluacion_epp33 import leer, guardar

CASCO = {
 1:'Casco cercano y nítido; la propuesta azul excede la extensión de la referencia. IoU insuficiente, no ausencia del objeto.',
 2:'Casco posterior del trabajador del fondo; la propuesta incluye más cabeza/cuello que la referencia del casco.',
 3:'Casco parcialmente visible del fondo; altura proyectada reducida y ausencia de propuesta solapada. Revisar resolución sin asumir oclusión total.',
 4:'Casco posterior/parcial; la propuesta se prolonga hacia cara/cuello y falla el IoU.',
 5:'Casco posterior/parcial; referencia estrecha frente a propuesta que incorpora cabeza y hombros.',
 6:'Casco grande en primer plano sin propuesta. Revisar además el recorte por borde superior; no se justifica atribuir la omisión a objeto pequeño.',
 7:'Trabajador muy lejano del extremo derecho; casco proyectado a 11,5 px de dimensión mínima. Caso prioritario de tamaño/resolución.',
 8:'Casco lateral cercano con propuesta demasiado extensa hacia cabeza/rostro; desacuerdo geométrico.',
 9:'Casco lateral grande y visible sin propuesta en la región; no hay evidencia de que el único problema sea tamaño o luz.',
10:'Casco lateral/inclinado del primer plano sin propuesta solapada; textura y borde visibles.',
11:'Casco frontal del fondo con propuesta que incluye cara/cuello; IoU insuficiente.',
12:'Casco frontal del trabajador del fondo visible; falta propuesta en su región.',
13:'Casco frontal del fondo, borde visible; no hay propuesta positiva solapada.',
14:'Casco frontal del fondo con referencia visible; sin propuesta en su región.',
15:'Casco lateral grande del primer plano; omisión de propuesta, no máscara de incertidumbre.',
16:'Casco lateral inclinado del primer plano; propuesta que engloba más cabeza/cuello que el casco de referencia.',
17:'Casco frontal del fondo nítido en el crop; no hay propuesta positiva en esa región.',
18:'Casco frontal del fondo e inclinación leve; omisión sin evidencia de clipping de iluminación.',
19:'Casco lateral inclinado del primer plano; borde y color distinguibles, sin propuesta solapada.',
20:'Casco frontal del fondo; no hay propuesta solapada. No corregir la referencia automáticamente para favorecer al modelo.',
}
PERSONA = {
 1:'La caja predicha abarca regiones de dos trabajadores cercanos. Revisar separación de instancias y convención de caja humana visible.',
 2:'Predicción extensa sobre trabajador posterior; la referencia es más compacta y las extremidades de vecinos se superponen. Adjudicar extensión visible.',
 3:'Persona real del primer plano; la predicción incluye más cuerpo/brazos que la referencia. IoU 0,490: no es una persona ficticia.',
 4:'Caja estrecha sobre brazo/hombro del trabajador agachado; fragmentación o duplicado de una persona anotada con caja mayor.',
 5:'Persona con prenda rosada visible al fondo, parcialmente tapada por el primer plano, sin referencia equivalente. Adjudicar exhaustividad/alcance de PERSONA.',
 6:'Persona real del primer plano; diferencia de extensión del cuerpo y brazos, IoU 0,499. Mantener el umbral y revisar convención.',
 7:'Persona del primer plano con brazo extendido; predicción y referencia usan extensiones diferentes de la instancia.',
 8:'Motociclista visible al fondo, sin caja humana equivalente. No confirmar fallo semántico de detección solo por su FP contra el archivo actual.',
 9:'Persona del primer plano con brazos hacia delante; diferencia de extensión respecto a la referencia del torso/cuerpo.',
10:'Motociclista visible al fondo sin caja humana equivalente; alcance de la referencia requiere adjudicación.',
11:'Trabajador lejano y recortado por borde derecho, con casco visible, sin caja humana en este frame; revisar exhaustividad y ROI objetivo.',
12:'Persona real inclinada con manos extendidas; predicción más extensa que la referencia. Error geométrico contra la caja actual.',
13:'Motociclista visible al fondo sin referencia equivalente; no relabelar ni excluirlo automáticamente.',
14:'Persona del primer plano con brazos adelantados; límites visibles usados por anotación y detector no coinciden.',
15:'Persona del primer plano frontal/lateral; diferencia de extensión de caja, no confusión de clase acreditada.',
16:'Persona del primer plano con brazos estirados; la caja predicha cubre una región mayor que la referencia compacta.',
17:'Persona inclinada del primer plano; diferencia de caja frente a la referencia, con otra persona cerca.',
18:'Trabajador derecho parcialmente visible; predicción engloba más torso/extremidades que la caja humana.',
19:'Persona inclinada del primer plano; desacuerdo de extensión frente a la referencia del cuerpo.',
}


def completar(salida):
    casos=leer(salida/'casos_auditoria.json')
    plegados={3,4,7,8,9,14,15,18,19,21,22}
    izquierda={2,5,6,10,13,16}
    frontales={1,11,12,17,20,23}
    abiertos={27,28,30,31,32,34,37,39,44}
    espalda={24,25,26,29,42,43}
    muro={33,35,36,38,40,41}
    for c in casos:
        n=int(c['id'].split('_')[-1]);cl=c['clase'];cats=[];factores={}
        for factor in ['oclusion','tamano_objeto','desenfoque','iluminacion','perspectiva','caja_humana_incorrecta','caja_prediccion_incorrecta','confusion_clases']:
            factores[factor]={'estado':'NO_ACREDITADO','evidencia':'No se confirmó causalidad en este caso.'}
        if cl=='CHALECO':
            if n in plegados:
                nota='Chaleco de primer plano visto de lado/espalda, plegado sobre hombro y torso al inclinarse; parte de la prenda queda autooculta. No hay propuesta positiva en la zona.'
                cats+=['PERSPECTIVA','OCLUSION_VISUAL_PARCIAL','FALTA_PROPUESTA_POSITIVA']
                factores['oclusion']={'estado':'OBSERVACION_VISUAL','evidencia':'Postura, pliegues y brazo ocultan parte de la prenda; la porción anotada sigue siendo visible.'}
            elif n in izquierda:
                nota='Chaleco del trabajador izquierdo, vista lateral y prenda parcialmente tapada por brazo/encuadre; bandas reflectivas visibles. No se explica por objeto pequeño.'
                cats+=['PERSPECTIVA','OCLUSION_VISUAL_PARCIAL','FALTA_PROPUESTA_POSITIVA']
                factores['oclusion']={'estado':'OBSERVACION_VISUAL','evidencia':'Brazo/encuadre limitan la prenda completa, sin convertir presencia en ausencia.'}
            elif n in frontales:
                nota='Chaleco frontal del trabajador posterior visible en un área amplia. Omisión de propuesta; no hay evidencia suficiente para atribuirla a luz o tamaño.'
                cats+=['FALTA_PROPUESTA_POSITIVA']
            elif n in abiertos:
                nota='Chaleco abierto con paneles naranjas laterales alrededor de camisa clara; postura frontal/lateral. La caja humana contiene el conjunto de la prenda abierta. Revisar convención sin declararla incorrecta.'
                cats+=['PERSPECTIVA','CHALECO_ABIERTO','ADJUDICACION_CONVENCION_CAJA']
                factores['caja_humana_incorrecta']={'estado':'REQUIERE_ADJUDICACION_NO_ERROR_CONFIRMADO','evidencia':'Definir una caja del chaleco abierto completo frente a sus paneles separados; no se corrigió la referencia.'}
            elif n in espalda:
                nota='Chaleco naranja con bandas visibles, vista posterior/lateral del trabajador del fondo; no hay propuesta positiva que solape la referencia.'
                cats+=['PERSPECTIVA','FALTA_PROPUESTA_POSITIVA']
            elif n in muro:
                nota='Trabajador agachado detrás del muro; solo se ve una franja de espalda/chaleco. Revisar marca VISIBLE/PARCIAL y extensión visible. El objeto no queda automáticamente excluido de evaluación.'
                cats+=['OCLUSION_VISUAL_PARCIAL','PERSPECTIVA','ADJUDICACION_VISIBILIDAD']
                factores['oclusion']={'estado':'OBSERVACION_VISUAL','evidencia':'Muro/postura ocultan gran parte del torso.'}
                factores['caja_humana_incorrecta']={'estado':'REQUIERE_ADJUDICACION_NO_ERROR_CONFIRMADO','evidencia':'Algunas marcas VISIBLE describen solo una franja de una prenda mayor; revisar criterio de visibilidad.'}
            else:raise ValueError('Caso no inspeccionado.')
            c['prioridad']=4
            if n in (24,42):
                nota+=' Además, NO-Safety Vest se solapa con el chaleco humano PRESENTE (IoU >=0,68): conflicto de clase/estado a revisar, no alerta temporal adjudicada.'
                cats+=['CONFUSION_CLASE_ESTADO'];c['prioridad']=5
                factores['confusion_clases']={'estado':'CONFLICTO_CON_REFERENCIA_PRESENTE','evidencia':c['clases_alternativas']}
            factores['perspectiva']={'estado':'OBSERVACION_VISUAL_NO_CAUSAL','evidencia':'Vista/postura descrita en la nota individual; no demuestra causa única.'}
        elif cl=='CASCO':
            nota=CASCO[n];c['prioridad']=3
            if c['indicadores']['desacuerdo_localizacion']:
                cats+=['CAJA_PREDICHA_GEOMETRIA','ADJUDICACION_CONVENCION_CAJA'];c['prioridad']=4
                factores['caja_prediccion_incorrecta']={'estado':'DESACUERDO_GEOMETRICO_MEDIDO','evidencia':f"IoU {c['max_iou']:.4f} con referencia; propuesta incluye más cabeza/rostro que la carcasa."}
                factores['caja_humana_incorrecta']={'estado':'REQUIERE_ADJUDICACION_NO_ERROR_CONFIRMADO','evidencia':'Acordar casco visible frente a cabeza/cuello; no cambiar IoU ni cajas para favorecer el resultado.'}
            else:cats+=['FALTA_PROPUESTA_POSITIVA']
            if n in (2,3,4,5,11,12,13,14,17,18,20):cats+=['PERSPECTIVA_FONDO_FRONTAL_POSTERIOR']
            if n==7:
                cats+=['TAMANO_OBJETO'];c['prioridad']=4
                factores['tamano_objeto']={'estado':'MEDIDO','evidencia':'Dimensión mínima proyectada 11,5 px a entrada 640.'}
            if n==6:
                cats+=['ADJUDICACION_RECORTE_BORDE']
        else:
            nota=PERSONA[n];c['prioridad']=4
            if n in (5,8,10,11,13):
                cats+=['REFERENCIA_INCOMPLETA_O_ALCANCE_AMBIGUO'];c['prioridad']=5
                factores['caja_humana_incorrecta']={'estado':'REQUIERE_ADJUDICACION_DE_EXHAUSTIVIDAD','evidencia':'Persona visible sin caja equivalente; puede ser un alcance de ROI/trabajador no documentado.'}
            elif n==4:
                cats+=['CAJA_PREDICHA_FRAGMENTO','OCLUSION_VISUAL_PARCIAL']
                factores['caja_prediccion_incorrecta']={'estado':'HIPOTESIS_VISUAL','evidencia':'Caja sobre fragmento de brazo/hombro de una persona mayor.'}
                factores['oclusion']={'estado':'OBSERVACION_VISUAL','evidencia':'Cuerpo doblado y parcialmente oculto por otros objetos/personas.'}
            else:
                cats+=['CAJA_PREDICHA_GEOMETRIA','ADJUDICACION_CONVENCION_CAJA']
                factores['caja_prediccion_incorrecta']={'estado':'DESACUERDO_GEOMETRICO_MEDIDO','evidencia':f"IoU máximo {c['max_iou']:.4f}; la instancia parece real, pero los límites no satisfacen 0,50."}
                factores['caja_humana_incorrecta']={'estado':'REQUIERE_ADJUDICACION_NO_ERROR_CONFIRMADO','evidencia':'Comparar extensión de brazos/cuerpo visible con la predicción; no se determina automáticamente quién tiene la caja correcta.'}
        for factor,flag in [('desenfoque','aviso_desenfoque_roi'),('iluminacion','aviso_iluminacion')]:
            factores[factor]={'estado':'SIN_AVISO_TECNICO_NO_DESCARTA_PROBLEMA','evidencia':{'aviso':c['indicadores'][flag],
                'laplaciano':c['laplaciano_roi_normalizada_256'],'gris_medio':c['gris_medio_roi'],'clip_oscuro':c['pixeles_oscuros'],'clip_claro':c['pixeles_saturados']}}
        c['categorias_auditoria']=cats;c['evaluacion_factores']=factores
        c['observacion_visual_agente']=f"{c['id']} ({c['sample_id']}): "+nota
        c['naturaleza_revision']='Inspección visual del agente y medidas técnicas; no segunda adjudicación humana.'
    (salida/'casos_auditoria.json').write_text(__import__('json').dumps(casos,ensure_ascii=False,indent=2),encoding='utf-8')
    guardar(salida/'resumen_auditoria.json',{'casos':len(casos),'por_clase':dict(Counter(c['clase'] for c in casos)),
        'categorias_solapadas_no_sumar_como_casos':dict(Counter(k for c in casos for k in c['categorias_auditoria'])),
        'revision_independiente':'PENDIENTE','etiquetas_originales_modificadas':False})


if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);args=p.parse_args();completar(args.salida)

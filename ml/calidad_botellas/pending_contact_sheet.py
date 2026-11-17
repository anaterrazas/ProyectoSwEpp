"""Hoja local de pendientes; no decide etiquetas ni modifica entradas."""
from collections import Counter
from copy import deepcopy
from html import escape
import json
from pathlib import Path

from .consolidate_review import digest, indexed, read_rows

BASE = Path(__file__).resolve().parents[2] / 'datasets/publicos_calidad_botellas/selections/pretrain_v001'
SOURCES = ('human_review_v001.jsonl', 'human_review_v001.report.md',
           'human_review_v001.coverage.json', 'human_review_v001.provenance.json')
OUTPUTS = ('human_review_v001.pending_contact_sheet.html',
           'human_review_v001.pending_decisions.jsonl')


def pending_records(directory):
    directory = Path(directory).resolve()
    rows = read_rows(directory / SOURCES[0])
    indexed(rows)
    coverage = json.loads((directory / SOURCES[2]).read_text(encoding='utf-8'))
    provenance = json.loads((directory / SOURCES[3]).read_text(encoding='utf-8'))
    report = (directory / SOURCES[1]).read_text(encoding='utf-8')
    if digest(directory / SOURCES[0]) != provenance['output_sha256']:
        raise ValueError('Hash de la revisión consolidada alterado')
    for name, expected in provenance['input_sha256'].items():
        if digest(directory / name) != expected:
            raise ValueError('Entrada de procedencia alterada: ' + name)
    pending = [r for r in rows if r['status'] == 'PENDING']
    expected = indexed(coverage['pending'])
    if len(pending) != 9 or {r['sample_id'] for r in pending} != set(expected):
        raise ValueError('No coinciden los nueve pendientes con cobertura')
    # El informe anterior delimita explícitamente su lista de pendientes.
    section = report.split('## Pendientes de confirmación (9)\n', 1)[1].split('\n## ', 1)[0]
    report_ids = [line.split(' — ', 1)[0][2:] for line in section.splitlines() if line.startswith('- ')]
    if len(report_ids) != 9 or set(report_ids) != set(expected):
        raise ValueError('Lista de pendientes del informe inconsistente')
    counts = Counter('detail' if r['review_reason'].endswith('ONLY_SMALL_TARGET_REGIONS_NEEDS_DETAIL') else 'framing' for r in pending)
    if counts != {'detail': 2, 'framing': 7}:
        raise ValueError('Distribución de motivos inesperada')
    imports = (directory.parent.parent / 'imports').resolve()
    for row in pending:
        if any(row[k] != expected[row['sample_id']][k] for k in ('expected_hash', 'file_name', 'review_reason')):
            raise ValueError('Cobertura contradictoria')
        image = (directory / row['original_url']).resolve()
        if not image.is_relative_to(imports) or digest(image) != row['expected_hash']:
            raise ValueError('Hash o ruta original incompatible')
        if any(v is not None for v in row['labels'].values()):
            raise ValueError('Una imagen pendiente ya contiene decisiones confirmadas')
    return pending


def render(rows):
    cards = []
    for number, row in enumerate(rows, 1):
        h = lambda value: escape(str(value), quote=True)
        metadata = [('sample_id', row['sample_id']), ('Nombre original', row['file_name']),
                    ('Ruta del original importado', row['original_url']), ('Hash esperado SHA-256', row['expected_hash']),
                    ('Etiquetas humanas actuales', json.dumps(row['labels'], ensure_ascii=False)),
                    ('Evidencia fuente (no confirmación humana)', json.dumps(row['source_labels'], ensure_ascii=False)),
                    ('Motivo pendiente', row['review_reason']), ('Grupo de origen', row['group_id']),
                    ('Partición propuesta conservada', row['proposed_partition']), ('Fuente', row['source']),
                    ('Autores fuente', ', '.join(row['creators'])), ('Licencia', row['license'])]
        fields = ''.join(f'<dt>{h(k)}</dt><dd>{h(v)}</dd>' for k, v in metadata)
        cards.append(f'''<article id="sample-{number}"><h2>{number}. {h(row['file_name'].split('/')[-1])}</h2>
<p>{h(row['review_reason'])}</p><a href="{h(row['original_url'])}" target="_blank" rel="noopener"><img src="{h(row['original_url'])}" alt="Original pendiente {number}; abrir fotografía" loading="eager"></a>
<p><button type="button" data-sample="{number}">Ampliar imagen {number}</button> · <a href="{h(row['original_url'])}" target="_blank" rel="noopener">Abrir original individual</a></p>
<dl>{fields}</dl><p><a href="{h(row['source_url'])}">Procedencia</a> · <a href="{h(row['license_url'])}">Licencia CC BY 4.0</a></p></article>''')
    return '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EPP · 9 imágenes pendientes</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef2f5;color:#182b3b;font:16px system-ui}header,main{max-width:1400px;margin:auto;padding:24px}header{background:#fff}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:24px}article{background:white;padding:20px;border-radius:12px;min-width:0}h2{font-size:18px;overflow-wrap:anywhere}article img{width:100%;height:460px;object-fit:contain;background:#202a33}dt{font-weight:bold;margin-top:12px}dd{margin:3px 0;overflow-wrap:anywhere;font-family:monospace}a{color:#075a96}button{padding:10px;cursor:pointer}dialog{width:96vw;max-width:none;height:94vh;padding:16px}dialog::backdrop{background:#000b}.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.viewport{height:calc(100% - 140px);overflow:auto;background:#202a33;margin-top:12px}.viewport img{display:block;max-width:none}#caption{overflow-wrap:anywhere;margin:8px 0}input{width:220px}
</style><header><h1>Revisión final · 9 imágenes pendientes</h1><p>2 requieren mayor detalle · 7 requieren confirmar encuadre/evaluabilidad.</p>
<p>Fotografías originales sin modificación. Las etiquetas humanas permanecen desconocidas (<code>null</code>). Esta hoja no asigna ni guarda etiquetas.</p>
<p>Abra «Ampliar», aumente el zoom y desplácese por la imagen para revisar cuerpo, cuello y tapa donde sean visibles. Ampliar no recupera detalles ausentes ni confirma evaluabilidad.</p>
<p>Los grupos y particiones se conservan; las imágenes no representan necesariamente botellas independientes.</p></header><main>''' + ''.join(cards) + '''</main>
<dialog id="viewer"><div class="toolbar"><button id="close" type="button">Cerrar</button><button id="fit" type="button">Ajustar</button><button id="native" type="button">100 % original</button><label>Zoom <input id="zoom" type="range" min="10" max="600" value="100"></label><output id="scale">100 %</output></div><p id="caption"></p><div class="viewport" id="viewport"><img id="detail" alt="Fotografía original ampliada"></div></dialog>
<script>
const viewer=document.querySelector('#viewer'),detail=document.querySelector('#detail'),zoom=document.querySelector('#zoom'),viewport=document.querySelector('#viewport');
function setZoom(value){value=Math.max(10,Math.min(600,value));zoom.value=value;detail.style.width=(detail.naturalWidth*value/100)+'px';document.querySelector('#scale').textContent=value+' %';}
function fit(){setZoom(Math.max(10,Math.floor(Math.min(viewport.clientWidth/detail.naturalWidth,viewport.clientHeight/detail.naturalHeight,1)*100)));viewport.scrollTo(0,0);}
document.querySelectorAll('[data-sample]').forEach(button=>button.addEventListener('click',()=>{const card=button.closest('article');document.querySelector('#caption').textContent=card.querySelector('h2').textContent;detail.onload=fit;detail.src=card.querySelector('img').getAttribute('src');viewer.showModal();if(detail.complete&&detail.naturalWidth)fit();}));
zoom.addEventListener('input',()=>setZoom(Number(zoom.value)));document.querySelector('#close').onclick=()=>viewer.close();document.querySelector('#fit').onclick=fit;document.querySelector('#native').onclick=()=>setZoom(100);
</script></html>'''


def generate(directory=BASE):
    directory = Path(directory).resolve()
    if any((directory / name).exists() for name in OUTPUTS):
        raise FileExistsError('No se sobrescriben hojas ni decisiones existentes')
    before = {name: digest(directory / name) for name in SOURCES}
    rows = pending_records(directory)
    decisions = []
    for row in rows:
        result = deepcopy(row)
        result['pending_decision'] = {
            'labels': dict.fromkeys(row['labels']),
            'evaluability': dict.fromkeys(('body', 'neck', 'cap', 'joint')),
            'CONFORME': None, 'NO_EVALUABLE': None,
            'outcome': None, 'notes': None, 'reviewer': None, 'reviewed_at_utc': None,
        }
        result['pending_decision_status'] = 'AWAITING_HUMAN_REVIEW'
        result['based_on_review_sha256'] = before[SOURCES[0]]
        decisions.append(result)
    if before != {name: digest(directory / name) for name in SOURCES}:
        raise ValueError('Fuentes modificadas durante generación')
    contents = (render(rows), ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in decisions))
    for name, content in zip(OUTPUTS, contents):
        with (directory / name).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(content)
    return {'pending': 9, 'detail': 2, 'framing': 7, 'verified_hashes': 9, 'sources_unchanged': True}


if __name__ == '__main__':
    print(json.dumps(generate()))

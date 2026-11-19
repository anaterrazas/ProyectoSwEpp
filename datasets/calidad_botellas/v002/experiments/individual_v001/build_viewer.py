"""Galería estática de evidencia observada y resultados individuales; sin inferencia adicional."""
from html import escape
import json
from pathlib import Path
from detectors import BASE


def main():
    comparison=json.loads((BASE/'comparison/results.json').read_text(encoding='utf-8'))
    sections=[]
    for name in ('prueba2_v001','tapas_v001'):
        folder=BASE/'runs'/name;r=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        relative=folder.relative_to(BASE).as_posix();stats={k:r[k] for k in ('frames_processed','observed_detections','temporary_track_ids','frames_without_detection','frames_with_multiple_detections','classifier_calls','processing_seconds')}
        cards=[]
        for track in r['tracks']:
            images=''.join('<figure><img src="'+escape(relative+'/'+s['path'],quote=True)+'"><figcaption>'+escape(Path(s['path']).stem)+' · SHA-256 '+s['sha256']+'</figcaption></figure>' for s in track['saved_regions'])
            card=f'<article><h3>ID temporal {track["track_id"]} · NO EVALUABLE</h3><p>Run: <code>{r["run_id"]}</code></p><p>{track["observed_frames"]} observaciones, fotogramas {track["first_frame"]}–{track["last_frame"]}. No es un ID físico permanente.</p><p>RAYADURA y DEFORMACION: NO DISPONIBLE. Llamadas al clasificador de tapa: {track["classifier_calls"]}.</p><p>ROI de tapa/cuello candidata geométrica; no es una detección de tapa ni una etiqueta humana.</p><div class="regions">{images}</div><details><summary>Motivos de bloqueo</summary><pre>{escape(json.dumps(track["cap_gate_reasons"],ensure_ascii=False,indent=2))}</pre></details></article>'
            cards.append(card)
        screenshots=''.join('<a href="'+relative+'/screenshots/'+p.name+'"><img class="shot" src="'+relative+'/screenshots/'+p.name+'" alt="Captura real '+escape(p.name)+'"></a>' for p in sorted((folder/'screenshots').glob('*.jpg')))
        sections.append(f'<section><h2>{escape(name)}</h2><video controls preload="metadata" src="{relative}/processed.mp4"></video><p><a href="{relative}/processed.mp4">Video procesado</a> · <a href="{relative}/report.json">Resumen por ID</a> · <a href="{relative}/frames.jsonl">Todas las observaciones con PTS</a></p><pre>{escape(json.dumps(stats,ensure_ascii=False,indent=2))}</pre><div class="shots">{screenshots}</div><div class="cards">'+(''.join(cards) if cards else '<p class="notice">SIN ENVASES DETECTADOS. NO EVALUABLE. No se crearon cajas, tracks ni recortes.</p>')+'</div></section>')
    table=[]
    for detector,videos in comparison['summary'].items():
        for name,m in videos.items():table.append(f'<tr><td>{detector}</td><td>{name}</td><td>{m["sampled_frames"]}</td><td>{m["detections"]}</td><td>{m["frames_with_detection"]}</td><td>{m["mean_seconds_per_frame"]:.4f}</td></tr>')
    page='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EPP · Inspección individual experimental</title>
<style>body{font:16px system-ui;margin:0;background:#eef3f7;color:#183144}main{max-width:1300px;margin:auto;padding:24px}section,article{background:white;border-radius:10px;padding:18px;margin:20px 0}video{width:100%;max-height:650px;background:#111}.notice{padding:18px;background:#fff0cc;border-left:5px solid #c17a00}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:16px}.cards article{border:1px solid #ccd4dc;margin:0;min-width:0}.regions{display:flex;gap:10px}.regions figure{margin:0;flex:1;min-width:0}.regions img{width:100%;height:260px;object-fit:contain;background:#eee}figcaption{font-size:12px;overflow-wrap:anywhere}.shots{display:flex;gap:12px}.shots a{width:33%}.shot{width:100%}pre,code{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px}a{color:#075b98}</style>
<main><h1>Canalización de inspección individual EPP</h1><p class="notice"><strong>Experimental. No control de conformidad.</strong> Verde: caja actual del detector con ID asociado; naranja: observación sin ID confirmado; azul: ROI candidata geométrica. No se dibujan posiciones de tracker sin detección actual. Los scores del detector no son confianza de calidad. La tapa permanece bloqueada sin evidencia compatible; cuerpo sin modelos.</p><h2>Comparación previa de alternativas</h2><p>Siete fotogramas por video. Conteos repetidos de observaciones, no unidades físicas ni precisión de detección. Sin verdad de referencia independiente: precision, recall, mAP y cambios de ID no medidos.</p><table><thead><tr><th>Detector</th><th>Video</th><th>Frames</th><th>Observaciones</th><th>Frames con detección</th><th>s/frame</th></tr></thead><tbody>'''+''.join(table)+'</tbody></table><p><a href="comparison/results.json">Datos de comparación</a> · <a href="comparison/gallery.html">Cajas de todas las alternativas</a></p>'+''.join(sections)+'</main></html>'
    with (BASE/'index.html').open('x',encoding='utf-8') as f:f.write(page)
    images=[]
    for row in comparison['frames']:
        images.append('<article><h2>'+escape(row['detector']+' / '+row['video']+' / frame '+str(row['frame_index']))+'</h2><img style="width:100%" src="../'+escape(row['image'],quote=True)+'"><p>Observaciones: '+str(len(row['detections']))+'</p></article>')
    with (BASE/'comparison/gallery.html').open('x',encoding='utf-8') as f:
        f.write('<!doctype html><html lang="es"><meta charset="utf-8"><title>Comparación real de detectores</title><style>body{font:16px system-ui}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:16px}</style><h1>Comparación previa: observaciones reales, sin cajas manuales</h1><main>'+''.join(images)+'</main></html>')


if __name__=='__main__':main()

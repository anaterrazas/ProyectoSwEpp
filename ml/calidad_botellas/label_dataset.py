"""Galería y etiquetado local con revisiones JSONL inmutables; sin Django/SQLite."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import urlparse
from uuid import uuid4

from .extract_crops import ROOT, sha256
from .validate_dataset import validate_many

DEFECTS = ("RAYADURA", "DEFORMACION", "TAPA_DEFECTUOSA")
EDITABLE = {"labels", "evaluable", "other_defect", "categories", "notes"}
REVIEW_FIELDS = (
    ("evaluable.body", "body", "Evaluabilidad del cuerpo"),
    ("evaluable.cap", "cap", "Evaluabilidad de la tapa"),
    ("other_defect", "other", "Otros defectos visibles fuera de taxonomía"),
    ("categories.CONFORME", "CONFORME", "Conclusión CONFORME"),
    ("categories.NO_EVALUABLE", "NO_EVALUABLE", "Conclusión NO_EVALUABLE"),
)


def missing_review_fields(row):
    missing = []
    for path, control, label in REVIEW_FIELDS:
        value = row
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if value is None:
            missing.append({"field": path, "control": control, "label": label})
    return missing


class ReviewIncomplete(ValueError):
    def __init__(self, fields):
        self.fields = fields
        super().__init__("Antes de cerrar, complete: " + "; ".join(field["label"] for field in fields) + ". Guarde las correcciones como borrador antes de cerrar.")


class Conflict(ValueError):
    pass


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def check_annotation(row, closed=False):
    labels, regions = row["labels"], row["evaluable"]
    if set(labels) != set(DEFECTS) or any(v is not None and (type(v) is not int or v not in (0, 1)) for v in labels.values()):
        raise ValueError("Defectos: use presente, ausente o desconocido.")
    if set(regions) != {"body", "cap"} or any(v is not None and type(v) is not bool for v in regions.values()):
        raise ValueError("Evaluabilidad inválida.")
    cats = row.get("categories", {"CONFORME": None, "NO_EVALUABLE": None})
    if set(cats) != {"CONFORME", "NO_EVALUABLE"} or any(v is not None and type(v) is not bool for v in cats.values()):
        raise ValueError("Categorías inválidas.")
    other = row["other_defect"]
    if other is not None and type(other) is not bool:
        raise ValueError("Otros defectos: use sí, no o desconocido.")
    if not isinstance(row.get("notes", ""), str) or len(row.get("notes", "")) > 4000:
        raise ValueError("Las observaciones admiten hasta 4000 caracteres.")
    for defect in DEFECTS:
        region = "cap" if defect == "TAPA_DEFECTUOSA" else "body"
        if labels[defect] == 0 and regions[region] is not True:
            raise ValueError("No marque un defecto como ausente si su región no es evaluable.")
    if cats["CONFORME"] is True and not (
        all(v == 0 for v in labels.values()) and all(v is True for v in regions.values())
        and other is False and cats["NO_EVALUABLE"] is False
    ):
        raise ValueError("CONFORME exige regiones evaluables, defectos ausentes y NO_EVALUABLE=No.")
    if closed:
        missing = missing_review_fields(row)
        if missing:
            raise ReviewIncomplete(missing)
        uncertain = any(v is None for v in labels.values()) or not all(regions.values())
        if uncertain and cats["NO_EVALUABLE"] is not True:
            raise ValueError("Atributos desconocidos o regiones insuficientes requieren NO_EVALUABLE=Sí.")
        conform = all(v == 0 for v in labels.values()) and all(regions.values()) and other is False
        if conform and cats["NO_EVALUABLE"] is False and cats["CONFORME"] is not True:
            raise ValueError("Revise la conclusión: se han indicado todas las condiciones de conformidad.")
        if cats["NO_EVALUABLE"] is True and not row.get("notes", "").strip():
            raise ValueError("Explique por qué la imagen no es evaluable.")


class Workspace:
    def __init__(self, datasets, directory):
        self.sources = [Path(p).resolve() for p in datasets]
        self.directory = Path(directory).resolve()
        if len(set(self.sources)) != len(self.sources):
            raise ValueError("No importe la misma ejecución dos veces.")
        if any(self.directory.is_relative_to(p) or p.is_relative_to(self.directory) for p in self.sources):
            raise ValueError("El espacio de etiquetas debe estar separado de las extracciones.")
        if any(self.directory.is_relative_to(ROOT / p) for p in ("media", "produccion", "config")):
            raise ValueError("No se permite guardar etiquetas en media ni en código de producción.")
        validate_many(self.sources)
        self.originals, self.images, signatures = {}, {}, []
        for source in self.sources:
            signatures.append({"root": str(source), "samples_sha256": sha256(source / "samples.jsonl"),
                               "run_sha256": sha256(source / "run.json")})
            for row in read_jsonl(source / "samples.jsonl"):
                sid = row["sample_id"]
                if sid in self.originals:
                    raise ValueError("ID de muestra duplicado entre fuentes.")
                self.originals[sid] = row
                self.images[sid] = (source / row["image"]).resolve()
        self.config = {"schema_version": "1.0.0", "sources": signatures,
                       "taxonomy_sha256": sha256(Path(__file__).with_name("taxonomy.json"))}
        if not self.directory.exists():
            self.directory.mkdir(parents=True, exist_ok=False)
            self._atomic(self.directory / "workspace.json", json.dumps(self.config, ensure_ascii=False, indent=2))
            (self.directory / "revisions").mkdir()
        else:
            existing = json.loads((self.directory / "workspace.json").read_text(encoding="utf-8"))
            if existing != self.config:
                raise ValueError("Las fuentes han cambiado. Cree un espacio nuevo; no sobrescriba el anterior.")
        self.mutex = threading.Lock()
        self.current()

    @staticmethod
    def _atomic(destination, text):
        temporary = destination.with_name("." + uuid4().hex + ".tmp")
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists():
            temporary.unlink()
            raise Conflict("La revisión ya existe; no se sobrescribirá.")
        os.rename(temporary, destination)

    def verify_sources(self):
        for source in self.config["sources"]:
            root = Path(source["root"])
            if sha256(root / "samples.jsonl") != source["samples_sha256"] or sha256(root / "run.json") != source["run_sha256"]:
                raise Conflict("El manifiesto original cambió. No se guardaron etiquetas.")
        if sha256(Path(__file__).with_name("taxonomy.json")) != self.config["taxonomy_sha256"]:
            raise Conflict("La taxonomía cambió. Cree una versión de trabajo nueva.")

    def current(self):
        self.verify_sources()
        files = sorted((self.directory / "revisions").glob("*.jsonl"))
        if not files:
            return 0, deepcopy(list(self.originals.values()))
        numbers = [int(p.stem) for p in files]
        if numbers != list(range(1, len(files) + 1)):
            raise Conflict("Falta una revisión; revise el respaldo antes de continuar.")
        rows = read_jsonl(files[-1])
        if len(rows) != len(self.originals) or len({r["sample_id"] for r in rows}) != len(rows):
            raise Conflict("Revisión incompleta o duplicada.")
        for row in rows:
            original = self.originals.get(row["sample_id"])
            if original is None or any(row.get(k) != v for k, v in original.items()
                                       if k not in EDITABLE | {"annotation_status", "annotator", "reviewer"}):
                raise Conflict("Los campos de procedencia no se pueden cambiar.")
            check_annotation(row, row["annotation_status"] == "REVIEWED")
        return len(files), rows

    @contextmanager
    def locked(self):
        with self.mutex:
            try:
                fd = os.open(self.directory / ".write.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as error:
                raise Conflict("Otro proceso está guardando. Si hubo un cierre anormal, revise el bloqueo manualmente.") from error
            try:
                yield
            finally:
                os.close(fd)
                (self.directory / ".write.lock").unlink()

    def save(self, payload):
        if set(payload) != {"sample_id", "revision", "actor", "action", "values"}:
            raise ValueError("Solicitud inválida.")
        actor = payload["actor"]
        if not isinstance(actor, str) or not 2 <= len(actor.strip()) <= 100:
            raise ValueError("Indique su nombre o identificador (2–100 caracteres).")
        actor = actor.strip()
        if payload["action"] not in ("draft", "review", "reopen"):
            raise ValueError("Acción inválida.")
        with self.locked():
            revision, rows = self.current()
            if type(payload["revision"]) is not int or payload["revision"] != revision:
                raise Conflict("Otra pestaña guardó cambios. Recargue antes de editar.")
            row = next((r for r in rows if r["sample_id"] == payload["sample_id"]), None)
            if row is None:
                raise ValueError("Muestra inexistente.")
            if sha256(self.images[row["sample_id"]]) != row["image_sha256"]:
                raise Conflict("La imagen original cambió; no se guardaron etiquetas.")
            action, values = payload["action"], payload["values"]
            if not isinstance(values, dict) or set(values) != EDITABLE:
                raise ValueError("Campos de anotación incompletos o no permitidos.")
            now = datetime.now(timezone.utc).isoformat()
            if action == "reopen":
                if row["annotation_status"] != "REVIEWED":
                    raise ValueError("La muestra todavía no está cerrada.")
                row.update(annotation_status="ANNOTATED", reviewer=None, reviewed_at=None)
            else:
                if row["annotation_status"] == "REVIEWED":
                    raise Conflict("Reabra la muestra antes de corregirla.")
                if action == "review":
                    if row["annotation_status"] != "ANNOTATED" or not row.get("annotator"):
                        raise ValueError("Guarde el borrador antes de cerrar.")
                    if actor.casefold() == row["annotator"].casefold():
                        raise ValueError("El cierre requiere un revisor distinto del anotador inicial.")
                    previous = {k: row.get(k, {"CONFORME": None, "NO_EVALUABLE": None} if k == "categories" else "") for k in EDITABLE}
                    if values != previous:
                        raise ValueError("Guarde las correcciones como borrador antes de cerrar.")
                row.update(deepcopy(values))
                check_annotation(row, action == "review")
                row["annotation_status"] = "REVIEWED" if action == "review" else "ANNOTATED"
                if not row.get("annotator"):
                    row["annotator"], row["annotated_at"] = actor, now
                if action == "review":
                    row["reviewer"], row["reviewed_at"] = actor, now
            row.update(updated_by=actor, updated_at=now)
            row.setdefault("annotation_history", []).append({"revision": revision + 1, "actor": actor,
                                                             "action": action, "at": now})
            text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
            self._atomic(self.directory / "revisions" / f"{revision + 1:06d}.jsonl", text)
            return revision + 1, rows


def make_server(workspace, port=8766):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body, content_type="application/json; charset=utf-8", download=False):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="annotations.jsonl"')
            self.end_headers()
            self.wfile.write(body)

        def trusted_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.trusted_host():
                return self.reply(403, {"error": "Host no permitido."})
            path = urlparse(self.path).path
            try:
                static = {"/": ("label_ui.html", "text/html; charset=utf-8"),
                          "/app.js": ("label_ui.js", "text/javascript; charset=utf-8"),
                          "/app.css": ("label_ui.css", "text/css; charset=utf-8")}
                if path in static:
                    name, mime = static[path]
                    return self.reply(200, Path(__file__).with_name(name).read_bytes(), mime)
                if path == "/favicon.ico":
                    return self.reply(204, b"", "image/x-icon")
                if path == "/api/state":
                    revision, rows = workspace.current()
                    return self.reply(200, {"revision": revision, "rows": rows, "token": token,
                                            "review_fields": [{"field": path, "control": control, "label": label}
                                                              for path, control, label in REVIEW_FIELDS]})
                if path == "/api/export":
                    _, rows = workspace.current()
                    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
                    return self.reply(200, text, "application/x-ndjson; charset=utf-8", download=True)
                if path.startswith("/image/"):
                    sid = path.removeprefix("/image/")
                    if sid not in workspace.images:
                        return self.reply(404, {"error": "Imagen inexistente."})
                    file = workspace.images[sid]
                    if sha256(file) != workspace.originals[sid]["image_sha256"]:
                        raise Conflict("La imagen original fue modificada.")
                    return self.reply(200, file.read_bytes(), "image/png")
                return self.reply(404, {"error": "Ruta inexistente."})
            except (ValueError, OSError, KeyError) as error:
                return self.reply(409, {"error": str(error)})

        def do_POST(self):
            if (not self.trusted_host() or self.headers.get("Origin") not in {
                f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
                or not secrets.compare_digest(self.headers.get("X-Label-Token", ""), token)):
                return self.reply(403, {"error": "Solicitud local no autorizada."})
            if self.path != "/api/save":
                return self.reply(404, {"error": "Ruta inexistente."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Cuerpo de solicitud inválido.")
                payload = json.loads(self.rfile.read(length))
                revision, rows = workspace.save(payload)
                return self.reply(200, {"revision": revision, "rows": rows, "token": token})
            except Conflict as error:
                return self.reply(409, {"error": str(error)})
            except ReviewIncomplete as error:
                return self.reply(400, {"error": str(error), "missing_fields": error.fields})
            except (ValueError, KeyError, TypeError) as error:
                return self.reply(400, {"error": str(error)})
            except OSError:
                return self.reply(500, {"error": "No se pudo guardar. Mantenga el formulario abierto y revise el disco."})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    workspace = Workspace(args.dataset, args.workspace)
    revision, rows = workspace.current()
    if args.check:
        print(json.dumps({"revision": revision, "samples": len(rows), "status": "OK"}))
        return
    server = make_server(workspace, args.port)
    print(f"Galería local: http://127.0.0.1:{server.server_port} — {len(rows)} imágenes; Ctrl+C para salir.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

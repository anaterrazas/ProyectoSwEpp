"""Anotaciones de prueba solo en copias temporales; no etiquetan el dataset real."""
from copy import deepcopy
import http.client
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import threading
import unittest

from .extract_crops import ROOT, sha256
from .label_dataset import Conflict, EDITABLE, REVIEW_FIELDS, ReviewIncomplete, Workspace, check_annotation, make_server, missing_review_fields

REFERENCE = ROOT / "datasets/calidad_botellas/v001/runs/referencia_a3"


class LabelingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="epp_labels_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        shutil.copytree(REFERENCE, self.source)
        self.before = {str(p.relative_to(self.source)): sha256(p) for p in self.source.rglob('*') if p.is_file()}
        self.workspace = Workspace([self.source], self.root / "labels")
        self.sid = next(iter(self.workspace.originals))

    def payload(self, action="draft", actor="Anotador de prueba", **values):
        revision, rows = self.workspace.current()
        row = next(r for r in rows if r["sample_id"] == self.sid)
        data = {key: deepcopy(row.get(key)) for key in EDITABLE}
        data["categories"] = row.get("categories", {"CONFORME": None, "NO_EVALUABLE": None})
        data["notes"] = row.get("notes", "")
        data.update(values)
        return {"sample_id": self.sid, "revision": revision, "actor": actor, "action": action, "values": data}

    def test_initial_state_keeps_unknowns_and_originals(self):
        revision, rows = self.workspace.current()
        self.assertEqual(revision, 0)
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(r["annotation_status"] == "PENDING" for r in rows))
        self.assertTrue(all(all(v is None for v in r["labels"].values()) for r in rows))
        after = {str(p.relative_to(self.source)): sha256(p) for p in self.source.rglob('*') if p.is_file()}
        self.assertEqual(self.before, after)

    def test_draft_correction_revision_history_and_preservation(self):
        self.workspace.save(self.payload(notes="Primer borrador de prueba"))
        first = sha256(self.root / "labels/revisions/000001.jsonl")
        self.workspace.save(self.payload(notes="Corrección de prueba"))
        self.assertEqual(first, sha256(self.root / "labels/revisions/000001.jsonl"))
        revision, rows = Workspace([self.source], self.root / "labels").current()
        row = next(r for r in rows if r["sample_id"] == self.sid)
        self.assertEqual(revision, 2)
        self.assertEqual(row["notes"], "Corrección de prueba")
        self.assertEqual(len(row["annotation_history"]), 2)
        self.assertIn("+00:00", row["annotated_at"])
        self.assertEqual(row["annotator"], "Anotador de prueba")
        self.assertEqual(len(rows), len({r["sample_id"] for r in rows}))
        self.assertEqual(self.before, {str(p.relative_to(self.source)): sha256(p) for p in self.source.rglob('*') if p.is_file()})

    def test_stale_revision_rejected(self):
        old = self.payload()
        self.workspace.save(old)
        with self.assertRaises(Conflict):
            self.workspace.save(old)
        self.assertEqual(self.workspace.current()[0], 1)

    def test_conflicting_labels_do_not_create_revision(self):
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(categories={"CONFORME": True, "NO_EVALUABLE": True}))
        self.assertEqual(self.workspace.current()[0], 0)

    def test_unseen_region_cannot_be_marked_defect_free(self):
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(labels={"RAYADURA": None, "DEFORMACION": None, "TAPA_DEFECTUOSA": 0}))
        self.assertEqual(self.workspace.current()[0], 0)

    def test_multiple_defects_with_unknown_region_can_be_closed_no_evaluable(self):
        self.workspace.save(self.payload(labels={"RAYADURA": 1, "DEFORMACION": 1, "TAPA_DEFECTUOSA": None},
                                         evaluable={"body": True, "cap": False}, other_defect=False,
                                         categories={"CONFORME": False, "NO_EVALUABLE": True}, notes="Tapa oculta; ejemplo solo de prueba."))
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(action="review"))
        self.workspace.save(self.payload(action="review", actor="Revisor de prueba"))
        _, rows = self.workspace.current()
        row = next(r for r in rows if r["sample_id"] == self.sid)
        self.assertEqual(row["annotation_status"], "REVIEWED")
        self.assertEqual(row["reviewer"], "Revisor de prueba")
        self.assertIsNone(row["labels"]["TAPA_DEFECTUOSA"])
        with self.assertRaises(Conflict):
            self.workspace.save(self.payload())
        self.workspace.save(self.payload(action="reopen", actor="Revisor de prueba"))
        self.workspace.save(self.payload(notes="Nueva corrección temporal"))
        self.assertEqual(self.workspace.current()[0], 4)

    def test_conforme_requires_explicit_complete_evidence(self):
        row = deepcopy(self.workspace.originals[self.sid])
        row.update(categories={"CONFORME": True, "NO_EVALUABLE": False}, notes="")
        with self.assertRaises(ValueError):
            check_annotation(row)
        row.update(labels={"RAYADURA": 0, "DEFORMACION": 0, "TAPA_DEFECTUOSA": 0},
                   evaluable={"body": True, "cap": True}, other_defect=False)
        check_annotation(row, closed=True)

    def test_missing_author_or_unknown_sample_rejected(self):
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(actor=""))
        payload = self.payload()
        payload["sample_id"] = "unknown"
        with self.assertRaises(ValueError):
            self.workspace.save(payload)

    def test_source_mutation_blocks_save(self):
        original = self.source / self.workspace.originals[self.sid]["image"]
        payload = self.payload()
        original.write_bytes(b"changed fixture")
        with self.assertRaises(Conflict):
            self.workspace.save(payload)

    def test_duplicate_source_and_nested_workspace_rejected(self):
        with self.assertRaises(ValueError):
            Workspace([self.source, self.source], self.root / "other")
        with self.assertRaises(ValueError):
            Workspace([self.source], self.source / "labels")

    def test_filesystem_lock_blocks_second_writer(self):
        lock = self.root / "labels/.write.lock"
        lock.write_text("fixture", encoding="utf-8")
        with self.assertRaises(Conflict):
            self.workspace.save(self.payload())
        lock.unlink()

    def test_close_reports_exact_fields_used_by_interface(self):
        row = deepcopy(self.workspace.originals[self.sid])
        row.update(evaluable={"body": False, "cap": None}, categories={"CONFORME": False, "NO_EVALUABLE": True}, notes="Fixture no evaluable")
        self.assertEqual([f["field"] for f in missing_review_fields(row)], ["evaluable.cap", "other_defect"])
        with self.assertRaises(ReviewIncomplete) as raised:
            check_annotation(row, closed=True)
        self.assertIn("Evaluabilidad de la tapa", str(raised.exception))
        self.assertIn("Otros defectos visibles fuera de taxonomía", str(raised.exception))
        self.assertNotIn("Conclusión CONFORME", str(raised.exception))
        html = Path(__file__).with_name("label_ui.html").read_text(encoding="utf-8")
        for _, control, _ in REVIEW_FIELDS:
            self.assertEqual(html.count('id="' + control + '"'), 1)
        self.assertIn('id="review-missing"', html)
        self.assertIn('id="other-fieldset"', html)

    def test_existing_19_drafts_survive_completion_independent_review_and_reopen(self):
        # Reproduce el bloqueo de 19 borradores sin alterar anotaciones reales.
        _, original_rows = self.workspace.current()
        for i, original in enumerate(original_rows):
            self.sid = original["sample_id"]
            self.workspace.save(self.payload(actor="ANOTADOR_01", evaluable={"body": False, "cap": None if i == 0 else False},
                                              categories={"CONFORME": False, "NO_EVALUABLE": True}, notes="Caso ficticio para regresión de cierre"))
        before = {p.name: sha256(p) for p in (self.root / "labels/revisions").glob('*.jsonl')}
        self.sid = original_rows[0]["sample_id"]
        with self.assertRaises(ReviewIncomplete):
            self.workspace.save(self.payload(action="review", actor="SUPERVISOR_01"))
        self.assertEqual(self.workspace.current()[0], 19)
        old = deepcopy(self.workspace.current()[1][0])
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(action="review", actor="SUPERVISOR_01", other_defect=False, evaluable={"body": False, "cap": False}))
        self.workspace.save(self.payload(actor="SUPERVISOR_01", other_defect=False, evaluable={"body": False, "cap": False}))
        with self.assertRaises(ValueError):
            self.workspace.save(self.payload(action="review", actor="ANOTADOR_01"))
        self.workspace.save(self.payload(action="review", actor="SUPERVISOR_01"))
        revision, rows = self.workspace.current()
        reviewed = next(r for r in rows if r["sample_id"] == self.sid)
        self.assertEqual(revision, 21)
        self.assertEqual(reviewed["annotator"], "ANOTADOR_01")
        self.assertEqual(reviewed["annotated_at"], old["annotated_at"])
        self.assertEqual(reviewed["reviewer"], "SUPERVISOR_01")
        self.assertEqual(reviewed["annotation_status"], "REVIEWED")
        self.assertEqual(reviewed["annotation_history"][:len(old["annotation_history"])], old["annotation_history"])
        self.assertTrue(all(v is None for v in reviewed["labels"].values()))
        self.assertEqual(sum(r["annotation_status"] == "ANNOTATED" for r in rows), 18)
        for name, digest in before.items():
            self.assertEqual(sha256(self.root / "labels/revisions" / name), digest)
        self.workspace.save(self.payload(action="reopen", actor="SUPERVISOR_01"))
        self.assertEqual(self.workspace.current()[0], 22)

    def test_http_gallery_security_export_and_save(self):
        server = make_server(self.workspace, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        host = f"127.0.0.1:{server.server_port}"
        client = http.client.HTTPConnection(host, timeout=5)
        self.addCleanup(client.close)
        client.request("GET", "/api/state")
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        state = json.loads(response.read())
        self.assertEqual(len(state["rows"]), 19)
        self.assertEqual({f["control"] for f in state["review_fields"]}, {"body", "cap", "other", "CONFORME", "NO_EVALUABLE"})
        client.request("GET", "/favicon.ico")
        response = client.getresponse()
        self.assertEqual(response.status, 204)
        response.read()
        client.request("GET", "/image/" + self.sid)
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        self.assertTrue(response.read().startswith(b"\x89PNG"))
        client.request("GET", "/image/../../db.sqlite3")
        response = client.getresponse()
        self.assertEqual(response.status, 404)
        response.read()
        client.request("POST", "/api/save", json.dumps(self.payload()), {"Content-Type": "application/json"})
        response = client.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        headers = {"Content-Type": "application/json", "X-Label-Token": state["token"], "Origin": "http://" + host}
        client.request("POST", "/api/save", json.dumps(self.payload(notes="HTTP fixture")), headers)
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.read())["revision"], 1)
        client.request("GET", "/api/export")
        response = client.getresponse()
        rows = [json.loads(line) for line in response.read().decode().splitlines()]
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows[0]["annotation_status"], "ANNOTATED")
        self.workspace.save(self.payload(evaluable={"body": False, "cap": False}, categories={"CONFORME": False, "NO_EVALUABLE": True}, notes="Fixture HTTP de cierre"))
        client.request("POST", "/api/save", json.dumps(self.payload(action="review", actor="SUPERVISOR_01")), headers)
        response = client.getresponse()
        self.assertEqual(response.status, 400)
        error = json.loads(response.read())
        self.assertEqual([field["control"] for field in error["missing_fields"]], ["other"])
        client.request("GET", "/", headers={"Host": "evil.example"})
        response = client.getresponse()
        self.assertEqual(response.status, 403)
        response.read()


if __name__ == "__main__":
    unittest.main()

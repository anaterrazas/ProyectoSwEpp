"""Fixtures artificiales solo para probar selección; la regresión usa el video real."""
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

import cv2
import numpy as np

from .extract_crops import Options, ROOT, Selector, crop_and_quality, extract, read_analysis, sha256
from .validate_dataset import validate, validate_many


class PreparationTests(unittest.TestCase):
    def test_quality_flags_and_clipping(self):
        options = Options()
        image = np.zeros((200, 100, 3), np.uint8)
        result = crop_and_quality(image, [-5, -5, 80, 180], options)
        self.assertEqual(result[1][:2], [0, 0])
        self.assertIn("possible_blur", result[2]["flags"])
        self.assertIn("underexposure", result[2]["flags"])
        self.assertIn("touches_frame_border", result[2]["flags"])
        self.assertEqual(result[2]["status"], "REVIEW")
        self.assertIsNone(crop_and_quality(image, [50, 50, 20, 20], options))
        self.assertIsNone(crop_and_quality(image, [0, 0, float('nan'), 1], options))

    def test_deduplication_time_limit_and_original_untouched(self):
        options = Options(max_per_track=2)
        selector = Selector(options)
        image = np.random.default_rng(1).integers(20, 230, (240, 200, 3), dtype=np.uint8)
        original = image.copy()
        for frame in [0, 1, 25, 50, 100]:
            selector.consider(1, image, [20, 20, 180, 220], frame, 50, 0.9)
        self.assertEqual(len(selector.samples[1]), 1)
        self.assertGreater(selector.stats["similar_or_temporally_close"], 0)
        for frame in range(150, 500, 50):
            other = np.random.default_rng(frame).integers(20, 230, image.shape, dtype=np.uint8)
            selector.consider(1, other, [20, 20, 180, 220], frame, 50, 0.9)
        self.assertLessEqual(len(selector.samples[1]), 2)
        np.testing.assert_array_equal(image, original)

    def test_options_and_memory_limit(self):
        with self.assertRaises(ValueError):
            Options(max_per_track=0).validate()
        selector = Selector(Options(max_memory_bytes=1))
        with self.assertRaises(ValueError):
            selector.consider(1, np.zeros((200, 100, 3), np.uint8), [0, 0, 100, 200], 0, 25, 0.9)

    def test_real_video_provenance_count_and_manifest(self):
        video = ROOT / "pruebas_ia/produccion.mp4"
        weights = ROOT / "yolo11n.pt"
        before_video, before_weights = sha256(video), sha256(weights)
        with TemporaryDirectory(prefix="epp_crop_test_") as temp:
            root = Path(temp)
            db = root / "fixture.sqlite3"
            with sqlite3.connect(db) as c:
                c.executescript("CREATE TABLE produccion_analisisproduccion(id,video_original,lote_id);"
                                "CREATE TABLE produccion_loteproduccion(id,producto_id);"
                                "CREATE TABLE produccion_producto(id,tipo);")
                c.execute("INSERT INTO produccion_analisisproduccion VALUES (1,?,1)", (video.name,))
                c.execute("INSERT INTO produccion_loteproduccion VALUES (1,1)")
                c.execute("INSERT INTO produccion_producto VALUES (1,'BOTELLA')")
            c.close()
            before_db = sha256(db)
            provenance = read_analysis(db, 1, video, video.parent)
            with self.assertRaises(ValueError):
                read_analysis(db, 999, video, video.parent)
            different = root / "different.mp4"
            different.write_bytes(b"not the original video")
            with self.assertRaises(ValueError):
                read_analysis(db, 1, different, video.parent)
            run = extract(video, weights, root / "dataset", provenance)
            self.assertEqual(run["audit_count"], 8)
            self.assertEqual(run["frames_processed"], 434)
            self.assertEqual(run["counted_track_ids"], [1, 2, 3, 4, 15, 23, 32, 35])
            self.assertGreater(run["saved_crops"], 0)
            self.assertLessEqual(run["saved_crops"], 40)
            rows = [json.loads(line) for line in (root / "dataset/samples.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(all(value is None for value in r["labels"].values()) for r in rows))
            self.assertEqual(validate(root / "dataset")["status"], "OK")
            with self.assertRaises(ValueError):
                validate(root / "dataset", ready=True)
            with self.assertRaises(ValueError):
                validate_many([root / "dataset", root / "dataset"])
            manifest = root / "dataset/samples.jsonl"
            content = manifest.read_text(encoding="utf-8")
            rows[0]["split"], rows[1]["split"] = "train", "val"
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate(root / "dataset")
            manifest.write_text(content, encoding="utf-8")
            with self.assertRaises(FileExistsError):
                extract(video, weights, root / "dataset", provenance)
            # Ningún recorte debe contener overlays ni conversiones de color: píxeles exactos del original.
            cap = cv2.VideoCapture(str(video))
            try:
                first = rows[0]
                cap.set(cv2.CAP_PROP_POS_FRAMES, first["frame_index"])
                ok, frame = cap.read()
                self.assertTrue(ok)
                left, top, right, bottom = first["crop_box_xyxy"]
                np.testing.assert_array_equal(cv2.imread(str(root / "dataset" / first["image"])), frame[top:bottom, left:right])
            finally:
                cap.release()
            sample = root / "dataset" / rows[0]["image"]
            sample.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                validate(root / "dataset")
            self.assertEqual(sha256(db), before_db)
        self.assertEqual(sha256(video), before_video)
        self.assertEqual(sha256(weights), before_weights)


if __name__ == "__main__":
    unittest.main()

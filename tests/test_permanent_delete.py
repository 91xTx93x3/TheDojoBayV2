import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


class FakeCache:
    def __init__(self, data):
        self.data = data
        self.saved = None
        self.invalidated = False

    def get_stale(self):
        return self.data

    def save(self, data):
        self.saved = data

    def invalidate(self):
        self.invalidated = True


class PermanentDeleteTests(unittest.TestCase):
    def test_owner_delete_removes_record_public_entry_cache_and_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dojos_path = root / "dojos_data.json"
            submissions_path = root / "dojo_submissions.json"
            image_dir = root / "dojos"
            qr_dir = root / "qr"
            image_dir.mkdir()
            qr_dir.mkdir()
            (image_dir / "photo.png").write_bytes(b"photo")
            (qr_dir / "node.png").write_bytes(b"qr")

            owner = "PM8TOwner"
            submission = {
                "id": "node-id",
                "name": "Reusable Name",
                "paynym": owner,
                "network": "mainnet",
                "status": "approved",
                "image_file": "photo.png",
                "qr_filename": "node.png",
            }
            submissions_path.write_text(json.dumps([submission]))
            dojos_path.write_text(json.dumps({
                "mainnet": [{
                    "name": "Reusable Name",
                    "submission_id": "node-id",
                    "image": "/static/images/qr/node.png",
                }],
                "testnet": [],
            }))
            fake_cache = FakeCache({
                "mainnet": [{"name": "Reusable Name", "status": "Active"}],
                "testnet": [],
                "stats": {},
            })

            with (
                patch.object(app_module, "DOJOS_DATA_FILE", dojos_path),
                patch.object(app_module, "SUBMISSIONS_FILE", submissions_path),
                patch.object(app_module, "DOJO_IMAGE_DIR", image_dir),
                patch.object(app_module, "QR_IMAGE_DIR", qr_dir),
                patch.object(app_module.data_loader, "data_file", dojos_path),
                patch.object(app_module, "cache", fake_cache),
                patch.object(app_module, "mainnet_dojos", []),
                patch.object(app_module, "testnet_dojos", []),
            ):
                client = app_module.app.test_client()
                with client.session_transaction() as session:
                    session["paynym"] = owner
                response = client.post("/add-dojo/delete/node-id")

            self.assertEqual(response.status_code, 302)
            self.assertEqual(json.loads(submissions_path.read_text()), [])
            self.assertEqual(
                json.loads(dojos_path.read_text()),
                {"mainnet": [], "testnet": []},
            )
            self.assertFalse((image_dir / "photo.png").exists())
            self.assertFalse((qr_dir / "node.png").exists())
            self.assertEqual(fake_cache.saved["mainnet"], [])

    def test_pending_duplicate_name_cannot_delete_another_owners_live_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dojos_path = root / "dojos_data.json"
            submissions_path = root / "dojo_submissions.json"
            image_dir = root / "dojos"
            qr_dir = root / "qr"
            image_dir.mkdir()
            qr_dir.mkdir()

            submissions = [{
                "id": "attacker-pending",
                "name": "Existing Node",
                "paynym": "PM8TAttacker",
                "network": "mainnet",
                "status": "pending",
            }]
            submissions_path.write_text(json.dumps(submissions))
            live_entry = {
                "name": "Existing Node",
                "submission_id": "legitimate-id",
                "pairing": {"url": "http://legitimate.onion"},
            }
            dojos_path.write_text(json.dumps({
                "mainnet": [live_entry],
                "testnet": [],
            }))

            with (
                patch.object(app_module, "DOJOS_DATA_FILE", dojos_path),
                patch.object(app_module, "SUBMISSIONS_FILE", submissions_path),
                patch.object(app_module, "DOJO_IMAGE_DIR", image_dir),
                patch.object(app_module, "QR_IMAGE_DIR", qr_dir),
                patch.object(app_module.data_loader, "data_file", dojos_path),
                patch.object(app_module, "cache", FakeCache(None)),
                patch.object(app_module, "mainnet_dojos", []),
                patch.object(app_module, "testnet_dojos", []),
            ):
                client = app_module.app.test_client()
                with client.session_transaction() as session:
                    session["paynym"] = "PM8TAttacker"
                response = client.post("/add-dojo/delete/attacker-pending")

            self.assertEqual(response.status_code, 302)
            self.assertEqual(json.loads(submissions_path.read_text()), [])
            self.assertEqual(
                json.loads(dojos_path.read_text())["mainnet"],
                [live_entry],
            )


if __name__ == "__main__":
    unittest.main()

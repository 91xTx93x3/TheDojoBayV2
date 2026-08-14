import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


PAYMENT_CODE = (
    "PM8TJQwkgoVeogzAQe431Bn3FSsXiCqjmFCpysFuSTjB7FaxfrJGtMAEfsA5dvpt"
    "jMAAxLXKM6bDAen5tFp326EHBmRH6jQ9vJDPnSwARLmUcJoucQtd"
)


class DojoEditTests(unittest.TestCase):
    def test_editing_approved_node_removes_old_qr_and_original_network_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data_path = root / "dojos_data.json"
            submissions_path = root / "dojo_submissions.json"
            qr_dir = root / "qr"
            qr_dir.mkdir()
            (qr_dir / "old.png").write_bytes(b"old qr data")

            pairing = json.dumps({
                "pairing": {
                    "type": "dojo.api",
                    "version": "1.30.0",
                    "apikey": "new-key",
                    "url": "http://new.onion/v2",
                },
            })
            data_path.write_text(json.dumps({
                "mainnet": [],
                "testnet": [{
                    "name": "Old Name",
                    "submission_id": "node-id",
                    "image": "/static/images/qr/old.png",
                }],
            }))
            submissions_path.write_text(json.dumps([{
                "id": "node-id",
                "paynym": PAYMENT_CODE,
                "name": "Old Name",
                "network": "testnet",
                "pairing_details": pairing,
                "pairing_signature": "old-signature",
                "qr_filename": "old.png",
                "submitted_at": "2026-08-01T00:00:00",
                "updated_at": "2026-08-01T00:00:00",
                "status": "approved",
            }]))

            client = app_module.app.test_client()
            with client.session_transaction() as session:
                session["paynym"] = PAYMENT_CODE

            with (
                patch.object(app_module, "DOJOS_DATA_FILE", data_path),
                patch.object(app_module, "SUBMISSIONS_FILE", submissions_path),
                patch.object(app_module, "QR_IMAGE_DIR", qr_dir),
                patch.object(app_module.data_loader, "data_file", data_path),
                patch.object(app_module, "verify_pairing_signature", return_value=True),
                patch.object(app_module, "_resolve_paynym_alias", return_value="+owner"),
                patch.object(app_module.cache, "invalidate"),
            ):
                response = client.post("/add-dojo/edit/node-id", data={
                    "name": "New Name",
                    "network": "mainnet",
                    "pairing_details": pairing,
                    "pairing_signature": "new-signature",
                })

            self.assertEqual(response.status_code, 302)
            self.assertFalse((qr_dir / "old.png").exists())

            submissions = json.loads(submissions_path.read_text())
            self.assertEqual(submissions[0]["status"], "pending")
            self.assertEqual(submissions[0]["network"], "mainnet")
            self.assertNotIn("qr_filename", submissions[0])

            directory = json.loads(data_path.read_text())
            self.assertEqual(directory["testnet"], [])
            self.assertEqual(directory["mainnet"], [])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


class AdminApproveTests(unittest.TestCase):
    def test_approve_recovers_when_dojos_data_file_has_unexpected_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            dojos_data_path = tmpdir_path / 'dojos_data.json'
            submissions_path = tmpdir_path / 'dojo_submissions.json'
            qr_dir = tmpdir_path / 'qr'
            qr_dir.mkdir()

            dojos_data_path.write_text(json.dumps([
                {'name': 'Existing Node'}
            ]))
            submissions_path.write_text(json.dumps([{
                'id': 'pending-node-1',
                'name': 'Pending Node',
                'network': 'mainnet',
                'status': 'pending',
                'paynym': 'PM8TJQwkgoVeogzAQe431Bn3FSsXiCqjmFCpysFuSTjB7FaxfrJGtMAEfsA5dvptjMAAxLXKM6bDAen5tFp326EHBmRH6jQ9vJDPnSwARLmUcJoucQtd',
                'pairing_details': json.dumps({
                    'pairing': {
                        'type': 'dojo.api',
                        'version': '1.29.0',
                        'apikey': 'abc123',
                        'url': 'http://example.onion/v2',
                    },
                    'explorer': {'type': 'explorer.btc_rpc_explorer', 'url': 'http://explorer.onion'},
                }),
                'pairing_signature': 'signature',
                'electrum_server': '',
                'nostr_x': '',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00',
            }]))

            original_dojos_data_file = app_module.DOJOS_DATA_FILE
            original_submissions_file = app_module.SUBMISSIONS_FILE
            original_data_loader_file = app_module.data_loader.data_file
            original_qr_image_dir = app_module.QR_IMAGE_DIR

            app_module.DOJOS_DATA_FILE = dojos_data_path
            app_module.SUBMISSIONS_FILE = submissions_path
            app_module.data_loader.data_file = dojos_data_path
            app_module.QR_IMAGE_DIR = qr_dir

            self.addCleanup(setattr, app_module, 'DOJOS_DATA_FILE', original_dojos_data_file)
            self.addCleanup(setattr, app_module, 'SUBMISSIONS_FILE', original_submissions_file)
            self.addCleanup(setattr, app_module.data_loader, 'data_file', original_data_loader_file)
            self.addCleanup(setattr, app_module, 'QR_IMAGE_DIR', original_qr_image_dir)

            client = app_module.app.test_client()
            with client.session_transaction() as session:
                session['paynym'] = next(iter(app_module.ADMIN_PAYNMS))

            with patch.object(app_module, 'verify_pairing_signature', return_value=True):
                response = client.post('/admin/dojos/pending-node-1/approve', follow_redirects=False)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/admin/dojos')

            submissions = json.loads(submissions_path.read_text())
            self.assertEqual(submissions[0]['status'], 'approved')

            dojos_data = json.loads(dojos_data_path.read_text())
            self.assertIn('mainnet', dojos_data)
            self.assertEqual(len(dojos_data['mainnet']), 2)
            approved = next(item for item in dojos_data['mainnet']
                            if item.get('name') == 'Pending Node')
            self.assertEqual(approved['image'], '/static/images/qr/Pending_Node_pending-.png')
            self.assertTrue((qr_dir / 'Pending_Node_pending-.png').is_file())

    def test_repair_regenerates_missing_qr_for_approved_submission(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dojos_data_path = root / 'dojos_data.json'
            submissions_path = root / 'dojo_submissions.json'
            qr_dir = root / 'qr'
            qr_dir.mkdir()
            pairing = {
                'pairing': {
                    'type': 'dojo.api',
                    'version': '1.29.2',
                    'apikey': 'secret',
                    'url': 'http://example.onion/v2',
                },
            }
            dojos_data_path.write_text(json.dumps({
                'mainnet': [{
                    'name': 'Tanto Alive',
                    'submission_id': '655d555d-node',
                    'pairing': pairing['pairing'],
                }],
                'testnet': [],
            }))
            submissions_path.write_text(json.dumps([{
                'id': '655d555d-node',
                'name': 'Tanto Alive',
                'network': 'mainnet',
                'status': 'approved',
                'pairing_details': json.dumps(pairing),
            }]))

            with (
                patch.object(app_module, 'DOJOS_DATA_FILE', dojos_data_path),
                patch.object(app_module, 'SUBMISSIONS_FILE', submissions_path),
                patch.object(app_module, 'QR_IMAGE_DIR', qr_dir),
            ):
                repaired = app_module._repair_missing_qr_codes()

            self.assertEqual(repaired, 1)
            qr_filename = 'Tanto_Alive_655d555d.png'
            self.assertTrue((qr_dir / qr_filename).is_file())
            directory = json.loads(dojos_data_path.read_text())
            self.assertEqual(
                directory['mainnet'][0]['image'],
                f'/static/images/qr/{qr_filename}',
            )
            submissions = json.loads(submissions_path.read_text())
            self.assertEqual(submissions[0]['qr_filename'], qr_filename)


if __name__ == '__main__':
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

import app as app_module


class AdminApproveTests(unittest.TestCase):
    def test_approve_recovers_when_dojos_data_file_has_unexpected_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            dojos_data_path = tmpdir_path / 'dojos_data.json'
            submissions_path = tmpdir_path / 'dojo_submissions.json'

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

            app_module.DOJOS_DATA_FILE = dojos_data_path
            app_module.SUBMISSIONS_FILE = submissions_path
            app_module.data_loader.data_file = dojos_data_path

            self.addCleanup(setattr, app_module, 'DOJOS_DATA_FILE', original_dojos_data_file)
            self.addCleanup(setattr, app_module, 'SUBMISSIONS_FILE', original_submissions_file)
            self.addCleanup(setattr, app_module.data_loader, 'data_file', original_data_loader_file)

            client = app_module.app.test_client()
            with client.session_transaction() as session:
                session['paynym'] = next(iter(app_module.ADMIN_PAYNMS))

            response = client.post('/admin/dojos/pending-node-1/approve', follow_redirects=False)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/admin/dojos')

            submissions = json.loads(submissions_path.read_text())
            self.assertEqual(submissions[0]['status'], 'approved')

            dojos_data = json.loads(dojos_data_path.read_text())
            self.assertIn('mainnet', dojos_data)
            self.assertEqual(len(dojos_data['mainnet']), 2)
            self.assertTrue(any(item.get('name') == 'Pending Node' for item in dojos_data['mainnet']))


if __name__ == '__main__':
    unittest.main()

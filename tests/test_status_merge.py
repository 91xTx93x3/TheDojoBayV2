import unittest
from unittest.mock import patch

import app as app_module


class StatusMergeTests(unittest.TestCase):
    def test_new_directory_nodes_are_visible_before_health_check_completes(self):
        cached = {
            'mainnet': [],
            'testnet': [{
                'name': 'Existing',
                'status': 'Active',
                'checked_at': '2026-08-09 19:44:25',
            }],
            'stats': {},
        }
        current_testnet = [
            {'name': 'Existing', 'pairing': {'url': 'http://existing.onion'}},
            {'name': 'New Node', 'pairing': {'url': 'http://new-node.onion'}},
        ]

        with (
            patch.object(app_module, 'mainnet_dojos', []),
            patch.object(app_module, 'testnet_dojos', current_testnet),
        ):
            merged = app_module._merge_status_with_directory(cached)

        self.assertEqual(
            [entry['name'] for entry in merged['testnet']],
            ['Existing', 'New Node'],
        )
        self.assertEqual(merged['testnet'][0]['status'], 'Active')
        self.assertEqual(merged['testnet'][1]['status'], 'Checking')
        self.assertEqual(merged['stats']['testnet_total'], 2)
        self.assertEqual(merged['stats']['testnet_active'], 1)


if __name__ == '__main__':
    unittest.main()

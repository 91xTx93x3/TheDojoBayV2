import unittest
import sys
from types import ModuleType
from unittest.mock import Mock, patch

requests = ModuleType("requests")


class RequestException(Exception):
    pass


class ConnectionError(RequestException):
    pass


class ConnectTimeout(RequestException):
    pass


requests.RequestException = RequestException
requests.ConnectionError = ConnectionError
requests.ConnectTimeout = ConnectTimeout
requests.get = Mock()
sys.modules.setdefault("requests", requests)

from checker import DojoChecker


class DojoCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = DojoChecker(
            {"http": "socks5h://127.0.0.1:9050"},
            timeout=45,
        )

    @patch("checker.requests.get")
    def test_retries_a_transient_tor_failure(self, get):
        response = Mock(status_code=301, headers={"X-Dojo-Version": "1.29.2"})
        get.side_effect = [requests.ConnectionError(), response]

        result = self.checker.check_dojo({
            "name": "Transient",
            "pairing": {"url": "http://transient.onion/v2"},
        })

        self.assertEqual(result["status"], "Active")
        self.assertEqual(result["dojo_version"], "1.29.2")
        self.assertNotIn("error", result)
        self.assertEqual(get.call_count, 2)

    @patch("checker.requests.get")
    def test_marks_node_inactive_after_two_failures(self, get):
        get.side_effect = requests.ConnectTimeout()

        result = self.checker.check_dojo({
            "name": "Offline",
            "pairing": {"url": "http://offline.onion/v2"},
        })

        self.assertEqual(result["status"], "Inactive")
        self.assertEqual(result["error"], "ConnectTimeout")
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()

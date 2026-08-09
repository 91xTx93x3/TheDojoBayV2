import base64
import hashlib
import hmac
import json
import struct
import unittest

import base58
import coincurve

import app as app_module
from auth47 import generate_challenge, verify_signature
from bip47_verify import (
    _bitcoin_msg_hash,
    build_legacy_pairing_signing_message,
    build_pairing_signing_message,
    canonicalize_pairing_details,
    derive_notification_address,
    parse_armored_signed_message,
    verify_pairing_signature,
)


SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def make_payment_identity(secret_number=1):
    parent_secret = secret_number.to_bytes(32, "big")
    parent_public = coincurve.PrivateKey(parent_secret).public_key.format(compressed=True)
    chain_code = bytes([secret_number + 10]) * 32
    payload = b"\x47\x01\x00" + parent_public + chain_code + (b"\x00" * 13)
    payment_code = base58.b58encode_check(payload).decode()

    digest = hmac.new(
        chain_code,
        parent_public + struct.pack(">I", 0),
        hashlib.sha512,
    ).digest()
    child_number = (secret_number + int.from_bytes(digest[:32], "big")) % SECP256K1_ORDER
    return payment_code, coincurve.PrivateKey(child_number.to_bytes(32, "big"))


def sign_message(private_key, message):
    digest = _bitcoin_msg_hash(message)
    recoverable = private_key.sign_recoverable(digest, hasher=None)
    header = bytes([27 + 4 + recoverable[64]])
    return base64.b64encode(header + recoverable[:64]).decode()


class BIP47SigningTests(unittest.TestCase):
    def setUp(self):
        self.payment_code, self.notification_key = make_payment_identity()
        self.pairing = json.dumps({
            "pairing": {
                "type": "dojo.api",
                "version": "1.26.0",
                "apikey": "78945612",
                "url": "http://example.onion/v2",
            },
            "explorer": {
                "type": "explorer.btc_rpc_explorer",
                "url": "http://explorer.onion",
            },
        }, separators=(",", ":"))

    def test_builds_canonical_bip47_bound_message(self):
        canonical = canonicalize_pairing_details(self.pairing)
        message = build_pairing_signing_message(self.pairing, self.payment_code)

        self.assertEqual(
            message,
            f"{canonical}\nBIP47:\n{self.payment_code}",
        )
        self.assertEqual(
            build_legacy_pairing_signing_message(self.pairing, self.payment_code),
            f"{canonical}\n\nBIP47:\n{self.payment_code}",
        )

    def test_verifies_compact_signature_against_notification_address(self):
        message = build_pairing_signing_message(self.pairing, self.payment_code)
        signature = sign_message(self.notification_key, message)

        self.assertTrue(verify_pairing_signature(self.payment_code, message, signature))
        self.assertTrue(derive_notification_address(self.payment_code).startswith("1"))

        other_code, _ = make_payment_identity(2)
        self.assertFalse(verify_pairing_signature(other_code, message, signature))

    def test_accepts_both_armored_signature_markers_and_rejects_changed_message(self):
        message = build_pairing_signing_message(self.pairing, self.payment_code)
        signature = sign_message(self.notification_key, message)

        for marker in ("BEGIN SIGNATURE", "BEGIN BITCOIN SIGNATURE"):
            armored = (
                "-----BEGIN BITCOIN SIGNED MESSAGE-----\n"
                f"{message}\n"
                f"-----{marker}-----\n"
                "Version: Bitcoin-qt (1.0)\n\n"
                f"{signature}\n"
                "-----END BITCOIN SIGNATURE-----"
            )
            parsed_message, parsed_signature = parse_armored_signed_message(armored)
            self.assertEqual(parsed_message, message)
            self.assertEqual(parsed_signature, signature)
            self.assertTrue(verify_pairing_signature(self.payment_code, message, armored))
            self.assertFalse(verify_pairing_signature(self.payment_code, message + " ", armored))

    def test_auth47_verifies_the_exact_server_challenge(self):
        challenge = generate_challenge("https://dojobay.pw/api/auth47/verify")
        signature = sign_message(self.notification_key, challenge.auth47_uri)

        self.assertTrue(verify_signature(challenge.challenge_id, self.payment_code, signature))
        self.assertFalse(verify_signature(challenge.challenge_id, self.payment_code, signature[:-1] + "A"))

    def test_signing_message_endpoint_uses_authenticated_payment_code(self):
        client = app_module.app.test_client()
        with client.session_transaction() as session:
            session["paynym"] = self.payment_code

        response = client.post(
            "/api/pairing-signing-message",
            json={"pairing_details": self.pairing},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(
            body["message"],
            build_pairing_signing_message(self.pairing, self.payment_code),
        )
        self.assertEqual(body["scheme"], "bip47-bound-v2")

if __name__ == "__main__":
    unittest.main()

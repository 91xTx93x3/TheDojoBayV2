"""
BIP47 notification address derivation and BIP-137 message signature verification.

Verifies that a message (e.g. pairing details) was signed with the private key
corresponding to the BIP47 notification address of a given payment code.

Dependencies: coincurve (secp256k1), base58 — both already in the venv.
"""

import base64
import hashlib
import hmac as _hmac
import struct

import base58
import coincurve
from bitcoinutils.setup import setup as _btc_setup
from bitcoinutils.keys import PublicKey as _BTCPublicKey

_btc_setup('mainnet')


# ---------------------------------------------------------------------------
# Payment code parsing
# ---------------------------------------------------------------------------

def _decode_payment_code(payment_code: str) -> tuple[bytes, bytes]:
    """
    Base58Check-decode a BIP47 payment code and return (pubkey_33, chain_code_32).

    Encoded structure (81 bytes before checksum):
      [0]     0x47  – Base58Check prefix byte
      [1]     0x01  – BIP47 protocol version
      [2]     0x00  – feature bits
      [3:36]        – compressed public key (33 bytes)
      [36:68]       – chain code (32 bytes)
      [68:81]       – reserved zeros (13 bytes)
    """
    try:
        raw = base58.b58decode_check(payment_code)
    except Exception as exc:
        raise ValueError(f"Invalid payment code: {exc}") from exc

    if len(raw) < 68:
        raise ValueError(f"Payment code payload too short: {len(raw)} bytes")

    pubkey = raw[3:36]
    chain_code = raw[36:68]
    return pubkey, chain_code


# ---------------------------------------------------------------------------
# BIP32 public child key derivation (non-hardened)
# ---------------------------------------------------------------------------

def _bip32_public_child(pubkey_bytes: bytes, chain_code: bytes, index: int) -> bytes:
    """Return the compressed child public key at *index* (non-hardened, index < 2^31)."""
    data = pubkey_bytes + struct.pack(">I", index)
    I = _hmac.new(chain_code, data, hashlib.sha512).digest()
    IL = I[:32]                                       # key tweak scalar
    # child_pub = parent_pub + IL*G  (EC point addition)
    tweak_pub = coincurve.PublicKey.from_secret(IL)
    parent_pub = coincurve.PublicKey(pubkey_bytes)
    child_pub = coincurve.PublicKey.combine_keys([parent_pub, tweak_pub])
    return child_pub.format(compressed=True)


# ---------------------------------------------------------------------------
# P2PKH address
# ---------------------------------------------------------------------------

def _pubkey_to_p2pkh(pubkey_bytes: bytes) -> str:
    """Return the mainnet P2PKH address for a compressed public key."""
    return _BTCPublicKey(pubkey_bytes.hex()).get_address().to_string()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def derive_notification_address(payment_code: str) -> str:
    """
    Return the BIP47 notification address for *payment_code*.

    The notification address is the P2PKH address of the BIP32 public child key
    at index 0, derived from the payment code's stored public key and chain code.
    """
    pubkey, chain_code = _decode_payment_code(payment_code)
    child_pubkey = _bip32_public_child(pubkey, chain_code, 0)
    return _pubkey_to_p2pkh(child_pubkey)


# ---------------------------------------------------------------------------
# BIP-137 message signature verification
# ---------------------------------------------------------------------------

_BITCOIN_MSG_PREFIX = b"\x18Bitcoin Signed Message:\n"


def _varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def _bitcoin_msg_hash(message: str) -> bytes:
    """Double-SHA256 of the Bitcoin magic-prefixed *message*."""
    msg_bytes = message.encode("utf-8")
    prefixed = _BITCOIN_MSG_PREFIX + _varint(len(msg_bytes)) + msg_bytes
    return hashlib.sha256(hashlib.sha256(prefixed).digest()).digest()


def verify_pairing_signature(payment_code: str, message: str, signature_b64: str) -> bool:
    """
    Return True if *message* was signed by the BIP47 notification address of
    *payment_code* using BIP-137 Bitcoin message signing.

    *signature_b64* is the standard base64-encoded compact signature (65 bytes):
      byte[0]: recovery flag (27–34)
      bytes[1:65]: compact ECDSA (r‖s, 32+32 bytes)
    """
    try:
        sig_bytes = base64.b64decode(signature_b64)
        if len(sig_bytes) != 65:
            return False

        rec_byte = sig_bytes[0]
        if not (27 <= rec_byte <= 34):
            return False

        compressed = rec_byte >= 31
        rec_id = (rec_byte - (31 if compressed else 27)) & 0x01

        msg_hash = _bitcoin_msg_hash(message)

        # coincurve recoverable signature format: 64 bytes (r‖s) + rec_id byte at the END
        rec_sig = sig_bytes[1:] + bytes([rec_id])
        recovered_pub = coincurve.PublicKey.from_signature_and_message(
            rec_sig,
            msg_hash,
            hasher=None,
        )

        pub_bytes = recovered_pub.format(compressed=compressed)
        recovered_address = _pubkey_to_p2pkh(pub_bytes)
        notification_address = derive_notification_address(payment_code)
        return recovered_address == notification_address

    except Exception:
        return False

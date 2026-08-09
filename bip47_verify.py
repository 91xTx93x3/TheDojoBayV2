"""
BIP47 notification address derivation and BIP-137 message signature verification.

Verifies that a message (e.g. pairing details) was signed with the private key
corresponding to the BIP47 notification address of a given payment code.

Dependencies: coincurve (secp256k1), base58 — both already in the venv.
"""

import base64
import hashlib
import hmac as _hmac
import json
import struct

import base58
import coincurve
from bitcoinutils.setup import setup as _btc_setup
from bitcoinutils.keys import PublicKey as _BTCPublicKey

_btc_setup('mainnet')

PAIRING_SIGNATURE_SCHEME = "bip47-bound-v1"


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

    if len(raw) != 81:
        raise ValueError(f"Invalid payment code payload length: {len(raw)} bytes")
    if raw[:3] != b"\x47\x01\x00":
        raise ValueError("Unsupported payment code prefix, version, or features")
    if raw[3] not in (2, 3):
        raise ValueError("Payment code contains an invalid compressed public key")
    if raw[68:] != b"\x00" * 13:
        raise ValueError("Payment code reserved bytes must be zero")

    pubkey = raw[3:36]
    chain_code = raw[36:68]
    try:
        coincurve.PublicKey(pubkey)
    except ValueError as exc:
        raise ValueError("Payment code contains an invalid public key") from exc
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


def canonicalize_pairing_details(pairing_details: str) -> str:
    """Return the standard, deterministic JSON representation of a pairing payload."""
    try:
        payload = json.loads(pairing_details)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Pairing details must be valid JSON") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("pairing"), dict):
        raise ValueError('Pairing details must contain a "pairing" object')
    if "explorer" in payload and not isinstance(payload["explorer"], dict):
        raise ValueError('"explorer" must be an object')

    return json.dumps(payload, indent=2, ensure_ascii=False)


def build_pairing_signing_message(pairing_details: str, payment_code: str) -> str:
    """Bind canonical pairing JSON to the authenticated BIP47 payment code."""
    _decode_payment_code(payment_code)
    canonical_pairing = canonicalize_pairing_details(pairing_details)
    return f"{canonical_pairing}\n\nBIP47:\n{payment_code}"


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


def parse_armored_signed_message(armored: str) -> tuple[str, str]:
    """Extract the message and compact signature from common Bitcoin armor variants."""
    lines = armored.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if not lines or lines[0].strip() != "-----BEGIN BITCOIN SIGNED MESSAGE-----":
        raise ValueError("Not an armored Bitcoin signed message")

    signature_markers = {
        "-----BEGIN SIGNATURE-----",
        "-----BEGIN BITCOIN SIGNATURE-----",
    }
    try:
        signature_start = next(
            index for index, line in enumerate(lines)
            if line.strip() in signature_markers
        )
    except StopIteration as exc:
        raise ValueError("Missing Bitcoin signature marker") from exc

    message = "\n".join(lines[1:signature_start])
    signature = ""
    for line in reversed(lines[signature_start + 1:]):
        candidate = line.strip()
        if not candidate or candidate.startswith("-----END") or ":" in candidate:
            continue
        try:
            decoded = base64.b64decode(candidate, validate=True)
        except (ValueError, TypeError):
            continue
        if len(decoded) == 65:
            signature = candidate
            break

    if not signature:
        raise ValueError("Missing compact BIP-137 signature")
    return message, signature


def verify_pairing_signature(payment_code: str, message: str, signature_b64: str) -> bool:
    """
    Return True if *message* was signed by the BIP47 notification address of
    *payment_code* using BIP-137 Bitcoin message signing.

    *signature_b64* is the standard base64-encoded compact signature (65 bytes):
      byte[0]: recovery flag (27–34)
      bytes[1:65]: compact ECDSA (r‖s, 32+32 bytes)
    """
    try:
        if signature_b64.startswith("-----BEGIN BITCOIN SIGNED MESSAGE-----"):
            armored_message, signature_b64 = parse_armored_signed_message(signature_b64)
            if armored_message != message:
                return False

        sig_bytes = base64.b64decode(signature_b64, validate=True)
        if len(sig_bytes) != 65:
            return False

        rec_byte = sig_bytes[0]
        if not (27 <= rec_byte <= 34):
            return False

        header = rec_byte - 27
        compressed = bool(header & 4)
        rec_id = header & 3

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

"""Auth47 challenge generation and verification for PayNym/BIP47 wallets.

Protocol flow:
1. Server generates nonce → builds Auth47 URI →  shows as QR
2. User scans QR with Samourai/Ashigaru: PayNym → ⋮ → Auth47
3. Wallet signs the URI, shows the compact signature (BIP-137)
4. User pastes payment code + signature into the web form
5. Server verifies signature → creates session

Auth47 URI format:
    auth47://<nonce>?c=<callback_url>&e=<expiry_unix_timestamp>

References:
    https://samouraiwallet.com/paynym
    https://github.com/bitcoin/bips/blob/master/bip-0047.mediawiki   (BIP-47)
    https://github.com/bitcoin/bips/blob/master/bip-0137.mediawiki   (BIP-137)
"""

import secrets
import qrcode
import io
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from bip47_verify import verify_pairing_signature


# In-memory challenge store  { challenge_id → Auth47Challenge }
# Challenges expire after TTL_MINUTES; store is cleaned up on every generation.
_challenges: Dict[str, "Auth47Challenge"] = {}
TTL_MINUTES = 15


@dataclass
class Auth47Challenge:
    challenge_id: str
    nonce: str
    callback_url: str
    expires_at: datetime  # timezone-aware UTC
    completed: bool = False
    authenticated_payment_code: Optional[str] = None

    @property
    def auth47_uri(self) -> str:
        ts = int(self.expires_at.timestamp())
        return f"auth47://{self.nonce}?c={self.callback_url}&e={ts}"

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def seconds_remaining(self) -> int:
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))

    def to_dict(self) -> dict:
        return {
            "challenge_id": self.challenge_id,
            "auth47_uri": self.auth47_uri,
            "nonce": self.nonce,
            "expires_at": self.expires_at.isoformat(),
            "seconds_remaining": self.seconds_remaining(),
        }


def generate_challenge(callback_url: str) -> Auth47Challenge:
    """Generate a fresh Auth47 challenge and store it in memory."""
    nonce = secrets.token_hex(16)          # 32 hex chars → compact QR
    challenge_id = secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TTL_MINUTES)

    challenge = Auth47Challenge(
        challenge_id=challenge_id,
        nonce=nonce,
        callback_url=callback_url,
        expires_at=expires_at,
    )
    _challenges[challenge_id] = challenge
    _cleanup_expired()
    return challenge


def get_challenge(challenge_id: str) -> Optional[Auth47Challenge]:
    """Return challenge if it exists and has not expired."""
    ch = _challenges.get(challenge_id)
    if ch:
        if ch.is_expired():
            del _challenges[challenge_id]
            return None
        return ch
    return None


def get_challenge_by_nonce(nonce: str) -> Optional[Auth47Challenge]:
    """Return challenge looked up by nonce value (used for wallet callbacks)."""
    for ch in list(_challenges.values()):
        if ch.nonce == nonce:
            if ch.is_expired():
                _challenges.pop(ch.challenge_id, None)
                return None
            return ch
    return None


def verify_signature(challenge_id: str, payment_code: str, signature: str) -> bool:
    """
    Verify an Auth47 signature produced by Samourai/Ashigaru.

    The wallet signs the Auth47 URI (auth47://<nonce>?c=…&e=…) using the
    private key of the BIP47 notification address derived from the payment code.
    The resulting signature is a BIP-137 compact base64-encoded signature.

    The signed message must be the exact server-generated Auth47 URI.
    """
    # Lookup: try challenge_id first, then nonce (wallet sends the nonce)
    challenge = get_challenge(challenge_id) or get_challenge_by_nonce(challenge_id)
    if not challenge:
        return False

    if not _is_valid_payment_code(payment_code) or not signature:
        return False

    return verify_pairing_signature(
        payment_code,
        challenge.auth47_uri,
        signature,
    )


def complete_challenge(challenge_id: str, payment_code: str) -> bool:
    """Mark a challenge as completed after successful wallet signature.
    Accepts either challenge_id or nonce as the first argument.
    """
    ch = _challenges.get(challenge_id) or get_challenge_by_nonce(challenge_id)
    if ch and not ch.is_expired():
        ch.completed = True
        ch.authenticated_payment_code = payment_code
        return True
    return False


def consume_challenge(challenge_id: str) -> Optional[str]:
    """Remove a completed challenge and return its payment code (for finalize step)."""
    ch = _challenges.pop(challenge_id, None)
    if ch and ch.completed:
        return ch.authenticated_payment_code
    return None


def generate_qr_png_b64(data: str) -> str:
    """Return a base64-encoded PNG of a QR code for *data*."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#e74c3c", back_color="#111111")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── helpers ────────────────────────────────────────────────────────────────────

def _is_valid_payment_code(code: str) -> bool:
    """BIP-47 payment codes start with PM8T and are 70-120 chars."""
    if not code or not isinstance(code, str):
        return False
    if not code.startswith("PM8T"):
        return False
    if not (70 <= len(code) <= 120):
        return False
    return True


def _cleanup_expired() -> None:
    expired = [k for k, v in list(_challenges.items()) if v.is_expired()]
    for k in expired:
        del _challenges[k]

"""Offline license validation for Vinemap Teams.

Individual developers get full features with no license. Teams keys (VMP1…)
unlock shared graph server features and are validated locally with Ed25519.

Install signing/verify support: pip install vinemap[license]
"""

import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Literal, Optional

LICENSE_PREFIX = "VMP1"
LICENSE_DIR = os.path.join(os.path.expanduser("~"), ".vinemap")
LICENSE_FILE = os.path.join(LICENSE_DIR, "license.json")

# Production: replace with your issuance public key before selling licenses.
# Tests use their own keypair in test_license.py.
LICENSE_PUBLIC_KEY_HEX = (
    "85b86af69bcbab04ac35a8693078d399caf248a8ed66fda3980f0894aa56148e"
)

Tier = Literal["free", "pro", "teams"]
# Individual developers: no practical file cap. Teams licensing gates org features only.
DEFAULT_MAX_FILES = 1_000_000
TIER_MAX_FILES: dict[Tier, int] = {
    "free": DEFAULT_MAX_FILES,
    "pro": DEFAULT_MAX_FILES,
    "teams": DEFAULT_MAX_FILES,
}


@dataclass(frozen=True)
class LicenseInfo:
    tier: Tier
    expires_at: Optional[int]  # unix seconds, None = no expiry
    subject: str = ""

    def is_valid(self) -> bool:
        if self.expires_at is not None and time.time() > self.expires_at:
            return False
        return self.tier in ("pro", "teams")


def _load_ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise SystemExit(
            "License support requires: pip install vinemap[license]\n"
            "(adds the cryptography package for Ed25519 verification)"
        ) from exc
    return Ed25519PublicKey


def _public_key():
    Ed25519PublicKey = _load_ed25519()
    raw = bytes.fromhex(LICENSE_PUBLIC_KEY_HEX)
    return Ed25519PublicKey.from_public_bytes(raw)


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_and_verify_key(key: str, public_key_hex: Optional[str] = None) -> LicenseInfo:
    """Parse a VMP1 license key and verify its Ed25519 signature."""
    parts = key.strip().split(".")
    if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
        raise ValueError("invalid license key format (expected VMP1.<payload>.<sig>)")

    payload_bytes = _b64url_decode(parts[1])
    signature = _b64url_decode(parts[2])

    Ed25519PublicKey = _load_ed25519()
    if public_key_hex:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
    else:
        pub = _public_key()

    pub.verify(signature, payload_bytes)

    data = json.loads(payload_bytes.decode("utf-8"))
    tier = data.get("tier")
    if tier not in ("pro", "teams"):
        raise ValueError(f"unknown tier: {tier!r}")

    exp = data.get("exp")
    expires_at = int(exp) if exp is not None else None
    if expires_at is not None and time.time() > expires_at:
        raise ValueError("license expired")

    return LicenseInfo(tier=tier, expires_at=expires_at, subject=str(data.get("sub", "")))


def sign_license_payload(
    payload: dict,
    private_key_hex: str,
) -> str:
    """Build a VMP1 key (used by tools/issue_license.py on the license server)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = priv.sign(body)
    return f"{LICENSE_PREFIX}.{_b64url_encode(body)}.{_b64url_encode(sig)}"


def save_license(key: str, info: LicenseInfo) -> None:
    os.makedirs(LICENSE_DIR, exist_ok=True)
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "key": key.strip(),
                "tier": info.tier,
                "expires_at": info.expires_at,
                "subject": info.subject,
                "activated_at": int(time.time()),
            },
            f,
            indent=2,
        )


def load_stored_license() -> Optional[LicenseInfo]:
    if not os.path.isfile(LICENSE_FILE):
        return None
    try:
        with open(LICENSE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("key", "")
        if not key:
            return None
        return parse_and_verify_key(key)
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def current_tier() -> Tier:
    info = load_stored_license()
    if info and info.is_valid():
        return info.tier
    return "free"


def max_files_for_tier(tier: Optional[Tier] = None) -> int:
    tier = tier or current_tier()
    return TIER_MAX_FILES.get(tier, TIER_MAX_FILES["free"])


def effective_max_files(requested: Optional[int]) -> int:
    """Return the effective file limit for indexing (no cap for individual use)."""
    cap = max_files_for_tier()
    if requested is None:
        return cap
    return min(requested, cap)


def require_pro(_feature: str) -> None:
    """No-op — all individual features are free; kept for CLI compatibility."""
    return


def require_teams(feature: str) -> None:
    tier = current_tier()
    if tier == "teams":
        return
    print(
        f"error: {feature} requires Vinemap Teams.\n"
        "  Activate: vinemap license activate <teams-key>\n"
        "  Contact:  https://vinemap.xyz#pricing",
        file=sys.stderr,
    )
    sys.exit(1)


def license_status_text() -> str:
    info = load_stored_license()
    if info is None:
        return "tier: free (full features, no file limit)\nlicense: none (Teams keys for org use)"
    if info.tier == "teams" and info.is_valid():
        exp = "never" if info.expires_at is None else time.strftime(
            "%Y-%m-%d", time.localtime(info.expires_at)
        )
        return (
            f"tier: {info.tier}\n"
            f"expires: {exp}\n"
            f"subject: {info.subject or '(anonymous)'}"
        )
    if not info.is_valid():
        return "tier: free (stored license expired or invalid)\nlicense: invalid"
    exp = "never" if info.expires_at is None else time.strftime(
        "%Y-%m-%d", time.localtime(info.expires_at)
    )
    return (
        f"tier: {info.tier}\n"
        f"expires: {exp}\n"
        f"subject: {info.subject or '(anonymous)'}"
    )

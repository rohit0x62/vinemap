import time

import pytest

from vinemap.license import (
    LICENSE_FILE,
    TIER_MAX_FILES,
    current_tier,
    effective_max_files,
    max_files_for_tier,
    parse_and_verify_key,
    save_license,
    sign_license_payload,
)

# Test-only keypair — not used for production issuance.
TEST_PUB = "85b86af69bcbab04ac35a8693078d399caf248a8ed66fda3980f0894aa56148e"
TEST_PRIV = "088ee4c67b4666c11fb02cea94d3356c628f2853c63c8b1f210dae9f0dc716f2"


pytest.importorskip("cryptography")


@pytest.fixture
def license_home(tmp_path, monkeypatch):
    lic_dir = tmp_path / ".vinemap"
    lic_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("vinemap.license.LICENSE_DIR", str(lic_dir))
    monkeypatch.setattr("vinemap.license.LICENSE_FILE", str(lic_dir / "license.json"))
    return lic_dir


def test_sign_and_verify_pro_key():
    payload = {"tier": "pro", "sub": "test-user", "exp": int(time.time()) + 3600}
    key = sign_license_payload(payload, TEST_PRIV)
    info = parse_and_verify_key(key, public_key_hex=TEST_PUB)
    assert info.tier == "pro"
    assert info.subject == "test-user"


def test_expired_key_rejected():
    payload = {"tier": "pro", "exp": int(time.time()) - 10}
    key = sign_license_payload(payload, TEST_PRIV)
    with pytest.raises(ValueError, match="expired"):
        parse_and_verify_key(key, public_key_hex=TEST_PUB)


def test_activate_changes_tier(license_home, monkeypatch):
    monkeypatch.setattr("vinemap.license.LICENSE_PUBLIC_KEY_HEX", TEST_PUB)
    payload = {"tier": "pro", "exp": int(time.time()) + 3600}
    key = sign_license_payload(payload, TEST_PRIV)
    info = parse_and_verify_key(key, public_key_hex=TEST_PUB)
    save_license(key, info)
    assert current_tier() == "pro"
    assert max_files_for_tier() == TIER_MAX_FILES["pro"]


def test_effective_max_files_no_cap_for_individuals(monkeypatch):
    monkeypatch.setattr("vinemap.license.current_tier", lambda: "free")
    assert effective_max_files(10_000) == 10_000
    assert effective_max_files(None) == TIER_MAX_FILES["free"]


def test_effective_max_files_teams_same_cap(monkeypatch):
    monkeypatch.setattr("vinemap.license.current_tier", lambda: "teams")
    assert effective_max_files(10_000) == 10_000
    assert effective_max_files(None) == TIER_MAX_FILES["teams"]

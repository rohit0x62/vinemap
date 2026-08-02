#!/usr/bin/env python3
"""Issue Vinemap license keys (run on your license server, NOT in end-user installs).

Requires VINEMAP_LICENSE_PRIVATE_KEY (hex Ed25519 private key matching the
public key embedded in vinemap/license.py).

Example:
  export VINEMAP_LICENSE_PRIVATE_KEY=<hex>
  python tools/issue_license.py --tier pro --days 365 --subject user@example.com
"""

import argparse
import os
import sys
import time

# Allow running from repo root: engine/tools/issue_license.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vinemap.license import sign_license_payload  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a Vinemap license key")
    parser.add_argument("--tier", choices=("pro", "teams"), default="pro")
    parser.add_argument("--days", type=int, default=365, help="validity in days (0 = no expiry)")
    parser.add_argument("--subject", default="", help="customer id or email hash")
    args = parser.parse_args()

    priv_hex = os.environ.get("VINEMAP_LICENSE_PRIVATE_KEY", "").strip()
    if not priv_hex:
        print("error: set VINEMAP_LICENSE_PRIVATE_KEY to your Ed25519 private key (hex)", file=sys.stderr)
        sys.exit(1)

    payload = {"tier": args.tier, "sub": args.subject}
    if args.days > 0:
        payload["exp"] = int(time.time()) + args.days * 86400

    key = sign_license_payload(payload, priv_hex)
    print(key)


if __name__ == "__main__":
    main()

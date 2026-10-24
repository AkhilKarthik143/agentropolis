#!/usr/bin/env python3
"""Inspect a v2 payment challenge, or explicitly execute one testnet purchase."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations.coinbase_x402 import X402HTTPClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-testnet", action="store_true")
    parser.add_argument("--authorization-id", default="")
    parser.add_argument("--max-cents", type=int, default=1)
    args = parser.parse_args()
    resource, recipient = os.getenv("X402_RESOURCE_URL", ""), os.getenv("X402_PAY_TO", "")
    if os.getenv("X402_MODE") != "testnet" or os.getenv("X402_NETWORK") not in {"base-sepolia", "eip155:84532"} or not resource or not recipient:
        print("NOT VERIFIED: configure testnet mode, Base Sepolia, resource URL and approved recipient.", file=sys.stderr)
        return 2
    try:
        origin = urlparse(resource)
        signer = None
        if args.execute_testnet:
            key = os.getenv("X402_WALLET_PRIVATE_KEY", "")
            if not key or key.startswith("your_") or not args.authorization_id:
                print("NOT VERIFIED: testnet execution requires a throwaway wallet and --authorization-id.", file=sys.stderr)
                return 2
            signer = X402HTTPClient.sdk_signer(key)
        buyer = X402HTTPClient(allowed_origin=f"{origin.scheme}://{origin.netloc}", pay_to=recipient, signer=signer,
            per_call_cap_cents=int(os.getenv("X402_PER_CALL_CAP_CENTS", "100")), daily_cap_cents=int(os.getenv("X402_DAILY_CAP_CENTS", "500")))
        if args.execute_testnet:
            result = buyer.purchase(resource, authorized_cents=args.max_cents, idempotency_key=args.authorization_id)
            print(json.dumps({key: value for key, value in result.items() if key != "service"}))
        else:
            challenge = buyer.inspect(resource, authorized_cents=args.max_cents)
            print(json.dumps({"mode": "testnet", "scope": "challenge_only", "settlement_verified": False, "accepted_options": len(challenge["accepts"])}))
        return 0
    except Exception as exc:
        print(f"NOT VERIFIED: x402 check failed ({type(exc).__name__}); do not retry a signed uncertain submission.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

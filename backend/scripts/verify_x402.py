#!/usr/bin/env python3
"""Credential-gated x402 testnet verification placeholder."""
import os
import sys

network = os.getenv("X402_NETWORK", "")
mode = os.getenv("X402_MODE", "")
wallet = os.getenv("X402_WALLET_PRIVATE_KEY", "")
if mode != "testnet" or network not in {"base-sepolia", "ethereum-sepolia", "solana-devnet"}:
    print("NOT VERIFIED: set X402_MODE=testnet and a known testnet X402_NETWORK.", file=sys.stderr)
    raise SystemExit(2)
if not wallet or wallet.startswith("your_"):
    print("NOT VERIFIED: set a throwaway X402_WALLET_PRIVATE_KEY for the testnet run.", file=sys.stderr)
    raise SystemExit(2)
print("Credential detected; live x402 verification is not run by the offline build.")
raise SystemExit(3)

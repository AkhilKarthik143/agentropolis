#!/usr/bin/env python3
"""Verify one small fake-money Nessie sandbox flow without printing secrets."""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.integrations.nessie import NessieBank

key = os.getenv("NESSIE_API_KEY", "")
mode = os.getenv("NESSIE_MODE", "")
if not key or key.startswith("your_"):
    print("NOT VERIFIED: set NESSIE_API_KEY to a Capital One Nessie sandbox key and rerun.", file=sys.stderr)
    raise SystemExit(2)
if mode != "sandbox":
    print("Refusing to run: set NESSIE_MODE=sandbox.", file=sys.stderr)
    raise SystemExit(2)
try:
    bank = NessieBank(api_key=key, base_url=os.getenv("NESSIE_BASE_URL", "https://api.nessieisreal.com"), mode="sandbox")
    payer_customer = bank.create_customer("Agentropolis", "Buyer")
    payee_customer = bank.create_customer("Agentropolis", "Supplier")
    payer_account = bank.create_sandbox_account(payer_customer, nickname="Agentropolis buyer")
    payee_account = bank.create_sandbox_account(payee_customer, nickname="Agentropolis supplier")
    deposit = bank.deposit(payer_account, 100, "Agentropolis verification funding")
    transfer = bank.transfer(payer_account, payee_account, 1, "Agentropolis verification transfer")
    history = bank.history(payee_account)
except Exception as exc:
    print(f"NOT VERIFIED: Nessie sandbox request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit(3) from exc

print(json.dumps({"mode": "sandbox", "payer_customer_id": payer_customer, "payee_customer_id": payee_customer, "payer_account_id": payer_account, "payee_account_id": payee_account, "deposit_id": deposit.get("_id") or deposit.get("id"), "transfer_id": transfer.get("_id") or transfer.get("id"), "history_records": len(history)}, sort_keys=True))


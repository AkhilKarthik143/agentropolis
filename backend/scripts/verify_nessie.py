#!/usr/bin/env python3
"""Nessie verification. Default: read-only; sandbox writes require CLI opt-in."""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations.nessie import NessieBank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-sandbox", action="store_true", help="Create fake customers/accounts and submit one fake one-cent transfer")
    args = parser.parse_args()
    key = os.getenv("NESSIE_API_KEY", "")
    if os.getenv("NESSIE_MODE") != "sandbox" or not key or key.startswith("your_"):
        print("NOT VERIFIED: configure NESSIE_MODE=sandbox and NESSIE_API_KEY.", file=sys.stderr)
        return 2
    bank = NessieBank(api_key=key, base_url=os.getenv("NESSIE_BASE_URL", "https://api.nessieisreal.com"))
    try:
        if not args.execute_sandbox:
            account = os.getenv("NESSIE_ACCOUNT_ID", "")
            if not account:
                print("NOT VERIFIED: set NESSIE_ACCOUNT_ID for the read-only check.", file=sys.stderr)
                return 2
            print(json.dumps({"mode": "sandbox", "scope": "read_only", "balance_cents": bank.balance_cents(account), "history_records": len(bank.history(account))}))
            return 0
        address = {"street_number": "1", "street_name": "Test Street", "city": "Testville", "state": "CA", "zip": "00000"}
        buyer = bank.create_customer("Agentropolis", "TestBuyer", address=address)
        seller = bank.create_customer("Agentropolis", "TestSeller", address=address)
        payer = bank.create_sandbox_account(buyer, nickname="Agentropolis verification buyer")
        payee = bank.create_sandbox_account(seller, nickname="Agentropolis verification seller")
        deposit = bank.deposit(payer, 100)
        transfer = bank.transfer(payer, payee, 1, "Agentropolis fake-money verification", f"verify-{uuid4().hex}")
        status = bank.get_transfer(transfer["_id"])
        print(json.dumps({"mode": "sandbox", "payer_account_id": payer, "payee_account_id": payee, "deposit_id": deposit["_id"], "transfer_id": transfer["_id"], "provider_status": status.get("status"), "settlement_verified": status.get("status") == "completed"}))
        return 0 if status.get("status") == "completed" else 3
    except Exception as exc:
        print(f"NOT VERIFIED: sandbox check failed ({type(exc).__name__}); inspect provider history before retrying writes.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

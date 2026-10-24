"""Capital One Nessie fake-money adapter; no production banking access.

Nessie does not document a server idempotency guarantee. An on-disk submission
journal prevents automatic re-submission, including after an uncertain timeout.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import urlparse

import httpx


class NessieError(RuntimeError):
    """Sanitized provider error: deliberately excludes credential-bearing URLs."""


class NessieUncertainError(NessieError):
    """The operation may have reached Nessie; investigate instead of resubmitting."""


@dataclass
class NessieBank:
    api_key: str | None = None
    base_url: str = "https://api.nessieisreal.com"
    mode: str = "sandbox"
    journal_path: str = ".data/nessie-submissions.sqlite3"
    client: httpx.Client | None = None

    def __post_init__(self) -> None:
        if self.mode != "sandbox":
            raise ValueError("Nessie adapter only permits sandbox mode")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != "api.nessieisreal.com" or parsed.query or parsed.username:
            raise ValueError("Nessie requires its official HTTPS sandbox endpoint")
        Path(self.journal_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.journal_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS nessie_submissions (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL, result TEXT)")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.api_key or self.api_key.startswith("your_"):
            raise NessieError("NESSIE_API_KEY is required for sandbox mode")
        try:
            request = self.client.request if self.client else httpx.request
            response = request(method, f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                params={"key": self.api_key}, headers={"Content-Type": "application/json"}, timeout=15, follow_redirects=False, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            raise NessieError(f"Nessie returned HTTP {exc.response.status_code}") from None
        except (httpx.RequestError, ValueError):
            raise NessieError("Nessie request failed or returned malformed JSON") from None

    @staticmethod
    def _created(data: Any) -> dict[str, Any]:
        obj = data.get("objectCreated", data) if isinstance(data, dict) else {}
        if not isinstance(obj, dict) or not (obj.get("_id") or obj.get("id")):
            raise NessieError("Nessie response has no provider object ID")
        return obj

    @staticmethod
    def _amount_body(amount_cents: int, **fields: Any) -> str:
        if type(amount_cents) is not int or amount_cents <= 0:
            raise ValueError("amount must be a positive integer number of cents")
        # Emit the exact decimal JSON number without authoritative float arithmetic.
        amount = format(Decimal(amount_cents) / Decimal(100), ".2f")
        return json.dumps(fields, separators=(",", ":"))[:-1] + ',"amount":' + amount + '}'

    def create_customer(self, first_name: str, last_name: str, *, address: dict[str, str] | None = None) -> str:
        if address is None:
            raise ValueError("Nessie sandbox customer requires an explicit test address")
        data = self._request("POST", "/customers", json={"first_name": first_name, "last_name": last_name, "address": address})
        obj = self._created(data)
        return str(obj.get("_id") or obj["id"])

    def create_sandbox_account(self, customer_id: str, account_type: str = "Checking", nickname: str = "Agentropolis") -> str:
        if account_type not in {"Checking", "Savings", "Credit Card"}:
            raise ValueError("unsupported Nessie account type")
        obj = self._created(self._request("POST", f"/customers/{customer_id}/accounts", json={"type": account_type, "nickname": nickname, "rewards": 0, "balance": 0}))
        return str(obj.get("_id") or obj["id"])

    def get_account(self, account_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/accounts/{account_id}")
        if not isinstance(data, dict) or "balance" not in data:
            raise NessieError("Nessie account response lacks a balance")
        return data

    def balance_cents(self, account_id: str) -> int:
        value = Decimal(str(self.get_account(account_id)["balance"])) * 100
        if not value.is_finite() or value != value.to_integral_value():
            raise NessieError("Nessie balance is not an exact minor currency amount")
        return int(value)

    def transfer(self, account_id: str, payee_id: str, amount_cents: int, description: str, idempotency_key: str | None = None) -> dict[str, Any]:
        if not idempotency_key:
            raise ValueError("a durable idempotency key is required for Nessie transfers")
        body = self._amount_body(amount_cents, medium="balance", payee_id=payee_id, description=f"{description} [{idempotency_key}]")
        fingerprint = hashlib.sha256(f"{account_id}:{body}".encode()).hexdigest()
        with sqlite3.connect(self.journal_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT fingerprint,state,result FROM nessie_submissions WHERE key=?", (idempotency_key,)).fetchone()
            if existing:
                if existing[0] != fingerprint:
                    raise ValueError("idempotency key reused for different transfer terms")
                if existing[1] == "submitted":
                    return json.loads(existing[2])
                raise NessieUncertainError("Transfer outcome uncertain; inspect provider history before any retry")
            conn.execute("INSERT INTO nessie_submissions VALUES (?,?,?,NULL)", (idempotency_key, fingerprint, "uncertain"))
        try:
            result = self._created(self._request("POST", f"/accounts/{account_id}/transfers", content=body))
        except NessieError:
            raise NessieUncertainError("Transfer submission failed or is uncertain; inspect provider history") from None
        with sqlite3.connect(self.journal_path) as conn:
            conn.execute("UPDATE nessie_submissions SET state='submitted',result=? WHERE key=?", (json.dumps(result), idempotency_key))
        return result

    def get_transfer(self, transfer_id: str) -> dict[str, Any]:
        result = self._request("GET", f"/transfers/{transfer_id}")
        if not isinstance(result, dict) or not result.get("_id"):
            raise NessieError("Nessie transfer lookup lacks an ID")
        return result

    def deposit(self, account_id: str, amount_cents: int, description: str = "Agentropolis sandbox funding") -> dict[str, Any]:
        return self._created(self._request("POST", f"/accounts/{account_id}/deposits", content=self._amount_body(amount_cents, medium="balance", description=description)))

    def create_account(self, business_id: str, opening_cents: int = 0) -> str:
        raise NessieError("Map the business to an explicit Nessie customer and sandbox account; no implicit mock account is created")

    def history(self, account_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/accounts/{account_id}/transfers")
        if not isinstance(data, list):
            raise NessieError("Nessie history response was not a list")
        return data


NessieBankingAdapter = NessieBank

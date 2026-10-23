from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.finance.banking import MockBank


@dataclass
class NessieBank:
    """Sandbox adapter seam. Live calls are intentionally opt-in and unverified here."""

    api_key: str | None = None
    base_url: str = "https://api.nessieisreal.com"
    mode: str = "sandbox"

    def __post_init__(self) -> None:
        if self.mode != "sandbox":
            raise ValueError("Nessie adapter only permits sandbox mode")
        self.mock = MockBank()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("NESSIE_API_KEY is required for sandbox mode")
        response = httpx.request(method, f"{self.base_url.rstrip('/')}/{path.lstrip('/')}", headers={"api-key": self.api_key, "Content-Type": "application/json"}, timeout=15, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def create_customer(self, first_name: str, last_name: str) -> str:
        data = self._request("POST", "/customers", json={"first_name": first_name, "last_name": last_name})
        return str(data.get("_id") or data.get("id"))

    def create_sandbox_account(self, customer_id: str, account_type: str = "Checking", nickname: str = "Agentropolis") -> str:
        data = self._request("POST", f"/customers/{customer_id}/accounts", json={"type": account_type, "nickname": nickname, "rewards": 0, "balance": 0})
        return str(data.get("_id") or data.get("id"))

    def transfer(self, account_id: str, payee_id: str, amount_cents: int, description: str, idempotency_key: str | None = None) -> dict[str, Any]:
        memo = f"{description} [{idempotency_key}]" if idempotency_key else description
        return self._request("POST", f"/accounts/{account_id}/transfers", json={"medium": "balance", "payee_id": payee_id, "amount": amount_cents / 100, "description": memo})

    def deposit(self, account_id: str, amount_cents: int, description: str = "Agentropolis sandbox funding") -> dict[str, Any]:
        if amount_cents <= 0:
            raise ValueError("deposit amount must be positive")
        return self._request("POST", f"/accounts/{account_id}/deposits", json={"medium": "balance", "amount": amount_cents / 100, "description": description})

    def create_account(self, business_id: str, opening_cents: int = 0) -> str:
        return self.mock.create_account(business_id, opening_cents)

    def history(self, account_id: str):
        if self.api_key:
            return self._request("GET", f"/accounts/{account_id}/transfers")
        return self.mock.history(account_id)


from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentReceipt:
    receipt_id: str
    amount_cents: int
    network: str
    tx_hash: str
    mode: str


class PaymentRail(Protocol):
    mode: str

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt: ...


class X402Adapter(PaymentRail, Protocol):
    """Adapter boundary for a paid agent-to-agent HTTP call."""


class MockX402:
    mode = "mock"

    def __init__(self, *, per_call_cap_cents: int = 2_500, daily_cap_cents: int = 10_000) -> None:
        self.per_call_cap_cents = per_call_cap_cents
        self.daily_cap_cents = daily_cap_cents
        self.spent_cents = 0
        self._receipts: dict[str, PaymentReceipt] = {}

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if not idempotency_key:
            raise ValueError("payment requires an idempotency key")
        if idempotency_key in self._receipts:
            receipt = self._receipts[idempotency_key]
            if receipt.amount_cents != amount_cents:
                raise ValueError("idempotency key reused for a different amount")
            return receipt
        if amount_cents <= 0 or amount_cents > self.per_call_cap_cents:
            raise ValueError("x402 per-call spend cap exceeded")
        if self.spent_cents + amount_cents > self.daily_cap_cents:
            raise ValueError("x402 daily spend cap exceeded")
        receipt = PaymentReceipt(f"receipt_{idempotency_key[:10]}", amount_cents, "mock-testnet", f"mocktx_{idempotency_key[:12]}", self.mode)
        self.spent_cents += amount_cents
        self._receipts[idempotency_key] = receipt
        return receipt


class X402Testnet:
    mode = "testnet"

    def __init__(self, network: str, *, per_call_cap_cents: int = 2_500, daily_cap_cents: int = 10_000) -> None:
        allowed = {"base-sepolia", "ethereum-sepolia", "solana-devnet"}
        if network not in allowed:
            raise ValueError("x402 adapter refuses unknown or mainnet networks")
        self.network = network
        self.per_call_cap_cents = per_call_cap_cents
        self.daily_cap_cents = daily_cap_cents
        self.spent_cents = 0

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if amount_cents > self.per_call_cap_cents or self.spent_cents + amount_cents > self.daily_cap_cents:
            raise ValueError("x402 spend cap exceeded")
        raise RuntimeError("Direct pay is unsupported for x402: use a payment-required HTTP resource and the guarded X402HTTPClient")


class X402Rail:
    def __init__(self, adapter: MockX402 | X402Testnet | None = None) -> None:
        self.adapter = adapter or MockX402()
        self.mode = self.adapter.mode

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        return self.adapter.pay(amount_cents, idempotency_key)


class NessieRail:
    mode = "nessie-sandbox"

    def __init__(self, bank: object, *, payer_account_id: str, payee_account_id: str) -> None:
        self.bank = bank
        self.payer_account_id = payer_account_id
        self.payee_account_id = payee_account_id

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if amount_cents <= 0:
            raise ValueError("Nessie payment amount must be positive")
        result = self.bank.transfer(self.payer_account_id, self.payee_account_id, amount_cents, "Agentropolis purchase", idempotency_key)
        transaction_id = result.get("_id") or result.get("id")
        if not transaction_id:
            raise RuntimeError("Nessie did not return a transaction ID; settlement is unconfirmed")
        confirmed = self.bank.get_transfer(str(transaction_id))
        if confirmed.get("status") != "completed":
            raise RuntimeError("Nessie transfer submitted but not completed; reconcile before ledger settlement")
        return PaymentReceipt(str(transaction_id), amount_cents, "nessie-sandbox", str(transaction_id), self.mode)


class FetRail:
    mode = "fetch-payment-protocol"

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        raise RuntimeError("FetRail delegates to the legacy payment protocol; no standalone rail is configured")


# An x402 purchase is an HTTP exchange, not an arbitrary transfer(amount).
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable
from urllib.parse import urlparse
import httpx

BASE_SEPOLIA = "eip155:84532"
BASE_SEPOLIA_USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"


class X402UncertainError(RuntimeError):
    pass


class X402HTTPClient:
    """Opt-in exact-USDC Base Sepolia buyer using the official v2 SDK signer.

    Recipient, asset, resource and caps are checked before signing. Submissions
    are durably reserved before sending; uncertain outcomes never auto-retry.
    Provider receipts require a successful testnet transaction receipt before
    the result is returned. The simulation never selects this client implicitly.
    """

    def __init__(self, *, allowed_origin: str, pay_to: str, signer: Callable[[dict[str, Any]], str] | None = None,
                 per_call_cap_cents: int = 100, daily_cap_cents: int = 500,
                 journal_path: str = ".data/x402-submissions.sqlite3", client: httpx.Client | None = None) -> None:
        origin = urlparse(allowed_origin)
        if origin.scheme != "https" or origin.username or origin.query or origin.fragment or origin.path not in {"", "/"}:
            raise ValueError("x402 origin must be an explicit HTTPS origin")
        if not re.fullmatch(r"0x[a-fA-F0-9]{40}", pay_to):
            raise ValueError("x402 requires an approved testnet recipient address")
        if not 0 < per_call_cap_cents <= daily_cap_cents:
            raise ValueError("invalid x402 spend caps")
        self.allowed_origin, self.pay_to = allowed_origin.rstrip("/"), pay_to
        self.signer, self.client = signer, client
        self.per_call_cap_cents, self.daily_cap_cents = per_call_cap_cents, daily_cap_cents
        self.journal_path = journal_path
        Path(journal_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(journal_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS x402_submissions (key TEXT PRIMARY KEY, fingerprint TEXT, day TEXT, amount_atomic INTEGER, status TEXT, result TEXT)")

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            request = self.client.request if self.client else httpx.request
            return request(method, url, timeout=15, follow_redirects=False, **kwargs)
        except httpx.HTTPError:
            raise X402UncertainError("x402 request failed; any signed submission must be reconciled") from None

    @staticmethod
    def _decode(header: str) -> dict[str, Any]:
        if not header or len(header) > 32000:
            raise ValueError("missing or oversized x402 header")
        value = json.loads(base64.b64decode(header, validate=True))
        if not isinstance(value, dict):
            raise ValueError("invalid x402 header object")
        return value

    def inspect(self, url: str, *, authorized_cents: int) -> dict[str, Any]:
        parsed = urlparse(url)
        if f"{parsed.scheme}://{parsed.netloc}" != self.allowed_origin or parsed.username or parsed.fragment:
            raise ValueError("resource is outside the approved origin")
        if type(authorized_cents) is not int or not 0 < authorized_cents <= self.per_call_cap_cents:
            raise ValueError("authorized amount exceeds per-call policy")
        response = self._request("GET", url)
        if response.status_code != 402:
            raise ValueError("resource did not return a payment-required challenge")
        data = self._decode(response.headers.get("PAYMENT-REQUIRED", ""))
        if data.get("x402Version") != 2 or data.get("resource", {}).get("url") != url:
            raise ValueError("unsupported x402 version or mismatched resource")
        accepted = []
        for option in data.get("accepts", []):
            if not isinstance(option, dict):
                continue
            amount = str(option.get("amount", ""))
            if (option.get("scheme") == "exact" and option.get("network") == BASE_SEPOLIA
                and str(option.get("asset", "")).lower() == BASE_SEPOLIA_USDC
                and str(option.get("payTo", "")).lower() == self.pay_to.lower()
                and option.get("extra", {}).get("assetTransferMethod", "eip3009") == "eip3009"
                and amount.isdecimal() and 0 < int(amount) <= authorized_cents * 10000
                and 0 < int(option.get("maxTimeoutSeconds", 0)) <= 300):
                accepted.append(option)
        if not accepted:
            raise ValueError("no challenge satisfies recipient, testnet, USDC and spending policy")
        return {"x402Version": 2, "resource": data["resource"], "accepts": [min(accepted, key=lambda item: int(item["amount"]))]}

    @staticmethod
    def sdk_signer(private_key: str) -> Callable[[dict[str, Any]], str]:
        """Create a local signer; importing/configuring this does not send funds."""
        from eth_account import Account
        from x402 import PaymentRequired, x402ClientSync
        from x402.mechanisms.evm import EthAccountSigner
        from x402.mechanisms.evm.exact import ExactEvmScheme
        from x402.http.utils import encode_payment_signature_header
        client = x402ClientSync()
        client.register(BASE_SEPOLIA, ExactEvmScheme(EthAccountSigner(Account.from_key(private_key))))
        return lambda challenge: encode_payment_signature_header(client.create_payment_payload(PaymentRequired.model_validate(challenge)))

    def purchase(self, url: str, *, authorized_cents: int, idempotency_key: str) -> dict[str, Any]:
        if not self.signer or not idempotency_key:
            raise ValueError("explicit signer and authorization idempotency key are required")
        fingerprint = hashlib.sha256(f"{url}:{self.pay_to}:{authorized_cents}".encode()).hexdigest()
        with sqlite3.connect(self.journal_path) as conn:
            row = conn.execute("SELECT fingerprint,status,result FROM x402_submissions WHERE key=?", (idempotency_key,)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise ValueError("payment key reused with changed authorization")
            if row[1] == "confirmed":
                return json.loads(row[2])
            raise X402UncertainError("Prior payment outcome uncertain; no automatic payment retry")
        challenge = self.inspect(url, authorized_cents=authorized_cents)
        amount = int(challenge["accepts"][0]["amount"])
        day = datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(self.journal_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            spent = conn.execute("SELECT COALESCE(SUM(amount_atomic),0) FROM x402_submissions WHERE day=?", (day,)).fetchone()[0]
            if spent + amount > self.daily_cap_cents * 10000:
                raise ValueError("x402 daily authorization budget exhausted")
            conn.execute("INSERT INTO x402_submissions VALUES (?,?,?,?,?,NULL)", (idempotency_key, fingerprint, day, amount, "uncertain"))
        signature = self.signer(challenge)
        response = self._request("GET", url, headers={"PAYMENT-SIGNATURE": signature, "Idempotency-Key": idempotency_key})
        if not response.is_success:
            raise X402UncertainError("Signed resource request not confirmed; reconcile before retry")
        settlement = self._decode(response.headers.get("PAYMENT-RESPONSE", ""))
        transaction = settlement.get("transaction", "")
        if settlement.get("success") is not True or settlement.get("network") != BASE_SEPOLIA or not re.fullmatch(r"0x[a-fA-F0-9]{64}", transaction):
            raise X402UncertainError("Provider settlement response is missing or invalid")
        chain = self._request("POST", "https://sepolia.base.org", json={"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt", "params": [transaction]})
        receipt = chain.json().get("result") if chain.is_success else None
        # Ethereum Transfer event signature is checked alongside recipient and amount.
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        matched = False
        if receipt and receipt.get("status") == "0x1":
            for log in receipt.get("logs", []):
                topics = log.get("topics", [])
                if (str(log.get("address", "")).lower() == BASE_SEPOLIA_USDC and len(topics) == 3
                    and topics[0].lower() == transfer_topic and topics[2][-40:].lower() == self.pay_to[2:].lower()
                    and int(log.get("data", "0x0"), 16) == amount):
                    matched = True
        if not matched:
            raise X402UncertainError("Testnet transfer not yet verified on chain; keep payment reserved")
        result = {"mode": "testnet", "network": BASE_SEPOLIA, "transaction": transaction,
                  "amount_atomic": amount, "asset": BASE_SEPOLIA_USDC, "pay_to": self.pay_to,
                  "resource": url, "status": "confirmed", "service": response.json()}
        with sqlite3.connect(self.journal_path) as conn:
            conn.execute("UPDATE x402_submissions SET status='confirmed',result=? WHERE key=?", (json.dumps(result), idempotency_key))
        return result

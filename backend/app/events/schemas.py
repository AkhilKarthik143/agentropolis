from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProposalType(StrEnum):
    OFFER = "OFFER"
    COUNTER_OFFER = "COUNTER_OFFER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    TRANSFER = "TRANSFER"
    FINANCING_REQUEST = "FINANCING_REQUEST"


class Proposal(BaseModel):
    """The only input shape the deterministic economy engine accepts."""

    model_config = ConfigDict(extra="forbid")

    proposal_type: ProposalType = Field(alias="type")
    proposal_id: str = Field(default_factory=lambda: f"prop_{uuid4().hex[:12]}")
    idempotency_key: str = Field(default_factory=lambda: f"idem_{uuid4().hex}")
    agent_id: str
    business_id: str
    counterparty_id: str | None = None
    deal_id: str | None = None
    session_id: str | None = None
    rationale: str = ""
    public_rationale: str = ""
    private_rationale: str = ""
    quantity: int | None = None
    unit: str | None = None
    unit_price_cents: int | None = None
    delivery_days: int | None = None
    payment_terms: str | None = None
    total_cents: int | None = None
    item: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("unit_price_cents", "total_cents")
    @classmethod
    def non_negative_money(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("money values must be non-negative integer cents")
        return value

    @field_validator("delivery_days")
    @classmethod
    def non_negative_delivery(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("delivery_days must be non-negative")
        return value


class ValidationResult(BaseModel):
    ok: bool
    stage: str
    reason_code: str | None = None
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int = 0
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str
    session_id: str | None = None
    business_id: str | None = None
    deal_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str | None = None
    hash: str | None = None


class DecisionRecord(BaseModel):
    proposal: dict[str, Any]
    validation: ValidationResult
    executed_outcome: dict[str, Any] = Field(default_factory=dict)
    public_rationale: str = ""
    private_rationale: str = ""


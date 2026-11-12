"""Two production-shaped requests through the running LiteLLM proxy (bench_config.yaml):

  1. coding agent   tool definitions, grep, two reads of the same file, a failing pytest run with a traceback, a model
                    file, git log, a patch and a passing re-run; the user then asks for the root cause and the result
  2. support chat   a policy system prompt with today's date, a customer who states contact constraints up front, a
                    knowledge-base search (RAG) result, order JSON, a decision, several follow-up turns; the user then
                    asks what was agreed

Each request goes through the four configurations on the echo provider (what reaches the model, tokens, latency), then
baseline and combined go to the real model (bench-llama, local llama3.2:3b).

    .venv-compression/Scripts/python reports/context-engineering/scripts/production_examples.py
writes raw/production_examples.json.
"""

import argparse
import json
import time

from bench_lib import CONFIGS, RAW, context_text, norm
from proxy_bench import post

from context_engineering.tokens import messages_tokens, tools_tokens

STUB = "[gateway: observation "
DUP = "[gateway: duplicate of observation "
SUMMARY = "[gateway: earlier conversation compacted"

REFUNDS_PY = '''"""Refund service: full and partial refunds against captured payments."""
from decimal import Decimal

from payments.models import Payment, Refund, RefundStatus
from payments.gateway import provider_client
from payments.errors import RefundError, InsufficientFunds

MAX_PARTIAL_REFUNDS = 5


def refundable_amount(payment: Payment) -> Decimal:
    refunded = sum((r.amount for r in payment.refunds if r.status != RefundStatus.FAILED), Decimal("0"))
    return payment.captured_amount - refunded


def create_refund(payment: Payment, amount: Decimal | None = None, reason: str = "requested_by_customer") -> Refund:
    """Refund `amount` (or everything that is left) of a captured payment."""
    if payment.status != "captured":
        raise RefundError(f"payment {payment.id} is {payment.status}, not captured")
    left = refundable_amount(payment)
    if amount is None:
        amount = left
    if amount <= 0 or amount > left:
        raise InsufficientFunds(f"refund {amount} exceeds refundable {left}")
    if amount < left:
        return _partial_refund(payment, amount, reason)
    return _full_refund(payment, reason)


def _full_refund(payment: Payment, reason: str) -> Refund:
    response = provider_client.refund(payment.provider_ref, amount=None, reason=reason,
                                      currency=payment.currency)
    return Refund.record(payment, payment.captured_amount, response["id"], RefundStatus.SUCCEEDED)


def _partial_refund(payment: Payment, amount: Decimal, reason: str) -> Refund:
    if len(payment.refunds) >= MAX_PARTIAL_REFUNDS:
        raise RefundError(f"payment {payment.id} already has {MAX_PARTIAL_REFUNDS} partial refunds")
    metadata = payment.metadata or {}
    response = provider_client.refund(payment.provider_ref, amount=str(amount), reason=reason,
                                      currency=metadata["currency"])
    return Refund.record(payment, amount, response["id"], RefundStatus.PENDING)
'''

MODELS_PY = '''"""Payment and refund models (SQLAlchemy)."""
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, JSON
from sqlalchemy.orm import relationship

from payments.db import Base


class RefundStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(32), primary_key=True)
    provider_ref = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False)
    currency = Column(String(3), nullable=False)          # ISO 4217, always set at capture
    captured_amount = Column(Numeric(12, 2), nullable=False)
    metadata = Column(JSON, nullable=True)                  # free-form client metadata; may be empty
    created_at = Column(DateTime, nullable=False)
    refunds = relationship("Refund", back_populates="payment", order_by="Refund.created_at")


class Refund(Base):
    __tablename__ = "refunds"
    id = Column(String(32), primary_key=True)
    payment_id = Column(String(32), ForeignKey("payments.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    provider_ref = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime, nullable=False)
    payment = relationship("Payment", back_populates="refunds")

    @classmethod
    def record(cls, payment, amount, provider_ref, status):
        refund = cls(payment=payment, amount=amount, provider_ref=provider_ref, status=status.value)
        payment.refunds.append(refund)
        return refund
'''

PYTEST_FAIL = "\n".join(
    ["============================= test session starts ==============================",
     "platform linux -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0",
     "rootdir: /srv/payments", "collected 14 items", ""]
    + [f"tests/test_refunds.py::test_{name} PASSED" for name in (
        "full_refund_captured", "full_refund_twice_rejected", "refund_not_captured_rejected",
        "refund_exceeds_amount_rejected", "zero_refund_rejected", "refundable_amount_ignores_failed",
        "full_refund_uses_payment_currency", "refund_reason_forwarded", "refund_records_provider_ref",
        "max_partial_refunds_enforced", "partial_refund_with_metadata_currency", "partial_then_full_refund")]
    + ["tests/test_refunds.py::test_partial_refund_without_metadata FAILED",
       "tests/test_refunds.py::test_partial_refund_empty_metadata FAILED", "",
       "=================================== FAILURES ===================================",
       "___________________ test_partial_refund_without_metadata ___________________", "",
       "    def test_partial_refund_without_metadata(captured_payment):",
       "        captured_payment.metadata = None",
       ">       refund = create_refund(captured_payment, Decimal(\"10.00\"))", "",
       "tests/test_refunds.py:118: ", "_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _",
       "payments/refunds.py:25: in create_refund", "    return _partial_refund(payment, amount, reason)",
       "payments/refunds.py:41: in _partial_refund",
       "    currency=metadata[\"currency\"])",
       "E   KeyError: 'currency'", "",
       "___________________ test_partial_refund_empty_metadata ___________________",
       "payments/refunds.py:41: in _partial_refund", "    currency=metadata[\"currency\"])",
       "E   KeyError: 'currency'",
       "=========================== short test summary info ============================",
       "FAILED tests/test_refunds.py::test_partial_refund_without_metadata - KeyError: 'currency'",
       "FAILED tests/test_refunds.py::test_partial_refund_empty_metadata - KeyError: 'currency'",
       "========================= 2 failed, 12 passed in 1.84s ========================="])

PYTEST_PASS = "\n".join(
    ["============================= test session starts ==============================",
     "platform linux -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0", "collected 14 items", "",
     "tests/test_refunds.py ..............                                     [100%]", "",
     "============================== 14 passed in 1.71s =============================="])

GIT_LOG = "\n".join([
    "a41c9e2 (HEAD -> main) Read refund currency from client metadata for partial refunds (PAY-2291)",
    "77d02bf Limit partial refunds per payment to 5",
    "1f3a8c0 Record provider refund id on Refund",
    "c09be41 Ignore failed refunds in refundable_amount",
    "5d2e7aa Initial refund service"])

GREP = "\n".join([
    "payments/refunds.py:17:def create_refund(payment: Payment, amount: Decimal | None = None, reason: str = \"requested_by_customer\") -> Refund:",
    "payments/refunds.py:31:def _full_refund(payment: Payment, reason: str) -> Refund:",
    "payments/refunds.py:37:def _partial_refund(payment: Payment, amount: Decimal, reason: str) -> Refund:",
    "payments/api/views.py:88:        refund = create_refund(payment, amount=body.amount, reason=body.reason)",
    "tests/test_refunds.py:12:from payments.refunds import create_refund, refundable_amount"])

TEST_NAMES = ["full_refund_captured", "full_refund_twice_rejected", "refund_not_captured_rejected",
              "refund_exceeds_amount_rejected", "zero_refund_rejected", "refundable_amount_ignores_failed",
              "full_refund_uses_payment_currency", "refund_reason_forwarded", "refund_records_provider_ref",
              "max_partial_refunds_enforced", "partial_refund_with_metadata_currency", "partial_then_full_refund",
              "partial_refund_without_metadata", "partial_refund_empty_metadata"]
TEST_REFUNDS_PY = "\n".join(
    ['"""Tests for payments.refunds."""', "from decimal import Decimal", "", "import pytest", "",
     "from payments.refunds import create_refund, refundable_amount",
     "from payments.errors import RefundError, InsufficientFunds", ""]
    + [line for i, name in enumerate(TEST_NAMES)
       for line in (f"def test_{name}(captured_payment, provider_stub):",
                    f"    captured_payment.metadata = {{'currency': 'EUR'}} if {i} % 3 else None",
                    f"    refund = create_refund(captured_payment, Decimal('{10 + i}.00'))",
                    f"    assert refund.amount == Decimal('{10 + i}.00')",
                    "    assert provider_stub.calls[-1]['currency'] == captured_payment.currency", "")])

VIEWS_PY = "\n".join(
    ['"""HTTP API for refunds (FastAPI)."""', "from decimal import Decimal", "",
     "from fastapi import APIRouter, HTTPException", "from pydantic import BaseModel, condecimal", "",
     "from payments.db import session_scope", "from payments.models import Payment",
     "from payments.refunds import create_refund", "from payments.errors import RefundError, InsufficientFunds", "",
     "router = APIRouter(prefix='/v1/payments')", "", "",
     "class RefundBody(BaseModel):", "    amount: condecimal(gt=0, max_digits=12, decimal_places=2) | None = None",
     "    reason: str = 'requested_by_customer'", "", "",
     "@router.post('/{payment_id}/refunds', status_code=201)",
     "def post_refund(payment_id: str, body: RefundBody):", "    with session_scope() as session:",
     "        payment = session.get(Payment, payment_id)", "        if payment is None:",
     "            raise HTTPException(404, 'payment not found')", "        try:",
     "            refund = create_refund(payment, amount=body.amount, reason=body.reason)",
     "        except InsufficientFunds as exc:", "            raise HTTPException(409, str(exc))",
     "        except RefundError as exc:", "            raise HTTPException(422, str(exc))",
     "        # Any other exception (for example a KeyError) propagates and becomes HTTP 500.",
     "        return {'id': refund.id, 'status': refund.status, 'amount': str(refund.amount)}"]
    + [f"# route {i}: GET /v1/payments/{{payment_id}}/refunds/{{refund_id}} detail handler {i}" for i in range(6)])

GIT_SHOW = "\n".join(
    ["commit a41c9e2b7d1f0c3e9a8b6d5c4f3e2d1c0b9a8f7e", "Author: Dev Bot <devbot@example.com>",
     "Date:   Wed Nov 12 06:58:10 2026 +0000", "",
     "    Read refund currency from client metadata for partial refunds (PAY-2291)", "",
     "diff --git a/payments/refunds.py b/payments/refunds.py", "@@ -38,4 +38,5 @@ def _partial_refund(...)",
     "+    metadata = payment.metadata or {}",
     "     response = provider_client.refund(payment.provider_ref, amount=str(amount), reason=reason,",
     "-                                      currency=payment.currency)",
     "+                                      currency=metadata[\"currency\"])"]
    + [f" unchanged context line {i} of payments/refunds.py" for i in range(12)])

ERROR_LOGS = "\n".join(
    f"2026-11-12T{8 + i // 30:02d}:{(i * 2) % 60:02d}:11Z ERROR payments.api POST /v1/payments/pay_{7000 + i}/refunds "
    f"500 KeyError('currency') request_id=req-{0xa0000 + i * 97:06x} amount={5 + i % 40}.00" for i in range(24))

TOOLS = [
    {"type": "function", "function": {"name": "grep", "description": "Search the repository with a regex.",
                                      "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}},
                                                     "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file from the repository.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                                     "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run pytest on a path.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                                     "required": ["path"]}}},
    {"type": "function", "function": {"name": "git_log", "description": "Show recent commits.",
                                      "parameters": {"type": "object", "properties": {"n": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "search_logs", "description": "Search production error logs.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"},
                                                     "since": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "git_show", "description": "Show a commit with its diff.",
                                      "parameters": {"type": "object", "properties": {"commit": {"type": "string"}},
                                                     "required": ["commit"]}}},
    {"type": "function", "function": {"name": "apply_patch", "description": "Apply a unified diff.",
                                      "parameters": {"type": "object", "properties": {"diff": {"type": "string"}},
                                                     "required": ["diff"]}}},
]


def call(call_id, name, arguments, output, reply):
    return [{"role": "assistant", "content": None, "tool_calls": [
                {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]},
            {"role": "tool", "tool_call_id": call_id, "content": output},
            {"role": "assistant", "content": reply}]


GATEWAY_PY = "\n".join(
    ['"""Thin client for the card processor\'s refund API."""', "import httpx", "", "from payments.settings import PROVIDER_URL, PROVIDER_KEY", "",
     "", "class ProviderClient:", "    def __init__(self, base_url: str, key: str):",
     "        self._http = httpx.Client(base_url=base_url, headers={'Authorization': f'Bearer {key}'}, timeout=10)", "",
     "    def refund(self, provider_ref: str, amount: str | None, reason: str, currency: str) -> dict:",
     "        if not currency or len(currency) != 3:", "            raise ValueError(f'invalid currency {currency!r}')",
     "        body = {'payment': provider_ref, 'reason': reason, 'currency': currency}",
     "        if amount is not None:", "            body['amount'] = amount",
     "        response = self._http.post('/v2/refunds', json=body)", "        response.raise_for_status()",
     "        return response.json()", "", "", "provider_client = ProviderClient(PROVIDER_URL, PROVIDER_KEY)"]
    + [f"# retry policy note {i}: refunds are idempotent on (payment, amount, reason) for 24 h" for i in range(22)])

ERRORS_PY = "\n".join(
    ['"""Domain errors for payments."""', "", "", "class PaymentsError(Exception):", "    status = 400", "",
     "", "class RefundError(PaymentsError):", "    status = 422", "", "",
     "class InsufficientFunds(RefundError):", "    status = 409", ""]
    + [f"class ProviderError{i}(PaymentsError):\n    status = 502\n    code = 'provider_{i:03d}'\n" for i in range(18)])

FULL_SUITE = "\n".join(
    ["============================= test session starts ==============================", "collected 212 items", ""]
    + [f"tests/test_{mod}.py {'.' * (8 + i % 9)}" + " " * 20 + f"[{min(100, 6 * (i + 1))}%]"
       for i, mod in enumerate(["api", "auth", "captures", "currency", "db", "gateway", "ledger", "metadata",
                                "models", "payouts", "refunds", "reports", "settlements", "webhooks"])]
    + ["", "FAILED tests/test_refunds.py::test_partial_refund_without_metadata - KeyError: 'currency'",
       "FAILED tests/test_refunds.py::test_partial_refund_empty_metadata - KeyError: 'currency'",
       "======================= 2 failed, 210 passed in 18.42s ========================"]
    + [f"slowest test {i}: tests/test_settlements.py::test_batch_{i} 0.{40 + i}s" for i in range(25)])

CHANGELOG = "\n".join(
    ["# Changelog", "", "## 2026-11-12", "- PAY-2291: read refund currency from client metadata for partial refunds", ""]
    + [f"## 2026-10-{28 - i:02d}\n- PAY-{2200 + i}: maintenance release {i} (dependency updates, logging tweaks)\n"
       for i in range(22)])


def coding_agent(longer: bool = False):
    patch = ("--- a/payments/refunds.py\n+++ b/payments/refunds.py\n@@ -38,5 +38,4 @@\n"
             "-    metadata = payment.metadata or {}\n     response = provider_client.refund(payment.provider_ref, "
             "amount=str(amount), reason=reason,\n-                                      currency=metadata[\"currency\"])\n"
             "+                                      currency=payment.currency)\n")
    messages = [
        {"role": "system", "content": (
            "You are a senior Python engineer working inside the payments repository. Use the tools to inspect the "
            "code and run the tests before changing anything. Keep changes minimal, never change public function "
            "signatures, and explain the root cause with file and line references when you are done.")},
        {"role": "user", "content": "Partial refunds return HTTP 500 in production since this morning (ticket "
                                    "PAY-2304). Find the cause and fix it. Do not change the public API."},
    ]
    messages += call("call_0", "search_logs", {"query": "status:500 path:/v1/payments/*/refunds", "since": "6h"},
                     ERROR_LOGS, "24 HTTP 500s on POST /refunds since 08:00, all KeyError('currency'). Finding the code.")
    messages += call("call_1", "grep", {"pattern": "def .*refund"}, GREP,
                     "The entry point is create_refund in payments/refunds.py; reading it.")
    messages += call("call_1b", "read_file", {"path": "payments/api/views.py"}, VIEWS_PY,
                     "The view maps InsufficientFunds to 409 and RefundError to 422; a KeyError becomes a 500.")
    messages += call("call_2", "read_file", {"path": "payments/refunds.py"}, REFUNDS_PY,
                     "Partial refunds go through _partial_refund, which reads the currency from payment.metadata. "
                     "Running the refund tests.")
    messages += call("call_3", "run_tests", {"path": "tests/test_refunds.py"}, PYTEST_FAIL,
                     "Two partial-refund tests fail with KeyError: 'currency' at payments/refunds.py:41 when the "
                     "payment has no metadata. Checking the model.")
    messages += call("call_3b", "read_file", {"path": "tests/test_refunds.py"}, TEST_REFUNDS_PY,
                     "The failing tests set metadata to None, which the model allows.")
    messages += call("call_4", "read_file", {"path": "payments/models.py"}, MODELS_PY,
                     "Payment.currency is always set at capture, while metadata is optional and may be empty.")
    messages += call("call_5", "git_log", {"n": 5}, GIT_LOG,
                     "Commit a41c9e2 (PAY-2291) switched partial refunds to metadata['currency'] this morning.")
    messages += call("call_5b", "git_show", {"commit": "a41c9e2"}, GIT_SHOW,
                     "a41c9e2 replaced currency=payment.currency with metadata[\"currency\"].")
    if longer:   # the agent keeps investigating before it patches, as real sessions do
        messages += call("call_5c", "read_file", {"path": "payments/gateway.py"}, GATEWAY_PY,
                         "The provider client validates the currency, so passing payment.currency is safe.")
        messages += call("call_5d", "read_file", {"path": "payments/errors.py"}, ERRORS_PY,
                         "No domain error covers a missing currency; the KeyError escapes as a 500.")
        messages += call("call_5e", "run_tests", {"path": "tests"}, FULL_SUITE,
                         "Only the two partial-refund tests fail in the whole suite.")
        messages += call("call_5f", "read_file", {"path": "CHANGELOG.md"}, CHANGELOG,
                         "PAY-2291 shipped this morning; nothing else touched refunds.")
    messages += call("call_6", "read_file", {"path": "payments/refunds.py"}, REFUNDS_PY,
                     "Confirmed the exact lines before patching.")
    messages += call("call_7", "apply_patch", {"diff": patch}, "Patch applied: payments/refunds.py (1 hunk).",
                     "Patched _partial_refund to use payment.currency. Re-running the tests.")
    messages += call("call_8", "run_tests", {"path": "tests/test_refunds.py"}, PYTEST_PASS,
                     "All refund tests pass now.")
    messages.append({"role": "user", "content": "Summarise for the incident ticket: what was the root cause (file "
                                                "and line), which commit introduced it, and how many tests pass now?"})
    return {"name": "coding_agent" + ("_longer" if longer else ""), "model_tools": TOOLS, "messages": messages,
            "facts": ["KeyError", "a41c9e2", "14"],
            "exact": ["KeyError: 'currency'", "payments/refunds.py:41", "a41c9e2", "currency=payment.currency",
                      "14 passed", "PAY-2304"]}


KB = "\n\n".join([
    "[KB-112] Damaged items: If an item arrives damaged, the customer may choose a free replacement or a full refund. "
    "Replacements ship with express delivery at no cost. A prepaid return label is emailed within 1 business day; "
    "the damaged item must be returned within 30 days. Photos of the damage are required for orders above 200 EUR.",
    "[KB-087] Contact preferences: Always honour the customer's stated contact channel. If a customer asks not to be "
    "called, do not call, including for delivery confirmations; use the channel they chose.",
    "[KB-140] Express delivery: Express shipments within the EU arrive in 1-2 business days after dispatch. "
    "Dispatch happens the same day for confirmations received before 14:00 CET.",
    "[KB-203] Refund timing: Refunds to cards appear within 5-10 business days; refunds to wallets within 2 days.",
    "[KB-019] Loyalty points: Points are not deducted for replaced items; they are deducted for refunded items.",
])

ORDER = json.dumps({
    "order_id": "ORD-48213", "placed_at": "2026-11-03T09:12:44Z", "status": "delivered", "currency": "EUR",
    "total": 349.90, "customer": {"id": "C-77120", "tier": "gold"},
    "items": [{"sku": "KTL-900-BLK", "name": "Electric kettle 1.7 l, black", "qty": 1, "price": 89.90},
              {"sku": "ESP-2200-STL", "name": "Espresso machine, steel", "qty": 1, "price": 260.00}],
    "shipping": {"carrier": "DHL", "tracking": "JD014600003829471", "address_city": "Valencia"},
}, indent=1)


KB_SHIPPING = "\n\n".join(f"[KB-{300 + i}] {text}" for i, text in enumerate([
    "Return labels: prepaid return labels are valid for 30 days and accepted at every DHL ServicePoint and "
    "Packstation in Spain. The label is a PDF attached to the email; a printed copy or the QR code both work.",
    "Replacement stock: when the replacement item is out of stock, offer the same model in another colour or a full "
    "refund; never substitute a different model without the customer's written agreement.",
    "Express delivery in Spain: express parcels to mainland Spain arrive within 1-2 business days; the Balearic and "
    "Canary Islands take 3-5 business days. A signature is required for items above 150 EUR.",
    "Gold tier: gold customers get priority handling and free returns on all orders, not only damaged ones.",
    "Damage claims with the carrier: agents open the carrier claim themselves; the customer does not need to contact "
    "DHL. Claims do not delay the replacement.",
    "Tracking: tracking numbers are sent in the dispatch email; agents may also share them in the conversation.",
    "Address changes: the delivery address can be changed until the parcel is dispatched; after dispatch, redirect "
    "through the carrier's own service.",
    "Business hours: the support team answers emails between 08:00 and 20:00 CET, Monday to Saturday.",
]))

SUPPORT_TOOLS = [
    {"type": "function", "function": {"name": "search_kb", "description": "Search the support knowledge base.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                                     "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_order", "description": "Fetch an order by id.",
                                      "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                                                     "required": ["order_id"]}}},
]


def support_chat(answer_length: int = 3):
    filler = (" Our team checks every case like this by hand, and we keep a note on your account so that anyone "
              "who picks up the conversation later sees the same history and does not ask you to repeat yourself.")
    messages = [
        {"role": "system", "content": (
            "You are a customer support agent for Hogar Direct. Follow the knowledge base. Be concise and friendly. "
            "Never promise anything the policy does not allow. Confirm decisions explicitly.\n"
            "Today's date: 2026-11-12 09:40 CET")},
        {"role": "user", "content": "Hi, this is Maria Lopez. My order ORD-48213 arrived yesterday and the espresso "
                                    "machine is cracked. Please only contact me by email, never by phone."},
        {"role": "assistant", "content": "I'm sorry about that, Maria. I'll only contact you by email. Let me check "
                                         "the policy for damaged items." + filler},
    ]
    messages += call("call_kb", "search_kb", {"query": "damaged item replacement refund contact preference"}, KB,
                     "You can choose a free replacement with express delivery, or a full refund. Since the order is "
                     "above 200 EUR, please send a photo of the damage." + filler)
    messages += [
        {"role": "user", "content": "Here is the photo link: https://share.example.com/p/8812. I'd prefer a "
                                    "replacement, not a refund."},
        {"role": "assistant", "content": "Thank you, the photo shows the crack clearly." + filler},
    ]
    messages += call("call_order", "get_order", {"order_id": "ORD-48213"}, ORDER,
                     "Decision: we agreed to send a replacement espresso machine (ESP-2200-STL) by express delivery, "
                     "free of charge, and to email you a prepaid return label for the damaged one." + filler)
    for question, answer in [
        ("When will the replacement arrive?", "If I confirm before 14:00 CET it ships today and arrives in 1-2 "
                                              "business days in Valencia."),
        ("Will I lose my loyalty points?", "No, points are not deducted for replaced items."),
        ("Can I return the broken one at a DHL point?", "Yes, the prepaid label works at any DHL ServicePoint "
                                                         "within 30 days."),
        ("The kettle is fine, I'll keep it. Do I need to do anything?", "No, only the espresso machine is part of "
                                                                         "this case."),
        ("Is there a way to track the replacement?", "You will receive a new DHL tracking number by email as soon "
                                                      "as it ships."),
        ("Does someone need to sign for it?", "Yes, express parcels above 150 EUR need a signature on delivery."),
        ("I'm away on Friday. Could it go to my office instead?", "Yes, send me the office address and I will "
                                                                   "update the shipment before dispatch."),
        ("Actually, let's keep my home address.", "Done, the replacement stays addressed to your home in Valencia."),
    ]:
        messages += [{"role": "user", "content": question},
                     {"role": "assistant", "content": answer + filler * answer_length}]
    messages += [{"role": "user", "content": "Do I need to contact DHL about the damage myself?"}]
    messages += call("call_kb2", "search_kb", {"query": "carrier damage claim return label express spain"},
                     KB_SHIPPING, "No, I open the carrier claim myself, and it does not delay your replacement."
                     + filler)
    messages.append({"role": "user", "content": "Before I go: what exactly did we agree for my damaged order, and "
                                                "how will you contact me about it?"})
    return {"name": "support_chat" + ("_longer" if answer_length > 3 else ""), "model_tools": SUPPORT_TOOLS,
            "messages": messages,
            "facts": ["replacement", "email"],
            "exact": ["ORD-48213", "ESP-2200-STL", "never by phone", "JD014600003829471"]}


def forwarded(base, key, example, config, model="bench-echo", max_tokens=200, with_tools=True):
    body = {"model": model, "messages": example["messages"], "max_tokens": max_tokens, "temperature": 0,
            "metadata": dict(CONFIGS[config])}
    if example["model_tools"] and with_tools:
        body["tools"] = example["model_tools"]
    payload, ms, error = post(base, key, body, timeout=1800)
    return payload, ms, error


def describe(example, received):
    text = context_text(received)
    return {
        "messages": len(received),
        "tokens": messages_tokens(received),
        "stubs": sum(1 for m in received if str(m.get("content")).startswith(STUB)),
        "duplicates_folded": sum(1 for m in received if str(m.get("content")).startswith(DUP)),
        "summaries": sum(1 for m in received if str(m.get("content")).startswith(SUMMARY)),
        "exact_strings_kept": f"{sum(1 for s in example['exact'] if s in text)}/{len(example['exact'])}",
        "missing_exact": [s for s in example["exact"] if s not in text],
        "latest_question_unchanged": received[-1] == example["messages"][-1],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4100")
    parser.add_argument("--key", default="sk-bench-local")
    parser.add_argument("--no-model", action="store_true")
    args = parser.parse_args()
    report = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "examples": []}
    for example in (coding_agent(), coding_agent(longer=True), support_chat(), support_chat(answer_length=8)):
        entry = {"name": example["name"], "original_tokens": messages_tokens(example["messages"]),
                 "original_messages": len(example["messages"]), "configs": {}, "model": {}}
        for config in CONFIGS:
            payload, ms, error = forwarded(args.base, args.key, example, config)
            if error:
                entry["configs"][config] = {"error": error}
                continue
            received = json.loads(payload["choices"][0]["message"]["content"])["received_messages"]
            entry["configs"][config] = {"latency_ms": round(ms, 1), **describe(example, received)}
            if config == "combined":
                entry["combined_forwarded"] = received
            print(example["name"], config, json.dumps(entry["configs"][config]), flush=True)
        # The local model runs with num_ctx 8192 (bench_config.yaml); llama's tokenizer counts more than cl100k, so
        # requests above about 6,500 cl100k tokens could be truncated in the baseline and are sent to the echo only.
        fits = entry["original_tokens"] + tools_tokens(example["model_tools"]) <= 6500
        entry["model_skipped"] = None if fits else "longer than the local model's 8,192-token context"
        if not args.no_model and fits:
            # The last turn asks for a written summary. With tool definitions present llama3.2 answers with another
            # tool call instead (seen in a first run), so the final-answer request is sent without `tools`.
            for config in ("baseline", "combined"):
                payload, ms, error = forwarded(args.base, args.key, example, config, model="bench-llama",
                                               with_tools=False)
                message = {} if error else payload["choices"][0]["message"]
                answer = message.get("content") or ""
                usage = None if error else payload.get("usage")
                entry["model"][config] = {
                    "latency_s": round(ms / 1000, 1), "error": error, "answer": answer, "usage": usage,
                    "tool_calls": message.get("tool_calls"),
                    "facts_found": [f for f in example["facts"] if norm(f) in norm(answer)]}
                print(example["name"], "model", config, json.dumps(entry["model"][config])[:400], flush=True)
        report["examples"].append(entry)
    (RAW / "production_examples.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

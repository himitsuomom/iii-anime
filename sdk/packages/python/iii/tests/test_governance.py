"""Tests for the iii.governance Agent Governance Toolkit bridge."""

from __future__ import annotations

import pytest

from iii.governance import (
    Decision,
    GovernanceDenied,
    InMemoryAuditLog,
    govern_function,
    register_governed,
)


class StubEvaluator:
    """Deterministic evaluator: denies whenever ``input.amount`` exceeds a cap."""

    def __init__(self, *, cap: float = 10_000):
        self.cap = cap
        self.calls: list[tuple[str, dict]] = []

    def evaluate(self, agent_id: str, context: dict) -> Decision:
        self.calls.append((agent_id, context))
        amount = context.get("input", {}).get("amount", 0)
        if amount > self.cap:
            return Decision(
                allowed=False,
                action="deny",
                matched_rule="block-large-transfers",
                reason=f"amount {amount} exceeds cap {self.cap}",
            )
        return Decision(allowed=True, action="allow", matched_rule="default-allow")


def transfer(data):
    return {"transferred": data["amount"]}


def test_allows_and_runs_handler():
    governed = govern_function(transfer, evaluator=StubEvaluator(), action="transfer")
    assert governed({"amount": 100}) == {"transferred": 100}


def test_denied_raises_governance_denied():
    governed = govern_function(transfer, evaluator=StubEvaluator(), action="transfer")
    with pytest.raises(GovernanceDenied) as excinfo:
        governed({"amount": 50_000})
    assert excinfo.value.decision.matched_rule == "block-large-transfers"


def test_handler_not_called_when_denied():
    called = {"value": False}

    def handler(data):
        called["value"] = True
        return "ran"

    governed = govern_function(handler, evaluator=StubEvaluator(), action="transfer")
    with pytest.raises(GovernanceDenied):
        governed({"amount": 50_000})
    assert called["value"] is False


def test_on_deny_short_circuits_with_value():
    governed = govern_function(
        transfer,
        evaluator=StubEvaluator(),
        action="transfer",
        on_deny=lambda decision: {"error": "blocked", "reason": decision.reason},
    )
    result = governed({"amount": 50_000})
    assert result["error"] == "blocked"
    assert "exceeds cap" in result["reason"]


def test_audit_records_each_evaluation():
    audit = InMemoryAuditLog()
    governed = govern_function(
        transfer, evaluator=StubEvaluator(), action="transfer", audit_log=audit
    )
    governed({"amount": 100})
    with pytest.raises(GovernanceDenied):
        governed({"amount": 50_000})

    assert len(audit.entries) == 2
    assert audit.entries[0]["outcome"] == "allow"
    assert audit.entries[1]["outcome"] == "deny"
    assert audit.entries[0]["action"] == "transfer"


def test_audit_disabled_yields_no_sink():
    governed = govern_function(
        transfer, evaluator=StubEvaluator(), action="transfer", audit=False
    )
    assert governed.audit_log is None
    assert governed({"amount": 1}) == {"transferred": 1}


def test_action_callable_is_evaluated_per_call():
    evaluator = StubEvaluator()
    governed = govern_function(
        transfer, evaluator=evaluator, action=lambda data: data["kind"]
    )
    governed({"amount": 1, "kind": "deposit"})
    assert evaluator.calls[-1][1]["action"]["type"] == "deposit"


def test_action_defaults_to_handler_name():
    evaluator = StubEvaluator()
    governed = govern_function(transfer, evaluator=evaluator)
    governed({"amount": 1})
    assert evaluator.calls[-1][1]["action"]["type"] == "transfer"


def test_non_mapping_payload_wrapped_as_value():
    evaluator = StubEvaluator()
    governed = govern_function(lambda data: data, evaluator=evaluator, action="echo")
    governed(42)
    assert evaluator.calls[-1][1]["input"] == {"value": 42}


def test_custom_context_builder():
    evaluator = StubEvaluator()
    governed = govern_function(
        transfer,
        evaluator=evaluator,
        action="transfer",
        context_builder=lambda data: {"input": data, "tenant": {"id": "acme"}},
    )
    governed({"amount": 1})
    assert evaluator.calls[-1][1]["tenant"] == {"id": "acme"}


@pytest.mark.asyncio
async def test_async_handler_is_governed_and_awaited():
    async def async_transfer(data):
        return {"ok": data["amount"]}

    governed = govern_function(async_transfer, evaluator=StubEvaluator(), action="transfer")
    assert await governed({"amount": 100}) == {"ok": 100}

    with pytest.raises(GovernanceDenied):
        await governed({"amount": 50_000})


def test_requires_policy_or_evaluator():
    with pytest.raises(ValueError):
        govern_function(transfer)


def test_wrapper_preserves_metadata():
    governed = govern_function(transfer, evaluator=StubEvaluator())
    assert governed.__wrapped__ is transfer
    assert governed.__name__ == "transfer"
    assert governed.__governed__ is True


class FakeClient:
    def __init__(self):
        self.registered: dict[str, object] = {}

    def register_function(self, function_id, handler, *, description=None, metadata=None):
        self.registered[function_id] = handler
        return {"id": function_id, "handler": handler}


def test_register_governed_registers_and_defaults_action_to_function_id():
    client = FakeClient()
    evaluator = StubEvaluator()
    ref = register_governed(client, "transfer", transfer, evaluator=evaluator)
    assert ref["id"] == "transfer"

    governed = client.registered["transfer"]
    governed({"amount": 1})
    assert evaluator.calls[-1][1]["action"]["type"] == "transfer"


# --- Integration with the real Agent Governance Toolkit (optional) ----------

try:
    import agentmesh  # noqa: F401

    _HAS_AGENTMESH = True
except ImportError:
    _HAS_AGENTMESH = False

requires_agentmesh = pytest.mark.skipif(
    not _HAS_AGENTMESH,
    reason="Agent Governance Toolkit (agentmesh) not installed",
)


POLICY_YAML = """
name: payments-policy
rules:
  - name: block-large-transfers
    description: Deny transfers above the limit
    condition: "action.type == 'transfer' and input.amount > 10000"
    action: deny
    priority: 100
  - name: allow-transfers
    condition: "action.type == 'transfer'"
    action: allow
    priority: 1
"""


@requires_agentmesh
def test_agt_engine_allows_small_transfer():
    governed = govern_function(transfer, policy=POLICY_YAML, action="transfer")
    assert governed({"amount": 100}) == {"transferred": 100}


@requires_agentmesh
def test_agt_engine_denies_large_transfer():
    governed = govern_function(transfer, policy=POLICY_YAML, action="transfer")
    with pytest.raises(GovernanceDenied):
        governed({"amount": 50_000})

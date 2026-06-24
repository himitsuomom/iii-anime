"""Governance integration for iii functions.

This module bridges iii's function model (``handler(data) -> result``) to the
`Agent Governance Toolkit (AGT) <https://github.com/microsoft/agent-governance-toolkit>`_
policy engine. Every governed invocation is evaluated against a declarative
policy *before* the handler runs, the decision is audited, and denied actions
raise :class:`GovernanceDenied` (or are routed to an ``on_deny`` callback).

The AGT policy engine (``agentmesh``) is an **optional** dependency (it requires
Python >= 3.11, so it is not locked into the SDK). Install it on demand, e.g.
from the copy vendored in this repo::

    uv pip install ./third_party/agent-governance-toolkit/agent-governance-python/agent-mesh
    # or, once published:  pip install agent-governance-toolkit

The bridge is also fully usable without AGT by injecting a custom ``evaluator``
that implements the :class:`PolicyEvaluator` protocol — useful for testing or
for plugging in a different policy backend.

Example::

    import iii
    from iii.governance import govern_function

    def transfer(data):
        ...  # move money

    policy = '''
    name: payments
    rules:
      - name: block-large-transfers
        condition: "action.type == 'transfer' and input.amount > 10000"
        action: deny
        priority: 100
      - name: allow-transfers
        condition: "action.type == 'transfer'"
        action: allow
    '''

    safe_transfer = govern_function(transfer, policy=policy, action="transfer")
    client.register_function("transfer", safe_transfer)
"""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Union, runtime_checkable

__all__ = [
    "Decision",
    "GovernanceDenied",
    "PolicyEvaluator",
    "AuditSink",
    "InMemoryAuditLog",
    "load_agt_evaluator",
    "govern_function",
    "register_governed",
]


@dataclass
class Decision:
    """Normalized result of a policy evaluation.

    Mirrors the relevant fields of AGT's ``PolicyDecision`` so that both the
    AGT engine and lightweight injected evaluators present the same surface.
    """

    allowed: bool
    action: str = "deny"
    matched_rule: Optional[str] = None
    reason: Optional[str] = None
    policy_name: Optional[str] = None


class GovernanceDenied(Exception):
    """Raised when a governed action is denied by policy.

    The originating decision is available on the ``decision`` attribute.
    """

    def __init__(self, decision: Any):
        self.decision = decision
        rule = getattr(decision, "matched_rule", None) or "<none>"
        reason = getattr(decision, "reason", None) or "denied by policy"
        super().__init__(f"Action denied by policy rule '{rule}': {reason}")


@runtime_checkable
class PolicyEvaluator(Protocol):
    """Minimal policy-engine interface the bridge depends on.

    AGT's ``PolicyEngine`` already satisfies this protocol via
    :func:`load_agt_evaluator`; any object exposing a compatible ``evaluate``
    can be injected instead (e.g. a stub in tests).
    """

    def evaluate(self, agent_id: str, context: dict[str, Any]) -> Any:
        """Return a decision with ``allowed``/``action``/``matched_rule``/``reason``."""
        ...


@runtime_checkable
class AuditSink(Protocol):
    """Audit interface compatible with AGT's ``AuditLog.log``."""

    def log(self, **kwargs: Any) -> Any: ...


@dataclass
class InMemoryAuditLog:
    """Lightweight, dependency-free audit sink.

    Records each evaluation as a dict in :attr:`entries`. Drop-in replacement
    for AGT's ``AuditLog`` for the fields the bridge writes. Use AGT's
    ``AuditLog`` (tamper-evident hash chain) in production by passing it as
    ``audit_log``.
    """

    entries: list[dict[str, Any]] = field(default_factory=list)

    def log(self, **kwargs: Any) -> dict[str, Any]:
        self.entries.append(kwargs)
        return kwargs


class _AgtEvaluator:
    """Adapts an AGT ``PolicyEngine`` to the :class:`PolicyEvaluator` protocol."""

    def __init__(self, engine: Any):
        self._engine = engine

    @property
    def engine(self) -> Any:
        return self._engine

    def evaluate(self, agent_id: str, context: dict[str, Any]) -> Any:
        return self._engine.evaluate(agent_id, context)


def load_agt_evaluator(
    policy: Union[str, Any],
    *,
    conflict_strategy: str = "deny_overrides",
) -> _AgtEvaluator:
    """Build a :class:`PolicyEvaluator` backed by AGT's policy engine.

    Args:
        policy: A policy file path, an inline YAML string, or an AGT ``Policy``
            object.
        conflict_strategy: AGT conflict-resolution strategy. Defaults to
            ``"deny_overrides"`` (any deny wins).

    Raises:
        ImportError: If the Agent Governance Toolkit (``agentmesh``) is not
            installed.
    """
    try:
        from agentmesh.governance.policy import (  # type: ignore[import-not-found]
            Policy,
            PolicyEngine,
        )
    except ImportError as exc:  # pragma: no cover - exercised via stub injection
        raise ImportError(
            "The Agent Governance Toolkit (agentmesh) is required to load a policy "
            "from YAML. Install it on demand, e.g. from the vendored copy:\n"
            "  uv pip install ./third_party/agent-governance-toolkit/"
            "agent-governance-python/agent-mesh\n"
            "or: pip install agent-governance-toolkit\n"
            "Alternatively, inject a custom `evaluator` (PolicyEvaluator) instead "
            "of `policy`."
        ) from exc

    engine = PolicyEngine(conflict_strategy=conflict_strategy)
    if isinstance(policy, str):
        loaded = engine.load_yaml_file(policy) if os.path.isfile(policy) else engine.load_yaml(policy)
    elif isinstance(policy, Policy):
        loaded = policy
        engine.load_policy(loaded)
    else:
        raise TypeError(
            f"policy must be a file path, YAML string, or AGT Policy object, got {type(policy).__name__}"
        )

    # Match govern()'s out-of-the-box behavior: a policy that names no agents
    # applies to every agent.
    if not getattr(loaded, "agent", None) and not getattr(loaded, "agents", None):
        loaded.agents = ["*"]

    return _AgtEvaluator(engine)


def _default_context_builder(data: Any) -> dict[str, Any]:
    """Build the policy context payload from an iii handler's ``data`` argument.

    A mapping payload is exposed under ``input.*`` directly; any other value is
    wrapped as ``input.value`` so policy conditions can reference it uniformly.
    """
    if isinstance(data, dict):
        return {"input": data}
    return {"input": {"value": data}}


@dataclass
class _Denied:
    """Sentinel carrying the value returned by an ``on_deny`` handler."""

    value: Any


_ALLOW = object()


def govern_function(
    handler: Callable[[Any], Any],
    *,
    policy: Union[str, Any, None] = None,
    evaluator: Optional[PolicyEvaluator] = None,
    action: Union[str, Callable[[Any], str], None] = None,
    agent_id: str = "*",
    audit: bool = True,
    audit_log: Optional[AuditSink] = None,
    on_deny: Optional[Callable[[Any], Any]] = None,
    context_builder: Optional[Callable[[Any], dict[str, Any]]] = None,
    conflict_strategy: str = "deny_overrides",
) -> Callable[[Any], Any]:
    """Wrap an iii function handler with policy enforcement and audit logging.

    The returned callable has the same shape as ``handler`` — it takes a single
    ``data`` argument and is suitable for ``client.register_function``. Sync and
    async handlers are both supported; async handlers stay async. On each call
    the policy is evaluated first: if denied, the handler never runs.

    Args:
        handler: The iii function handler to govern (``handler(data) -> result``).
        policy: Policy file path, inline YAML, or AGT ``Policy`` object. Required
            unless ``evaluator`` is supplied; ignored when ``evaluator`` is set.
        evaluator: A pre-built :class:`PolicyEvaluator`. Use this to inject a
            custom or stubbed policy backend. Takes precedence over ``policy``.
        action: The action identifier evaluated against the policy. Either a
            fixed string, or a callable ``data -> str`` to derive it per call.
            Defaults to the handler's ``__name__``.
        agent_id: Agent identifier passed to the evaluator. Defaults to ``"*"``.
        audit: Whether to record an audit entry per evaluation. Defaults True.
        audit_log: Audit sink to write to. Defaults to a fresh
            :class:`InMemoryAuditLog` when ``audit`` is True.
        on_deny: Optional callback invoked with the decision when an action is
            denied; its return value becomes the handler's result. Default:
            raise :class:`GovernanceDenied`.
        context_builder: Maps ``data`` to extra policy context. Defaults to
            exposing the payload under ``input.*``.
        conflict_strategy: Forwarded to :func:`load_agt_evaluator` when building
            an evaluator from ``policy``.

    Returns:
        A governed handler with ``evaluator`` and ``audit_log`` attributes for
        inspection, plus ``__wrapped__`` pointing at the original handler.
    """
    if evaluator is None:
        if policy is None:
            raise ValueError("govern_function requires either `policy` or `evaluator`")
        evaluator = load_agt_evaluator(policy, conflict_strategy=conflict_strategy)

    sink: Optional[AuditSink] = None
    if audit:
        sink = audit_log if audit_log is not None else InMemoryAuditLog()

    build_context = context_builder or _default_context_builder
    default_action = getattr(handler, "__name__", "invoke")

    def _resolve_action(data: Any) -> str:
        if callable(action):
            return action(data)
        if action is not None:
            return action
        return default_action

    def _enforce(data: Any) -> Union[object, _Denied]:
        action_type = _resolve_action(data)
        context: dict[str, Any] = {"action": {"type": action_type}}
        extra = build_context(data)
        if extra:
            context.update(extra)

        decision = evaluator.evaluate(agent_id, context)

        if sink is not None:
            outcome = getattr(decision, "action", None) or ("allow" if getattr(decision, "allowed", False) else "deny")
            sink.log(
                event_type="policy_evaluation",
                agent_did=agent_id,
                action=action_type,
                outcome=outcome,
                policy_decision=outcome,
                data={
                    "rule": getattr(decision, "matched_rule", None) or "",
                    "reason": getattr(decision, "reason", None) or "",
                },
            )

        if getattr(decision, "allowed", False):
            return _ALLOW

        if on_deny is not None:
            return _Denied(on_deny(decision))
        raise GovernanceDenied(decision)

    if inspect.iscoroutinefunction(handler):

        async def async_wrapper(data: Any) -> Any:
            outcome = _enforce(data)
            if isinstance(outcome, _Denied):
                return outcome.value
            return await handler(data)

        wrapper: Callable[[Any], Any] = async_wrapper
    else:

        def sync_wrapper(data: Any) -> Any:
            outcome = _enforce(data)
            if isinstance(outcome, _Denied):
                return outcome.value
            return handler(data)

        wrapper = sync_wrapper

    # Preserve identity/metadata so iii's schema auto-extraction and tooling
    # can still see through to the original handler.
    wrapper.__wrapped__ = handler  # type: ignore[attr-defined]
    wrapper.__name__ = getattr(handler, "__name__", "governed")
    wrapper.__doc__ = handler.__doc__
    wrapper.__governed__ = True  # type: ignore[attr-defined]
    wrapper.evaluator = evaluator  # type: ignore[attr-defined]
    wrapper.audit_log = sink  # type: ignore[attr-defined]
    return wrapper


def register_governed(
    client: Any,
    function_id: str,
    handler: Callable[[Any], Any],
    *,
    policy: Union[str, Any, None] = None,
    evaluator: Optional[PolicyEvaluator] = None,
    action: Union[str, Callable[[Any], str], None] = None,
    agent_id: str = "*",
    audit: bool = True,
    audit_log: Optional[AuditSink] = None,
    on_deny: Optional[Callable[[Any], Any]] = None,
    context_builder: Optional[Callable[[Any], dict[str, Any]]] = None,
    conflict_strategy: str = "deny_overrides",
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Any:
    """Govern ``handler`` and register it with the iii engine in one step.

    Convenience wrapper over :func:`govern_function` followed by
    ``client.register_function``. The action defaults to ``function_id`` (rather
    than the handler name), since that is the identity the engine exposes.

    Returns the ``FunctionRef`` from ``register_function``.
    """
    governed = govern_function(
        handler,
        policy=policy,
        evaluator=evaluator,
        action=action if action is not None else function_id,
        agent_id=agent_id,
        audit=audit,
        audit_log=audit_log,
        on_deny=on_deny,
        context_builder=context_builder,
        conflict_strategy=conflict_strategy,
    )
    return client.register_function(
        function_id,
        governed,
        description=description,
        metadata=metadata,
    )

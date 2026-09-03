from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from phase4_models import (
    EvidenceDecision,
    RiskDecision,
    Phase4Decision,
)


class Phase4Ledger:
    def __init__(self, base_path: str | Path = "logs") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]

        if hasattr(value, "value"):
            return value.value

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return value

    def record_evidence(
        self,
        decision_id: str,
        symbol: str,
        evidence_result,
    ) -> None:
        path = self.base_path / "evidence.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "decision_id": decision_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "evidence_score": evidence_result.score,
            "completeness": evidence_result.completeness,
            "contradictions": list(evidence_result.contradictions),
            "missing": list(evidence_result.missing),
            "reasons": list(evidence_result.reasons),
            "status": evidence_result.status.value,
        }

        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def record_risk(
        self,
        decision_id: str,
        symbol: str,
        risk_result,
    ) -> None:
        path = self.base_path / "risk_events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "decision_id": decision_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "status": risk_result.status.value,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "reason": check.reason,
                    "actual": check.actual,
                    "limit": check.limit,
                }
                for check in risk_result.checks
            ],
            "blocking_reasons": list(risk_result.blocking_reasons),
        }

        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def record_decision(self, decision) -> None:
        path = self.base_path / "decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "decision_id": decision.decision_id,
            "symbol": decision.symbol,
            "direction": decision.direction,
            "conviction": decision.conviction,
            "evidence_status": decision.evidence.status.value,
            "evidence_score": decision.evidence.score,
            "risk_status": decision.risk.status.value if decision.risk else "NOT_RUN",
            "final_status": decision.final_status.value,
            "reasons": list(decision.reasons),
            "execution_intent_created": decision.execution_intent is not None,
            "order_submitted": False,
            "created_at": decision.created_at.isoformat(),
        }

        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
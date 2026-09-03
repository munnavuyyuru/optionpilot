from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from phase4_models import EvidenceKind


@dataclass(frozen=True)
class RiskPolicy:
    max_position_risk_usd: float = 500.0
    max_daily_loss_usd: float = 500.0
    max_total_options_exposure_usd: float = 5000.0
    max_single_symbol_exposure_usd: float = 1500.0
    max_open_positions: int = 5
    min_dte: int = 21
    max_dte: int = 60
    max_bid_ask_pct: float = 0.10
    min_open_interest: int = 100
    min_volume: int = 10

    required_evidence_categories: frozenset = frozenset()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RiskPolicy":
        path = Path(path)
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        risk_data = data.get("risk", {})
        evidence_data = data.get("evidence", {})

        required_cats = frozenset(evidence_data.get("required_categories", []))

        return cls(
            max_position_risk_usd=float(risk_data.get("max_position_risk_usd", 500.0)),
            max_daily_loss_usd=float(risk_data.get("max_daily_loss_usd", 500.0)),
            max_total_options_exposure_usd=float(risk_data.get("max_total_options_exposure_usd", 5000.0)),
            max_single_symbol_exposure_usd=float(risk_data.get("max_single_symbol_exposure_usd", 1500.0)),
            max_open_positions=int(risk_data.get("max_open_positions", 5)),
            min_dte=int(risk_data.get("min_dte", 21)),
            max_dte=int(risk_data.get("max_dte", 60)),
            max_bid_ask_pct=float(risk_data.get("max_bid_ask_pct", 0.10)),
            min_open_interest=int(risk_data.get("min_open_interest", 100)),
            min_volume=int(risk_data.get("min_volume", 10)),
        )
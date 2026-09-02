from __future__ import annotations

import json
from pathlib import Path

from conviction_models import ConvictionResult


class DecisionLedger:
    """Append-only JSONL ledger. Never stores credentials."""

    def __init__(self, path: str | Path = "logs/decisions.jsonl") -> None:
        self.path = Path(path)

    def append(self, result: ConvictionResult) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        record = result.model_dump(mode="json")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
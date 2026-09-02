from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conviction_models import (
    Direction,
    EvidenceItem,
    EvidenceKind,
    EvidencePackage,
    OptionCandidate,
)
from options_selector import OptionCandidate as SelectorOptionCandidate
from scoring import ScoredCandidate

if TYPE_CHECKING:
    from options_data import OptionSnapshotData


def _make_evidence_id(kind: str, symbol: str, suffix: str = "") -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = f"{kind}-{symbol.upper()}-{date_str}"
    return f"{base}-{suffix}" if suffix else base


def _signal_to_evidence(signal, symbol: str) -> list[EvidenceItem]:
    """Convert MarketSignal components to EvidenceItems."""
    items = []
    for component in signal.components:
        if component.score is None:
            continue
        kind_map = {
            "regime": EvidenceKind.TECHNICAL,
            "momentum": EvidenceKind.TECHNICAL,
            "technical": EvidenceKind.TECHNICAL,
            "sentiment": EvidenceKind.NEWS,
            "volatility": EvidenceKind.OPTIONS,
        }
        items.append(EvidenceItem(
            evidence_id=component.evidence_id,
            kind=kind_map.get(component.name, EvidenceKind.TECHNICAL),
            source="phase2_signal",
            title=component.name.title(),
            observed_at=datetime.now(timezone.utc),
            summary=component.reason,
            relevance=int(component.weight * 100),
            quality=85,
            freshness=95,
            corroboration_count=1,
            primary_source=True,
        ))
    return items


def _option_chain_to_evidence(
    chain: dict[str, "OptionSnapshotData"],
    symbol: str,
    selected_contracts: list[SelectorOptionCandidate],
) -> list[EvidenceItem]:
    """Convert option chain snapshots to EvidenceItems."""
    items = []
    selected_symbols = {c.contract.symbol for c in selected_contracts}

    for sym, snap in chain.items():
        if sym not in selected_symbols:
            continue

        eid = _make_evidence_id("OPT", symbol, f"IV-{snap.strike:.0f}")
        if snap.implied_volatility is not None:
            items.append(EvidenceItem(
                evidence_id=eid,
                kind=EvidenceKind.OPTIONS,
                source="phase2_option_chain",
                title=f"IV {sym}",
                observed_at=datetime.now(timezone.utc),
                summary=f"Implied volatility {snap.implied_volatility:.2%}",
                relevance=80,
                quality=90,
                freshness=90,
                corroboration_count=1,
                primary_source=True,
            ))

        eid = _make_evidence_id("OPT", symbol, f"GREEKS-{snap.strike:.0f}")
        if snap.delta is not None:
            items.append(EvidenceItem(
                evidence_id=eid,
                kind=EvidenceKind.OPTIONS,
                source="phase2_option_chain",
                title=f"Greeks {sym}",
                observed_at=datetime.now(timezone.utc),
                summary=f"Delta={snap.delta:.3f} Gamma={snap.gamma:.4f} Theta={snap.theta:.4f} Vega={snap.vega:.4f}",
                relevance=85,
                quality=90,
                freshness=90,
                corroboration_count=1,
                primary_source=True,
            ))

    return items


def _risk_to_evidence(symbol: str, passed: bool, reasons: tuple[str, ...], failures: tuple[str, ...]) -> EvidenceItem:
    """Create risk validation evidence item."""
    return EvidenceItem(
        evidence_id=_make_evidence_id("RISK", symbol, "VALIDATION"),
        kind=EvidenceKind.RISK,
        source="phase2_risk",
        title="Risk Validation",
        observed_at=datetime.now(timezone.utc),
        summary="Risk check " + ("passed" if passed else "failed"),
        relevance=95,
        quality=100,
        freshness=100,
        corroboration_count=1,
        primary_source=True,
    )


def scored_candidate_to_option_candidate(
    scored: ScoredCandidate,
    signal,
    chain: dict[str, "OptionSnapshotData"],
    risk_result=None,
) -> OptionCandidate:
    """
    Convert Phase 2 ScoredCandidate to Phase 3 OptionCandidate.
    """
    option = scored.option
    direction = signal.direction.upper()
    direction_enum = Direction.BULLISH if direction == "BULLISH" else Direction.BEARISH

    # Build debit spread contracts
    from options_selector import build_debit_spread
    spread = build_debit_spread(
        direction=direction.lower(),
        long_contract=option.contract,
        chain={option.snapshot.symbol: option.snapshot},
        width=5.0,
    )

    if spread:
        long_leg, short_leg = spread
        contracts = (long_leg.symbol, short_leg.symbol)
        strikes = (long_leg.strike_price, short_leg.strike_price)
    else:
        # Fallback to single leg
        contracts = (option.contract.symbol,)
        strikes = (option.contract.strike_price,)

    # Collect evidence
    evidence_items = []
    evidence_items.extend(_signal_to_evidence(signal, option.contract.underlying_symbol))
    evidence_items.extend(_option_chain_to_evidence(chain, option.contract.underlying_symbol, [option]))
    if risk_result:
        evidence_items.append(_risk_to_evidence(
            option.contract.underlying_symbol,
            risk_result.approved,
            risk_result.reasons,
            risk_result.failures,
        ))

    evidence_package = EvidencePackage(items=tuple(evidence_items))

    return OptionCandidate(
        candidate_id=f"{option.contract.underlying_symbol}-CAND-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
        underlying=option.contract.underlying_symbol,
        direction=direction_enum,
        strategy="BULL_CALL_DEBIT_SPREAD" if direction == "BULLISH" else "BEAR_PUT_DEBIT_SPREAD",
        contracts=contracts,
        expiry=option.contract.expiration_date.isoformat(),
        strikes=strikes,
        quantity=1,
        max_loss=scored.max_loss or 0.0,
        max_reward=scored.max_reward or 0.0,
        signal_score=scored.total_score,
        evidence=evidence_package,
    )
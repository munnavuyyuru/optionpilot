from __future__ import annotations

from dataclasses import dataclass

from phase4_models import (
    RiskCheck,
    RiskDecision,
    RiskStatus,
    OptionRiskInput,
    PortfolioRiskInput,
)
from risk_policy import RiskPolicy
from position_sizing import validate_position_risk
from exposure import (
    validate_total_options_exposure,
    validate_symbol_exposure,
    validate_open_positions,
    validate_daily_loss,
    validate_duplicate_exposure,
)
from liquidity import validate_bid_ask, validate_liquidity, validate_dte


class RiskSentinel:
    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def evaluate(
        self,
        *,
        option: OptionRiskInput,
        portfolio: PortfolioRiskInput,
    ) -> RiskDecision:
        checks: list = []
        blocking: list[str] = []

        def add_check(
            name: str,
            passed: bool,
            reason: str,
            actual=None,
            limit=None,
        ) -> None:
            checks.append(
                RiskCheck(
                    name=name,
                    passed=passed,
                    reason=reason,
                    actual=actual,
                    limit=limit,
                )
            )
            if not passed:
                blocking.append(reason)

        # Position Risk
        passed, risk, reason = validate_position_risk(
            option.max_loss_per_contract_usd,
            option.quantity,
            self.policy.max_position_risk_usd,
        )
        add_check(
            "position_risk",
            passed,
            reason,
            actual=risk,
            limit=self.policy.max_position_risk_usd,
        )

        # Daily Loss
        daily_loss = abs(portfolio.daily_loss_usd)
        daily_ok = daily_loss < self.policy.max_daily_loss_usd

        add_check(
            "daily_loss",
            daily_ok,
            (
                "Daily loss is within policy."
                if daily_ok
                else (
                    f"Daily loss ${daily_loss:.2f} reaches/exceeds "
                    f"limit ${self.policy.max_daily_loss_usd:.2f}."
                )
            ),
            actual=daily_loss,
            limit=self.policy.max_daily_loss_usd,
        )

        # Total Options Exposure
        total_ok, projected_total, reason = validate_total_options_exposure(
            portfolio.total_options_exposure_usd,
            risk,
            self.policy.max_total_options_exposure_usd,
        )
        add_check(
            "total_options_exposure",
            total_ok,
            reason,
            actual=projected_total,
            limit=self.policy.max_total_options_exposure_usd,
        )

        # Symbol Exposure
        symbol_ok, projected_symbol, reason = validate_symbol_exposure(
            portfolio.symbol_exposure_usd,
            risk,
            self.policy.max_single_symbol_exposure_usd,
        )
        add_check(
            "symbol_exposure",
            symbol_ok,
            reason,
            actual=projected_symbol,
            limit=self.policy.max_single_symbol_exposure_usd,
        )

        # Open Positions
        positions_ok, projected_positions, reason = validate_open_positions(
            portfolio.open_positions,
            will_open_new_position=True,
            limit=self.policy.max_open_positions,
        )
        add_check(
            "open_positions",
            positions_ok,
            reason,
            actual=projected_positions,
            limit=self.policy.max_open_positions,
        )

        # Duplicate Exposure
        duplicate_ok = not portfolio.duplicate_symbol
        add_check(
            "duplicate_exposure",
            duplicate_ok,
            (
                "No duplicate exposure."
                if duplicate_ok
                else "Duplicate symbol exposure detected."
            ),
        )

        # DTE
        if option.dte is None:
            add_check(
                "dte",
                False,
                "DTE is missing; risk check fails closed.",
                actual=None,
                limit=f"{self.policy.min_dte}-{self.policy.max_dte}",
            )
        elif self.policy.min_dte <= option.dte <= self.policy.max_dte:
            add_check(
                "dte",
                True,
                "DTE is within policy.",
                actual=option.dte,
                limit=f"{self.policy.min_dte}-{self.policy.max_dte}",
            )
        else:
            add_check(
                "dte",
                False,
                (
                    f"DTE {option.dte} is outside "
                    f"{self.policy.min_dte}-{self.policy.max_dte}."
                ),
                actual=option.dte,
                limit=f"{self.policy.min_dte}-{self.policy.max_dte}",
            )

        # Bid/Ask Spread
        spread_ok, spread, reason = validate_bid_ask(
            option.bid,
            option.ask,
            self.policy.max_bid_ask_pct,
        )
        add_check(
            "bid_ask",
            spread_ok,
            reason,
            actual=spread,
            limit=self.policy.max_bid_ask_pct,
        )

        # Liquidity (OI + Volume)
        liquidity_ok, reason = validate_liquidity(
            option.open_interest,
            option.volume,
            self.policy.min_open_interest,
            self.policy.min_volume,
        )
        add_check(
            "liquidity",
            liquidity_ok,
            reason,
            actual={
                "open_interest": option.open_interest,
                "volume": option.volume,
            },
            limit={
                "open_interest": self.policy.min_open_interest,
                "volume": self.policy.min_volume,
            },
        )

        # Market Data Freshness
        add_check(
            "market_data_freshness",
            option.market_data_fresh,
            (
                "Market data is fresh."
                if option.market_data_fresh
                else "Market data is stale or unavailable."
            ),
        )

        approved = not blocking

        return RiskDecision(
            status=(
                RiskStatus.APPROVED
                if approved
                else RiskStatus.BLOCKED
            ),
            checks=tuple(checks),
            blocking_reasons=tuple(blocking),
        )
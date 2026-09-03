from src.risk_policy import RiskPolicy
from src.risk_sentinel import OptionRiskInput, PortfolioRiskInput, RiskSentinel


def sentinel():
    return RiskSentinel(RiskPolicy())


def valid_option():
    return OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )


def valid_portfolio():
    return PortfolioRiskInput(
        daily_loss_usd=0,
        total_options_exposure_usd=0,
        symbol_exposure_usd=0,
        open_positions=0,
        duplicate_symbol=False,
    )


def test_valid_risk_passes():
    result = sentinel().evaluate(
        option=valid_option(),
        portfolio=valid_portfolio(),
    )
    assert result.approved


def test_position_risk_too_high_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=600,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "position_risk" and not check.passed for check in result.checks)


def test_daily_loss_blocks():
    portfolio = PortfolioRiskInput(
        daily_loss_usd=-500,
        total_options_exposure_usd=0,
        symbol_exposure_usd=0,
        open_positions=0,
        duplicate_symbol=False,
    )
    result = sentinel().evaluate(option=valid_option(), portfolio=portfolio)
    assert not result.approved
    assert any(check.name == "daily_loss" and not check.passed for check in result.checks)


def test_total_exposure_blocks():
    portfolio = PortfolioRiskInput(
        daily_loss_usd=0,
        total_options_exposure_usd=4800,
        symbol_exposure_usd=0,
        open_positions=0,
        duplicate_symbol=False,
    )
    result = sentinel().evaluate(option=valid_option(), portfolio=portfolio)
    assert not result.approved
    assert any(check.name == "total_options_exposure" and not check.passed for check in result.checks)


def test_symbol_exposure_blocks():
    portfolio = PortfolioRiskInput(
        daily_loss_usd=0,
        total_options_exposure_usd=0,
        symbol_exposure_usd=1400,
        open_positions=0,
        duplicate_symbol=False,
    )
    result = sentinel().evaluate(option=valid_option(), portfolio=portfolio)
    assert not result.approved
    assert any(check.name == "symbol_exposure" and not check.passed for check in result.checks)


def test_max_positions_blocks():
    portfolio = PortfolioRiskInput(
        daily_loss_usd=0,
        total_options_exposure_usd=0,
        symbol_exposure_usd=0,
        open_positions=5,
        duplicate_symbol=False,
    )
    result = sentinel().evaluate(option=valid_option(), portfolio=portfolio)
    assert not result.approved
    assert any(check.name == "open_positions" and not check.passed for check in result.checks)


def test_duplicate_blocks():
    portfolio = PortfolioRiskInput(
        daily_loss_usd=0,
        total_options_exposure_usd=0,
        symbol_exposure_usd=0,
        open_positions=0,
        duplicate_symbol=True,
    )
    result = sentinel().evaluate(option=valid_option(), portfolio=portfolio)
    assert not result.approved
    assert any(check.name == "duplicate_exposure" and not check.passed for check in result.checks)


def test_wide_spread_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=5.0,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "bid_ask" and not check.passed for check in result.checks)


def test_missing_bid_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "bid_ask" and not check.passed for check in result.checks)


def test_low_oi_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=4.1,
        open_interest=50,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "liquidity" and not check.passed for check in result.checks)


def test_low_volume_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=5,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "liquidity" and not check.passed for check in result.checks)


def test_dte_too_low_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=10,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "dte" and not check.passed for check in result.checks)


def test_dte_too_high_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=70,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "dte" and not check.passed for check in result.checks)


def test_missing_dte_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=None,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "dte" and not check.passed for check in result.checks)


def test_stale_data_blocks():
    option = OptionRiskInput(
        max_loss_per_contract_usd=200,
        quantity=1,
        dte=30,
        bid=4.0,
        ask=4.1,
        open_interest=500,
        volume=100,
        market_data_fresh=False,
    )
    result = sentinel().evaluate(option=option, portfolio=valid_portfolio())
    assert not result.approved
    assert any(check.name == "market_data_freshness" and not check.passed for check in result.checks)
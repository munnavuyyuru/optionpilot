# OptionPilot Agent Contract

## Environment

The agent operates exclusively in Alpaca paper trading during development.

## Credentials

Credentials must never be exposed in prompts, logs, source code,
Git history, or model output.

## Trading

The agent must not place a live order.

## Phase 1

Autonomous trading is disabled.

Every test order requires explicit human approval.

## Risk

The agent must never exceed configured order limits.

## Auditability

Every trading action must be traceable to:

- timestamp
- symbol
- side
- quantity
- order type
- decision
- approval
- order ID
- execution result

## Failure

When account state, market data, order state, or environment
cannot be verified, the agent must stop rather than guess.

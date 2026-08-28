"""Run first. Confirms keys work, account is paper, and options are enabled."""
from alpaca.trading.client import TradingClient
from agent.config import require_alpaca, PAPER

def main() -> None:
    api_key, secret_key = require_alpaca()
    client = TradingClient(api_key, secret_key, paper=PAPER)
    acct = client.get_account()

    print(f"account id      {acct.id}")
    print(f"status          {acct.status}")
    print(f"equity          ${float(acct.equity):,.2f}")
    print(f"buying power    ${float(acct.buying_power):,.2f}")
    print(f"options level   {getattr(acct, 'options_trading_level', 'n/a')}")
    print(f"options bp      {getattr(acct, 'options_buying_power', 'n/a')}")

    equity = float(acct.equity)
    if abs(equity - 100_000) > 1:
        print(f"\n  WARNING: equity is ${equity:,.2f}, hackathon requires exactly $100,000.")
        print("  Reset it in the dashboard: Paper account -> Reset -> set 100000")

    lvl = getattr(acct, "options_trading_level", 0) or 0
    if int(lvl) < 1:
        print("\n  WARNING: options not enabled. Request approval in the dashboard")
        print("  before building — every strategy must use options.")

    print(f"\n  Submit this account id with your project: {acct.id}")

if __name__ == "__main__":
    main()

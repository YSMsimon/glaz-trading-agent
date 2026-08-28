from agent.analytics import Leg, analyze, value_at

def test_long_call_unbounded_up_limited_loss():
    p = analyze([Leg("buy", "call", 100, 3.0)])
    assert p.max_profit is None                 # unlimited upside
    assert p.max_loss == -300                    # premium paid x100
    assert abs(p.breakevens[0] - 103) < 0.5

def test_bull_call_spread_defined():
    # buy 100 call @3, sell 110 call @1  -> debit 2.00
    legs = [Leg("buy","call",100,3.0), Leg("sell","call",110,1.0)]
    p = analyze(legs)
    assert p.net == -200                          # net debit
    assert p.max_loss == -200                      # can't lose more than debit
    assert p.max_profit == 800                     # (10 width - 2) x100
    assert abs(p.breakevens[0] - 102) < 0.5

def test_credit_put_spread():
    # sell 100 put @3, buy 90 put @1 -> credit 2.00, width 10
    legs = [Leg("sell","put",100,3.0), Leg("buy","put",90,1.0)]
    p = analyze(legs)
    assert p.net == 200                            # credit received
    assert p.max_profit == 200
    assert p.max_loss == -800

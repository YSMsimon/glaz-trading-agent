from agent.risk import check_order

BASE = dict(contracts=1, contract_price=2.0, kind_is_defined_risk=True,
            dte=21, equity=100_000, open_positions=0, daily_pl=0.0)

def test_clean_order_passes():
    assert check_order(**BASE).ok

def test_oversize_flagged():
    v = check_order(**{**BASE, "contract_price": 60.0})  # $6000 > 5% of 100k
    assert not v.ok and any("position" in x for x in v.warnings)

def test_naked_short_blocked():
    v = check_order(**{**BASE, "kind_is_defined_risk": False})
    assert not v.ok and any("naked" in x for x in v.warnings)

def test_dte_bounds():
    assert not check_order(**{**BASE, "dte": 3}).ok
    assert not check_order(**{**BASE, "dte": 60}).ok

def test_daily_halt():
    v = check_order(**{**BASE, "daily_pl": -4000})  # > 3% of 100k
    assert not v.ok and any("daily loss" in x for x in v.warnings)

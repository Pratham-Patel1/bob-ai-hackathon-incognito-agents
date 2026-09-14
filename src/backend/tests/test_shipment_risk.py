"""
Tests for ShipmentRiskEngine.
"""
import pytest
from datetime import datetime, timedelta, timezone
from backend.engines.shipment_risk import run, RiskResult, _level_from_score


def _now_plus(hours: float) -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=hours)
    return dt.isoformat()


def _shipment(**kwargs):
    base = {
        "scheduled_arrival": _now_plus(48),
        "cargo_value_usd": 10_000,
        "temperature_required": False,
    }
    base.update(kwargs)
    return base


def _disruption(severity="high"):
    return {"severity": severity}


def test_no_disruptions_low_risk():
    result = run(_shipment(), active_disruptions=[])
    assert result.score < 0.3
    assert result.level == "low"


def test_critical_disruption_raises_score():
    result = run(_shipment(), active_disruptions=[_disruption("critical")])
    assert result.score >= 0.27  # 0.30 * 1.0 multiplier


def test_compound_disruption_penalty():
    result_one = run(_shipment(), active_disruptions=[_disruption("high")])
    result_two = run(_shipment(), active_disruptions=[_disruption("high"), _disruption("high")])
    # Compound penalty adds +0.10
    assert result_two.score > result_one.score
    assert result_two.score >= result_one.score + 0.09


def test_urgency_factor():
    urgent = _shipment(scheduled_arrival=_now_plus(12))  # < 24h
    not_urgent = _shipment(scheduled_arrival=_now_plus(72))
    disruptions = [_disruption("medium")]
    result_urgent = run(urgent, disruptions)
    result_not = run(not_urgent, disruptions)
    assert result_urgent.score > result_not.score


def test_high_value_cargo():
    cheap = _shipment(cargo_value_usd=5_000)
    expensive = _shipment(cargo_value_usd=200_000)
    disruptions = [_disruption("medium")]
    assert run(expensive, disruptions).score > run(cheap, disruptions).score


def test_cold_chain_excursion():
    s = _shipment(temperature_required=True)
    without = run(s, [], temperature_excursion=False)
    with_exc = run(s, [], temperature_excursion=True)
    assert with_exc.score > without.score


def test_low_carrier_reliability():
    good_carrier = {"reliability_score": 0.95}
    bad_carrier = {"reliability_score": 0.50}
    s = _shipment()
    result_good = run(s, [], carrier=good_carrier)
    result_bad = run(s, [], carrier=bad_carrier)
    assert result_bad.score > result_good.score


def test_score_clamped_to_1():
    """Worst-case scenario should not exceed 1.0."""
    s = _shipment(
        scheduled_arrival=_now_plus(6),
        cargo_value_usd=500_000,
        temperature_required=True,
    )
    disrupt = [_disruption("critical"), _disruption("critical"), _disruption("critical")]
    result = run(s, disrupt, temperature_excursion=True, carrier={"reliability_score": 0.3})
    assert result.score <= 1.0


def test_level_mapping():
    assert _level_from_score(0.1) == "low"
    assert _level_from_score(0.4) == "medium"
    assert _level_from_score(0.7) == "high"
    assert _level_from_score(0.9) == "critical"


def test_factors_populated():
    result = run(_shipment(), active_disruptions=[_disruption("high")])
    assert len(result.factors) > 0
    assert result.explanation != ""

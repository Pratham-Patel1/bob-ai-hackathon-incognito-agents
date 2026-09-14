"""
Tests for BusinessImpactEngine — Phase 2E

Run with:
    pytest src/backend/tests/test_business_impact.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.business_impact import (
    BusinessImpactResult,
    _CARGO_RISK_CAP_PCT,
    _SLA_PENALTY_CAP_PCT,
    calculate_business_impact,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shipment(
    cargo_value_usd: float = 100_000.0,
    cargo_type: str = "general",
    temperature_required: bool = False,
    weight_kg: float = 500.0,
    priority: str = "medium",
) -> dict:
    return {
        "cargo_value_usd": cargo_value_usd,
        "cargo_type": cargo_type,
        "temperature_required": temperature_required,
        "weight_kg": weight_kg,
        "priority": priority,
    }


def _disruption(
    delay_hours: float = 12.0,
    severity: str = "medium",
    disruption_type: str = "weather",
) -> dict:
    return {
        "delay_hours": delay_hours,
        "severity": severity,
        "disruption_type": disruption_type,
    }


# ---------------------------------------------------------------------------
# Zero delay — no impact
# ---------------------------------------------------------------------------

class TestZeroDelay:
    def test_zero_delay_zero_cargo_risk(self):
        result = calculate_business_impact(_shipment(), _disruption(delay_hours=0.0))
        assert result.cargo_value_at_risk_usd == pytest.approx(0.0)

    def test_zero_delay_zero_sla_penalty(self):
        result = calculate_business_impact(_shipment(), _disruption(delay_hours=0.0))
        assert result.sla_penalty_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Cargo type risk rates
# ---------------------------------------------------------------------------

class TestCargoTypeRates:
    def test_temperature_sensitive_higher_than_general(self):
        gen  = calculate_business_impact(_shipment(cargo_type="general"),             _disruption(delay_hours=10))
        temp = calculate_business_impact(_shipment(cargo_type="temperature_sensitive"), _disruption(delay_hours=10))
        assert temp.cargo_value_at_risk_usd > gen.cargo_value_at_risk_usd

    def test_temperature_flag_triggers_temp_sensitive_rate(self):
        gen_temp = calculate_business_impact(
            _shipment(cargo_type="general", temperature_required=True),
            _disruption(delay_hours=10),
        )
        gen_only = calculate_business_impact(
            _shipment(cargo_type="general", temperature_required=False),
            _disruption(delay_hours=10),
        )
        assert gen_temp.cargo_value_at_risk_usd > gen_only.cargo_value_at_risk_usd

    def test_hazmat_higher_than_general(self):
        gen   = calculate_business_impact(_shipment(cargo_type="general"), _disruption(delay_hours=10))
        haz   = calculate_business_impact(_shipment(cargo_type="hazmat"),  _disruption(delay_hours=10))
        assert haz.cargo_value_at_risk_usd > gen.cargo_value_at_risk_usd


# ---------------------------------------------------------------------------
# SLA penalty by priority
# ---------------------------------------------------------------------------

class TestSLAPenalty:
    def test_critical_priority_higher_penalty_than_low(self):
        low  = calculate_business_impact(_shipment(priority="low"),      _disruption(delay_hours=10))
        crit = calculate_business_impact(_shipment(priority="critical"),  _disruption(delay_hours=10))
        assert crit.sla_penalty_usd > low.sla_penalty_usd

    def test_longer_delay_higher_penalty(self):
        r_short = calculate_business_impact(_shipment(), _disruption(delay_hours=5))
        r_long  = calculate_business_impact(_shipment(), _disruption(delay_hours=50))
        assert r_long.sla_penalty_usd > r_short.sla_penalty_usd

    def test_sla_penalty_capped_at_25pct_cargo_value(self):
        # Very long delay — penalty should cap at 25% of $100k = $25k
        result = calculate_business_impact(_shipment(cargo_value_usd=100_000), _disruption(delay_hours=10_000))
        assert result.sla_penalty_usd <= 100_000 * _SLA_PENALTY_CAP_PCT + 0.01


# ---------------------------------------------------------------------------
# Cargo at risk caps
# ---------------------------------------------------------------------------

class TestCargoAtRiskCap:
    def test_cargo_at_risk_never_exceeds_80pct(self):
        result = calculate_business_impact(
            _shipment(cargo_type="temperature_sensitive", cargo_value_usd=100_000),
            _disruption(delay_hours=10_000),
        )
        assert result.cargo_value_at_risk_usd <= 100_000 * _CARGO_RISK_CAP_PCT + 0.01


# ---------------------------------------------------------------------------
# Extra transport cost
# ---------------------------------------------------------------------------

class TestExtraTransportCost:
    def test_provided_alternative_cost_used_directly(self):
        result = calculate_business_impact(
            _shipment(),
            _disruption(),
            alternative_route_cost_usd=5000.0,
        )
        assert result.extra_transport_cost_usd == pytest.approx(5000.0)

    def test_estimated_cost_higher_for_critical_severity(self):
        r_low  = calculate_business_impact(_shipment(), _disruption(severity="low"))
        r_crit = calculate_business_impact(_shipment(), _disruption(severity="critical"))
        assert r_crit.extra_transport_cost_usd > r_low.extra_transport_cost_usd


# ---------------------------------------------------------------------------
# Total exposure
# ---------------------------------------------------------------------------

class TestTotalExposure:
    def test_total_is_sum_of_components(self):
        result = calculate_business_impact(_shipment(), _disruption())
        expected = (result.cargo_value_at_risk_usd
                    + result.sla_penalty_usd
                    + result.extra_transport_cost_usd)
        assert result.total_financial_exposure_usd == pytest.approx(expected, abs=0.01)

    def test_total_exposure_non_negative(self):
        result = calculate_business_impact(_shipment(), _disruption(delay_hours=0))
        assert result.total_financial_exposure_usd >= 0.0

    def test_breakdown_dict_matches_fields(self):
        result = calculate_business_impact(_shipment(), _disruption())
        assert result.breakdown["cargo_value_at_risk_usd"] == result.cargo_value_at_risk_usd
        assert result.breakdown["sla_penalty_usd"] == result.sla_penalty_usd
        assert result.breakdown["extra_transport_cost_usd"] == result.extra_transport_cost_usd
        assert result.breakdown["total_financial_exposure_usd"] == result.total_financial_exposure_usd

    def test_risk_percentage_reasonable(self):
        result = calculate_business_impact(_shipment(cargo_value_usd=100_000), _disruption(delay_hours=10))
        assert 0.0 <= result.risk_percentage <= 100.0


# ---------------------------------------------------------------------------
# No disruption context
# ---------------------------------------------------------------------------

class TestNoDisruption:
    def test_no_disruption_context_no_crash(self):
        result = calculate_business_impact(_shipment(), None)
        assert isinstance(result, BusinessImpactResult)

    def test_no_disruption_zero_delay_zero_risk(self):
        result = calculate_business_impact(_shipment(), None)
        # No delay → no cargo risk, no SLA penalty
        assert result.cargo_value_at_risk_usd == pytest.approx(0.0)
        assert result.sla_penalty_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_business_impact_result(self):
        result = calculate_business_impact(_shipment(), _disruption())
        assert isinstance(result, BusinessImpactResult)

    def test_factors_list_of_strings(self):
        result = calculate_business_impact(_shipment(), _disruption())
        assert all(isinstance(f, str) for f in result.factors)

    def test_deterministic_same_input(self):
        s = _shipment()
        d = _disruption()
        r1 = calculate_business_impact(s, d)
        r2 = calculate_business_impact(s, d)
        assert r1.total_financial_exposure_usd == r2.total_financial_exposure_usd

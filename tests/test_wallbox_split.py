"""Tests for wallbox/house consumption split (Phase: Wallbox-Provider).

The actual sensor read + subtraction lives in the coordinator and requires
Home Assistant runtime. These tests cover the contract on the data class and
the invariant that the rule engine is not influenced by wallbox_power.
"""
from datetime import datetime, timezone

from custom_components.e3dc_maestro.control_engine import (
    MaestroParams,
    MaestroState,
    decide,
)
from custom_components.e3dc_maestro.const import PHASE_OFF


def _state(**overrides) -> MaestroState:
    base = dict(
        soc=60.0,
        pv_power=2000.0,
        house_power=400.0,
        grid_power=0.0,
        battery_power=0.0,
    )
    base.update(overrides)
    return MaestroState(**base)


def test_wallbox_power_defaults_to_zero():
    """MaestroState must accept the new field with a safe default."""
    s = _state()
    assert s.wallbox_power == 0.0


def test_wallbox_power_is_settable():
    s = _state(wallbox_power=7400.0)
    assert s.wallbox_power == 7400.0


def test_decide_unaffected_by_wallbox_power():
    """The rule engine must operate on house_power only — adding a wallbox
    load must NOT change the resulting decision when house_power is fixed."""
    params = MaestroParams()
    now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    base = _state(soc=60.0, pv_power=3000.0, house_power=500.0)
    with_ev = _state(soc=60.0, pv_power=3000.0, house_power=500.0, wallbox_power=11000.0)
    # The decision should depend solely on house_power; wallbox_power is
    # exposed for telemetry only.
    d_base = decide(base, params, now, regelung_aktiv=False)
    d_ev = decide(with_ev, params, now, regelung_aktiv=False)
    # Both should be PHASE_OFF (regelung_aktiv=False) — sanity gate.
    assert d_base.phase == PHASE_OFF
    assert d_ev.phase == PHASE_OFF
    # And the surplus calculation inside the engine uses house_power, not
    # house+wallbox: assert by structural equality of the visible fields.
    assert d_base.target_charge_power == d_ev.target_charge_power
    assert d_base.power_mode == d_ev.power_mode

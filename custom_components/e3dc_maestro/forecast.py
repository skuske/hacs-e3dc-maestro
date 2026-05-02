"""F1: 24-hour battery SoC forecast simulator.

Uses the pure ``decide()`` function from the rule engine to step through
the next 24 hours and estimate the battery state of charge trajectory,
grid exchange and self-sufficiency.

The simulation is deterministic and runs fully in-process without I/O,
so it can be called from both the coordinator and the F3 optimizer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .const import (
    PHASE_MORNING_DISCHARGE,
    POWER_MODE_CHARGE,
    POWER_MODE_CHARGE_FROM_GRID,
    POWER_MODE_DISCHARGE,
    POWER_MODE_IDLE,
    POWER_MODE_NORMAL,
)
from .control_engine import MaestroDecision, MaestroParams, MaestroState, decide

if TYPE_CHECKING:
    pass


@dataclass
class ForecastResult:
    """Result of a 24-hour simulation."""

    # SoC values after each simulated hour (index 0 = after hour 0, i.e. 1h from now)
    trajectory_soc: list[float]          # len=24
    trajectory_hours: list[int]          # UTC hour-of-day for each step (len=24)
    trajectory_phases: list[str]         # phase returned by decide() (len=24)

    min_soc: float                       # min SoC over 24h
    max_soc: float                       # max SoC over 24h

    grid_draw_kwh: float                 # total kWh drawn from grid (>0 = bad)
    grid_feed_in_kwh: float              # total kWh fed into grid (>0 = good)

    # Fraction of house consumption covered without drawing from grid (0–1)
    self_sufficiency: float | None = None

    # PV lost due to full battery + feed-in cap
    pv_curtailed_kwh: float = 0.0


def simulate_next_24h(
    *,
    soc: float,
    consumption_h: list[float],  # 24 hourly mean W values indexed by UTC hour-of-day
    pv_h: list[float],            # 24 hourly mean W values indexed by UTC hour-of-day
    params: MaestroParams,
    now: datetime,
    battery_capacity_kwh: float = 15.0,
    regelung_aktiv: bool = True,
    max_discharge_power: float | None = None,
) -> ForecastResult:
    """Simulate the next 24 hours starting from *soc* %.

    Parameters
    ----------
    soc:
        Starting state of charge in percent (0–100).
    consumption_h:
        Average house consumption for each UTC hour of the day (W), len=24.
    pv_h:
        Average PV production for each UTC hour of the day (W), len=24.
    params:
        Current MaestroParams (used as-is for all 24 steps).
    now:
        Current UTC datetime.  Simulation starts at *now* rounded to the hour.
    battery_capacity_kwh:
        Usable battery capacity in kWh.
    regelung_aktiv:
        Whether the Maestro rule engine is enabled.
    max_discharge_power:
        Maximum battery discharge power in W.  Defaults to ``params.inverter_power``.
    """
    if battery_capacity_kwh <= 0:
        battery_capacity_kwh = 15.0
    capacity_wh = battery_capacity_kwh * 1000.0
    max_disch_w = max_discharge_power or params.inverter_power

    # Round to current hour
    base = now.replace(minute=0, second=0, microsecond=0, tzinfo=now.tzinfo or timezone.utc)

    trajectory_soc: list[float] = []
    trajectory_hours: list[int] = []
    trajectory_phases: list[str] = []
    total_consumption_wh = 0.0
    grid_draw_wh = 0.0
    grid_feed_wh = 0.0
    pv_curtailed_wh = 0.0

    # Feed-in limit in W (inf = no limit configured)
    feed_in_limit_w = (
        params.feed_in_limit_percent / 100.0 * params.installed_kwp * 1000.0
        if params.feed_in_limit_percent > 0 and params.installed_kwp > 0
        else float("inf")
    )

    current_soc = float(soc)

    for h in range(24):
        sim_now = base + timedelta(hours=h + 1)
        hour_idx = sim_now.hour  # 0–23, UTC hour for consumption/pv lookup

        cons_w = max(0.0, float(consumption_h[hour_idx]))
        pv_w = max(0.0, float(pv_h[hour_idx]))

        # Approximate grid for state construction (grid balances the system)
        pv_surplus_w = pv_w - cons_w  # positive = export without battery

        state = MaestroState(
            soc=current_soc,
            pv_power=pv_w,
            house_power=cons_w,
            # Approximate: grid covers any deficit not yet compensated by battery
            grid_power=max(0.0, -pv_surplus_w),
            battery_power=0.0,
        )

        decision: MaestroDecision = decide(
            state, params, sim_now, regelung_aktiv=regelung_aktiv
        )
        phase = decision.phase

        # ── Determine battery net power for this hour ──────────────────────
        # Discriminator ist primär der power_mode, NICHT charge_power_limit:
        # seit dem Spreading-/Idle-Fix liefert decide() bei „Ladung gesperrt,
        # Entladung frei" power_mode=NORMAL mit charge_power_limit=1 (1 W
        # Sentinel). Wenn man hier 1 W als „lade konstant" interpretiert,
        # wird der ganze 24h-Trace flach – obwohl der Akku nachts realistisch
        # entladen würde, um den Hausverbrauch zu decken.
        if decision.power_mode == POWER_MODE_DISCHARGE or phase == PHASE_MORNING_DISCHARGE:
            # Forced discharge: cover house consumption.
            bat_net_w = -min(max_disch_w, cons_w)
        elif decision.power_mode == POWER_MODE_IDLE:
            # Hard idle (z. B. HT-Schutz): kein Akku-Fluss.
            bat_net_w = 0.0
        elif decision.power_mode in (POWER_MODE_CHARGE, POWER_MODE_CHARGE_FROM_GRID) and (
            decision.charge_power_limit is not None and decision.charge_power_limit > 1
        ):
            # Echte Zwangsladung (Korridor, Spreading aktiv, Notfall, Curtailment).
            # Das 1-W-Sentinel ist hier ausgeschlossen – das ist NORMAL + cap.
            bat_net_w = min(decision.charge_power_limit, params.max_charge_power)
        else:
            # NORMAL (auch mit charge_power_limit=1 als „Laden gesperrt"-Sentinel):
            # passive PV-Pufferung + freies Entladen bei Defizit.
            charge_cap = params.max_charge_power
            if decision.charge_power_limit is not None:
                charge_cap = min(charge_cap, max(0, int(decision.charge_power_limit)))
            if pv_surplus_w > 0:
                bat_net_w = min(pv_surplus_w, charge_cap)
            else:
                bat_net_w = max(-max_disch_w, pv_surplus_w)

        # ── SoC update ──────────────────────────────────────────────────────
        delta_wh = bat_net_w * 1.0  # 1 hour
        raw_soc = current_soc + delta_wh / capacity_wh * 100.0
        # Clamp to [0, 100] and track rejected charge (battery full)
        if raw_soc > 100.0:
            rejected_wh = (raw_soc - 100.0) / 100.0 * capacity_wh
            bat_net_w -= rejected_wh  # adjust for grid accounting below
            current_soc = 100.0
        elif raw_soc < 0.0:
            current_soc = 0.0
        else:
            current_soc = raw_soc

        # ── Grid accounting with curtailment ────────────────────────────────
        # grid_net > 0 = feed-in, grid_net < 0 = draw
        grid_net_w = pv_w - cons_w - bat_net_w
        if grid_net_w < 0:
            grid_draw_wh += abs(grid_net_w)
        else:
            # Anything above the feed-in limit is curtailed (physically lost)
            if grid_net_w > feed_in_limit_w:
                pv_curtailed_wh += grid_net_w - feed_in_limit_w
                grid_feed_wh += feed_in_limit_w
            else:
                grid_feed_wh += grid_net_w

        total_consumption_wh += cons_w

        trajectory_soc.append(round(current_soc, 1))
        trajectory_hours.append(hour_idx)
        trajectory_phases.append(phase)

    min_soc = min(trajectory_soc) if trajectory_soc else current_soc
    max_soc = max(trajectory_soc) if trajectory_soc else current_soc

    self_sufficiency: float | None = None
    if total_consumption_wh > 0:
        covered_wh = total_consumption_wh - grid_draw_wh
        self_sufficiency = round(max(0.0, min(1.0, covered_wh / total_consumption_wh)), 3)

    return ForecastResult(
        trajectory_soc=trajectory_soc,
        trajectory_hours=trajectory_hours,
        trajectory_phases=trajectory_phases,
        min_soc=round(min_soc, 1),
        max_soc=round(max_soc, 1),
        grid_draw_kwh=round(grid_draw_wh / 1000.0, 3),
        grid_feed_in_kwh=round(grid_feed_wh / 1000.0, 3),
        pv_curtailed_kwh=round(pv_curtailed_wh / 1000.0, 3),
        self_sufficiency=self_sufficiency,
    )

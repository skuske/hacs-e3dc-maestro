# v0.3.3 – Bugfix: Forecast-Grid-Bilanz bei leerem Akku

Patch-Release. Reine Fehlerbehebung in der 24h-SoC-Forecast-Simulation.

## ⬆️ Upgrade-Hinweis

Einfach via HACS aktualisieren. HA lädt die Integration automatisch neu.
Keine Konfigurationsänderung, keine Migration nötig.

## 🐛 Bugfix

- **Forecast-Simulator buchte den Hausverbrauch nicht ans Netz, wenn der
  Akku in der Prognose auf 0 % lief.**
  Folge: Sensoren `forecast_min_soc_nachste_24h` zeigten korrekt 0 %, aber
  `grid_draw_kwh` blieb bei 0 und `self_sufficiency` bei 100 % – obwohl die
  Trajektorie eine Nachtphase mit leerem Akku enthielt, die physikalisch
  nur aus dem Netz versorgt werden kann.

  **Fix:** Beim SoC-Clamp auf 0 wird das nicht mehr aus dem Akku entnehmbare
  Defizit zurück in `bat_net_w` korrigiert, sodass die Bilanzgleichung
  `grid_net = pv − cons − bat_net` stimmt. Die nicht aus dem Akku gedeckten
  kWh wandern jetzt korrekt in `grid_draw_kwh`, und `self_sufficiency`
  spiegelt die reale Eigenversorgungsquote wider.

## 🔍 Diagnostik

- Neuer Debug-Log in [`control_engine.py`](custom_components/e3dc_maestro/control_engine.py)
  am `pv_delay`-Gate: bei aktivem Debug-Logger
  (`logger.logs.custom_components.e3dc_maestro: debug`) protokolliert jeder
  `decide()`-Zyklus, ob die Phase auslösen würde und welches Kriterium sie
  ggf. blockt (Format `[pv_delay-gate] ...`). Hilft, Korner-Cases mit
  Spreading- vs. pv_delay-Konflikt nachzuvollziehen.

## ✅ Tests

- 235 Unit-Tests grün (1 neuer Regressionstest:
  `test_grid_draw_accounted_after_soc_clamp_to_zero`).

## 🔗 Bezug zu v0.3.2 / v0.3.1

Alle Fixes und Features aus v0.3.1/v0.3.2 sind unverändert enthalten.
v0.3.3 ist ein reiner Bugfix-Patch obendrauf.

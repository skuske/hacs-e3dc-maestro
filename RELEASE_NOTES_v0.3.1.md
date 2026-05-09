# v0.3.1 – Wallbox-Verbrauchstrennung, openWB & EVCC Auto-Erkennung, RSCP-Auto-Detect, Hardware-Schutz Spreading

## ⬆️ Upgrade-Hinweis

Nach dem Update empfiehlt sich ein einmaliger Durchlauf des Konfigurations-Wizards
(**Einstellungen → Geräte & Dienste → E3DC Maestro → Konfigurieren**),
damit die Auto-Erkennung für Wallbox-Sensor, EVCC und die RSCP-Quellen/Systemparameter ausgeführt wird und die
neuen Felder mit sinnvollen Werten vorbelegt werden.

**Wichtig für Bestandsuser:**
- Wenn `Netzbezug heute` bisher 0 kWh anzeigte, im Schritt „Quell-Entities" auf den RSCP-Sensor `sensor.*_transfer_to_from_grid` umstellen und die neue Option **„Vorzeichen Netzleistung invertieren"** aktivieren (Auto-Detect schlägt das automatisch vor).
- Beim ersten HA-Start nach dem Update läuft eine einmalige Config-Entry-Migration (v2 → v3), die den Spreading-Switch automatisch aktiviert. Wer das nicht möchte, kann ihn anschließend im UI wieder ausschalten.

Ein HA-Neustart ist **nicht** erforderlich (HA lädt die Integration nach dem Update selbst neu; die Migration läuft dabei automatisch).


Qualitäts-Release mit saubererer Verbrauchsabrechnung, Auto-Erkennung für openWB/EVCC, vollautomatischer Übernahme der Sensoren und Systemparameter aus der E3DC-RSCP-Integration, drei neuen Sensoren – sowie einem Hardware-Schutz, der den Spreading-Modus standardmäßig aktiviert, um 0/max-Lade-Bursts im Auto-Modus zu vermeiden.

## ✨ Neue Features

### Haus / Wallbox Verbrauchstrennung
- Neues Feld **Wallbox-Powersensor** im Konfigurations-Wizard (Schritt 7).
  Wird der Sensor belegt, separiert Maestro den EV-Ladeverbrauch vom Hausverbrauch —
  EWMA-Glättung, PV-Forecast und der Optimizer werden nicht mehr durch Ladespitzen verfälscht.
- Neue Option **„Hausverbrauchszähler enthält die Wallbox bereits"**:
  - `false` (E3DC-nativ): E3DC hat einen separaten Wallbox-Powermeter → Maestro zählt Wallbox zusätzlich als Last.
  - `true` (openWB am EVU-Zähler): Wallbox-Strom steckt bereits im Hausverbrauch-Sensor → Maestro zieht ihn ab, um den reinen Hausverbrauch zu ermitteln.
- Separate EWMA-Instanz für Wallbox-Leistung verhindert, dass EV-Ladepeaks den Haus-EWMA dauerhaft verzerren.

### Drei neue Sensoren
| Entity | Einheit | Beschreibung |
|---|---|---|
| `sensor.e3dc_maestro_wallbox_leistung` | W | Aktueller Wallbox-Verbrauch (geglättet) |
| `sensor.e3dc_maestro_gesamtlast_leistung` | W | Haus + Wallbox (Gesamtlast aus Sicht des WR) |
| `sensor.e3dc_maestro_wallbox_energie_heute` | kWh | Kumulierter Wallbox-Tagesverbrauch (`state_class: total_increasing`, Energy-Dashboard-tauglich) |

### Auto-Erkennung für openWB
- Wizard scannt automatisch nach `sensor.openwb_chargepoint_<N>_ladeleistung` (niedrigste CP-Nummer gewinnt).
- Bei Fund wird der Wallbox-Powersensor vorbelegt, Wallbox-Typ auf `generic` gesetzt und
  „Hausverbrauch enthält Wallbox" auf `true` (openWB misst am EVU-Zähler).

### Auto-Erkennung für EVCC (`evcc_intg`)
- Wizard erkennt die [marq24/ha-evcc](https://github.com/marq24/ha-evcc)-Integration (Domain `evcc_intg`).
- Er wählt automatisch den ersten `binary_sensor.*_charging` und `select.*_mode` (alphabetisch).
- `evcc_now_value` wird auf `"now"` vorbelegt.
- EVCC-Auto-Erkennung läuft orthogonal zur openWB/E3DC-Erkennung — alle drei können parallel aktiv sein.

### Auto-Erkennung: verbesserter Erkennungs-Dialog
- „Erkannte Quellen"-Zusammenfassung zeigt jetzt dedizierte Zeilen für
  „Wallbox-Provider erkannt" und „EVCC-Integration erkannt".
- `wallbox_provider` wird in der Zusammenfassung nicht mehr angezeigt (internes Back-Compat-Feld).

### RSCP-Auto-Detect für Quell-Sensoren und System-Parameter
- Wizard und Optionen-Dialog erkennen die [E3DC RSCP](https://github.com/torbennehmer/hacs-e3dc) Integration (Domain `e3dc_rscp`, von Torben Nehmer) und füllen die folgenden Felder automatisch vor:
  - **Quell-Sensoren** (Schritt „Quell-Entities"): SoC, PV-Produktion, Zusatz-PV, Hausverbrauch, Netzleistung, Batterieleistung sowie die Tageszähler.
  - **Systemparameter** (Schritt „Systemparameter"): Installierte PV-Leistung (kWp), WR-Nennleistung (W), Max. Ladeleistung (W), Einspeisegrenze (%) und Brutto-Batteriekapazität (kWh).
- Erkannte Werte werden direkt im Dialog als Liste eingeblendet — auch wenn die Felder bereits manuell ausgefüllt sind. So kann verglichen und bei Bedarf manuell überschrieben werden.
- Bestehende Konfigurationen haben Vorrang — Auto-Detect überschreibt **nichts**.

### Vorzeichen-Invert für Netzleistung (`transfer_to_from_grid`)
- Neue Option **„Vorzeichen Netzleistung invertieren"** im Schritt „Quell-Entities":
  - RSCP-Sensor `sensor.*_transfer_to_from_grid` liefert positive Werte für **Bezug** — Maestro verwendet intern aber positive Werte für **Einspeisung**.
  - Auto-Detect setzt das Flag automatisch auf `true`, wenn der erkannte Netz-Sensor das `_transfer_to_from_grid`-Suffix hat.
  - Bestehende Setups mit `export_to_grid` bleiben unverändert (Flag bleibt `false`).
- **Bugfix:** `Netzbezug heute` (Sensor `netzbezug_heute`) wurde mit dem alten `export_to_grid`-Sensor durchgehend bei 0 kWh stehengelassen, da dieser Sensor nur die Einspeisung meldet. Mit dem neuen Sensor + Invert-Flag werden Bezug und Einspeisung korrekt getrennt erfasst.

### Brutto-/Netto-Hinweis Batteriekapazität
- Die Batteriekapazität wurde aus dem PV-Forecast-Schritt in den Schritt „Systemparameter" verschoben.
- Der Auto-Detect-Wert (RSCP `_installed_battery_capacity`) ist die **Brutto-Kapazität** und wird ausschließlich in der Übersicht angezeigt — **nicht** ins Eingabefeld vorgeschlagen, damit der nutzbare Netto-Wert bewusst eingetragen wird.
- Inline-Hinweis am Feld: _„Nutzbare (Netto-)Kapazität eintragen. Der Auto-Detect-Wert oben ist die Brutto-Kapazität aus der RSCP-Diagnose und sollte NICHT 1:1 übernommen werden."_

## 🐛 Bugfixes / Verbesserungen

- **Netzbezug heute = 0 kWh:** Behoben durch neuen `transfer_to_from_grid`-Sensor + Vorzeichen-Invert-Flag (siehe oben). Alte Setups mit `export_to_grid` blieben unbemerkt ohne Bezugswert.
- **Auto-Detect verfälscht legacy Setups nicht:** Im Optionen-Dialog wird das Invert-Flag nicht überschrieben, wenn bereits ein `grid_power_sensor` konfiguriert ist — sonst hätten alle Bestands-User mit `export_to_grid` fälschlicherweise `invert=true` bekommen.
- **Batteriekapazität sichtbar im richtigen Schritt:** Das Feld lag bisher im PV-Forecast-Schritt und blieb dort selbst bei deaktiviertem Forecast eingetragen — jetzt zentral im Systemparameter-Schritt mit Auto-Detect-Hinweis.
- **Wallbox-Provider aus dem UI entfernt:** Das Feld `wallbox_provider` hatte keinen funktionalen Effekt im UI und wurde entfernt. Der Wert wird intern für Rückwärtskompatibilität weiterhin gepflegt, ist aber nicht mehr im Konfigurations-Wizard sichtbar.
- **Wallbox-Typ wird bei Auto-Erkennung korrekt gesetzt:**
  - E3DC-RSCP-Wallbox gefunden → `wallbox_type = e3dc`
  - openWB gefunden → `wallbox_type = generic`
- **EWMA-Overflow bei langen Ladepausen:** Trennung der Wallbox-EWMA verhindert, dass ein EV-Ladestart nach stundenlangem Stillstand den Haus-EWMA schlagartig verzerrt.
- **`pv_delay` / Korridor-Pause / Spreading-Pause sendeten keine Lade-Sperre an den E3DC** (Live-Befund 10.05.2026): Die drei Phasen lieferten `charge_power_limit=None`, was im Coordinator zu `clear_power_limits` führte – der Wechselrichter fiel auf den Default zurück und lud mit voller PV-Überschussleistung, obwohl die Phase ausdrücklich „Ladung pausieren" entschied. Beobachtbarer Effekt: 8 kW Ladestrom in Phase `pv_delay`. Fix: Alle drei Phasen senden jetzt `max_charge=0` an den E3DC. Die Entladung bleibt explizit frei (`discharge_power_limit=None`, `power_mode=NORMAL`) — das Haus darf bei kurzen PV-Einbrüchen weiter aus dem Akku versorgt werden; nur die Notstromreserve-Phase sperrt die Entladung.
- **`pv_delay` Spreading-Konflikt** (Folge des obigen Bugs): `pv_delay` preempted bei guter PV-Prognose die Spreading-Phase und unterdrückte damit die zeitbasierte gleichmäßige Ladekurve. Fix: Bei aktivem Spreading und SoC < 98 % wird `pv_delay` übersprungen — analog zur bestehenden Korridor-Pause-Exemption. Spreading bleibt damit der dominante Modus für die sanfte Tagesladung.

## �️ Hardware-Schutz: Spreading standardmäßig aktiv

### Hintergrund

Beobachtung im Live-Betrieb (09.05.2026):
Im Auto-Modus oszillierte die Batterieladung zwischen 0 W und ~8.000 W
(Volllast-Bursts), bis der `Spreading`-Switch manuell aktiviert wurde.
Mit Spreading lief die Ladung dann sauber bei ~1–2 kW.

```
11:12   +8.075 W  ████████████████████████████████████████████████████████████████████████████████
11:14   +6.968 W  █████████████████████████████████████████████████████████████████████
11:32     +321 W  ███
11:42   +4.262 W  ██████████████████████████████████████████
11:52   +7.857 W  ██████████████████████████████████████████████████████████████████████████████
                  ↓↓↓ Spreading aktiviert
11:56   +1.010 W  ██████████
12:08   +1.687 W  ████████████████
12:18   +1.220 W  ████████████
12:34   +1.614 W  ████████████████
```

Die Bursts entstanden in der Lücke zwischen Korridor (`SoC < interim_target`)
und Idle (`clear_power_limits`). Wechselrichter-seitig führt das zu unnötigem
Hardware-Stress (Schaltzyklen, Temperaturwechsel).

### `spreading_enabled` ist jetzt Default `True`

Der Schalter `Ladeverteilung aktivieren` wird bei neuen Installationen
standardmäßig aktiviert. Damit wird die Restkapazität zwischen aktuellem
SoC und Spreading-Ziel zeitbasiert (`kWh / Restzeit bis Ladeende`) verteilt
→ glatte, gleichmäßige Ladekurve statt 0/max-Bursts.

### Automatische Migration bestehender Installationen

Config-Entry-Schemaversion: **2 → 3**.
Bestehende Installationen, die `spreading_enabled` nicht explizit auf `True`
gesetzt haben, werden bei einem HA-Restart automatisch migriert.
Eine Info-Meldung im Log dokumentiert die Umstellung:

> *E3DC Maestro v0.3.1: Spreading (Ladeverteilung) automatisch aktiviert –
> schützt die Hardware vor 0/max-Lade-Bursts. Kann im UI deaktiviert werden.*

Wer Spreading bewusst ausgeschaltet lassen möchte (z. B. für aggressive
Tibber-LT-Volllast-Strategien), kann den Switch nach der Migration im UI
wieder deaktivieren.

### Korridor-Glättung als zusätzliche Defense

Auch in der regulären Korridor-Phase wird die Ladeleistung jetzt durch
die Spreading-Rate gedeckelt (sofern `spreading_enabled=True`).
Wirkt vor allem im `advanced_corridor`-Modus, der mit aggressivem
`upper_corridor` Werte um 6–8 kW anfordern kann.

Reason-String enthält dann den Zusatz `Glättung XW`.

### Curtailment Guard hat Vorrang vor Spreading

Bei aktivem Abregelschutz (`curtailment_guard_active=True`) wird Spreading
übersprungen, damit sonst abgeregelte PV-Leistung als Senke in den Akku
darf. Vorher hätte Spreading die Ladung auf ~1–2 kW limitiert, was bei
abgeregelter Anlage Verluste bedeutet hätte.

### Spreading hat Vorrang vor Lower-Corridor-Pause

In Auto-Modus (und damit auch in der **„Prognose SoC nächste 24h"**) konnte
weiterhin ein Treppenmuster auftreten: Lag der SoC knapp über dem
linear ansteigenden Interim-Target, fiel die rechnerische Ladeleistung
unter den `lower_corridor` (Default 500 W) und die Korridor-Pause
schickte die Engine in `IDLE` — Spreading wurde nie erreicht. Die Lücke
zum Interim-Target wuchs, bis die Korridor-Phase mit voller Leistung
feuerte → Treppe. Ab v0.3.1 wird die Lower-Corridor-Pause bei aktivem
Spreading übersprungen, sodass die zeitbasierte Spreading-Rate eine
glatte Ladekurve liefert. `lower_corridor_pause_enabled` greift
weiterhin, wenn Spreading manuell deaktiviert wurde.

### Glattere 24h-SoC-Prognose (Sub-Hour-Interpolation)

Wenn PV- oder Verbrauchs-Forecast nur in Stundenauflösung vorliegt
(typisch bei Solcast Free oder dem Lernhistorien-Fallback für Verbrauch),
wurden die Werte bisher als **Stufenfunktion** in die 15-Minuten-Simulation
übernommen — innerhalb einer Stunde war jeder Quarter-Step identisch,
was am Stundenwechsel zu sichtbaren Mini-Treppen in der SoC-Prognose
führte. Ab v0.3.1 interpoliert `forecast.py` Stunden-Samples linear
(energieerhaltend, Mittel über die 4 Quartale ≈ Stunden-Sample).
Höhere Auflösungen (48/96 Werte) bleiben unverändert, damit Solcast-Peaks
über der Einspeisegrenze nicht weggemittelt werden.

### 24h-SoC-Prognose nutzt jetzt Solcast (statt 90-Tage-Mittel)

Bisher hat der UI-Sensor `Prognose SoC nächste 24h` ausschließlich das
gelernte 90-Tage-PV-Profil verwendet, während der Auto-Optimizer parallel
schon die echte Solcast-/Forecast.Solar-Tagesprognose nutzte. Folge: An
einem 90-kWh-Sonnentag konnte die UI-Trajektorie nachts auf ~25 % SoC
fallen (Mittelwert-Tag → zu wenig PV), obwohl der Optimizer korrekt mit
„Baseline optimal" entschied. Live-Regelung war nie betroffen — nur die
Anzeige. Ab v0.3.1 zieht `_async_update_forecast` dieselbe Solcast-/
Forecast.Solar-Quelle wie der Optimizer (`_read_pv_forecast_profile`)
und greift nur als Fallback auf den 90-Tage-Mittelwert zurück.

### Forecast-Tag-Auswahl: heute vs. morgen

Der UI-Forecast deckt das 24h-Sliding-Window ab `now` ab — der Optimizer
dagegen optimiert speziell für den Folgetag. Dieselbe Solcast-Quelle
mit fixem `days_ahead=1` führte daher dazu, dass der UI-Forecast nachts
(z. B. 00:30 lokal) das Profil von **morgen** lud, obwohl die nächsten
24 h fast vollständig im **heutigen** Kalendertag liegen — bei einem
guten Heute-Tag (125 kWh) und schwächerem Morgen (86 kWh) zeigte die
Trajektorie dann fälschlich ein Akku-Entladen ab Nachmittag. Ab v0.3.1
wählt der Forecast den Solcast-Tag dynamisch:
* **vor 12:00 lokal** → Großteil der nächsten 24 h ist HEUTE → `days_ahead=0`
* **ab 12:00 lokal** → Großteil ist MORGEN → `days_ahead=1`

Zusätzlich kann der Auto-Detect-Scan jetzt auch den Heute-Sensor finden
(z. B. Solcast `prognose_heute`), wenn `CONF_PV_FORECAST_SENSOR` auf den
Morgen-Sensor zeigt — vorher fiel der Forecast in dem Fall stillschweigend
aufs 90-Tage-Mittel zurück.

### Forecast: TZ-korrekte Profil-Lookups (UTC)

`ConsumptionStats.hourly_profile_w` und die Solcast-Buckets aus
`_read_pv_forecast_profile` sind nach **UTC-Stunde** indexiert. Im
Forecast-Loop wurde aber `sim_now.hour` (lokale Zeit) als Lookup-Index
verwendet → in der Sommerzeit lag der Stundenversatz +2 h, sodass der
Forecast schon um 04:30 lokal die PV-Werte von 06:30 lokal sah und
fälschlich Akku-Ladung vor Sonnenaufgang einplante. Ab v0.3.1 konvertiert
`forecast.py` `sim_now` für die Profil-Lookups nach UTC; die Trajektorie-
Beschriftung und die Tarifslot-Zuordnung (`price_q`) bleiben in lokaler
Zeit.

## �🔧 Technisch

- 232 Tests grün — neue/geänderte Tests in `test_wallbox_split.py` (EWMA-Subtraktion, kWh-Akkumulation, `MaestroState.wallbox_power`) sowie in `TestCorridor` (`test_spreading_caps_corridor_power_advanced`, `test_no_smoothing_when_spreading_disabled`) und in `TestLowerCorridorPause` (`test_spreading_overrides_corridor_pause`).
- `control_engine.py`:
  - `MaestroState.wallbox_power` als neues Feld (verwendet in Coordinator, **nicht** in `decide()` — Regellogik bleibt stabil).
  - `MaestroParams.spreading_enabled` Default `False` → `True`.
  - Korridor-Phase bekommt einen Spreading-basierten Cap auf die Ladeleistung (Reason enthält `Glättung XW`).
  - Curtailment Guard übersteuert Spreading, damit abgeregelte PV-Leistung als Senke in den Akku darf.
  - Lower-Corridor-Pause wird bei aktivem Spreading übersprungen (verhindert das Treppenmuster in 24h-SoC-Prognose und im Auto-Modus, wenn der SoC knapp über dem Interim-Target liegt).
- `forecast.py`:
  - `_pv_lookup` interpoliert für 24-elementige Hourly-Arrays linear zwischen den Stunden-Samples (48/96 unverändert).
  - Neuer `_cons_lookup` interpoliert den hourly Verbrauchs-Trace analog → glattere SoC-Trajektorie ohne stündliche Slope-Sprünge.
- `coordinator.py`:
  - `_async_update_forecast` zieht jetzt die Solcast-/Forecast.Solar-Tagesprognose (`_read_pv_forecast_profile(now, days_ahead=…)`) bevor sie auf das 90-Tage-Mittel zurückfällt — `days_ahead` wird dabei dynamisch gewählt (0 vor 12:00 lokal, 1 danach), damit das geladene Profil zum gezeigten 24h-Sliding-Window passt.
  - Auto-Detect-Scan in `_read_pv_forecast_profile` ist jetzt für `days_ahead ∈ {0, 1}` aktiv (vorher nur `=1`), damit der Heute-Sensor (z. B. Solcast `prognose_heute`) auch dann gefunden wird, wenn der konfigurierte Hauptsensor auf den Morgen-Sensor zeigt.
- `forecast.py`:
  - Profile werden in **UTC-Stunde** indexiert; der Forecast-Loop konvertiert `sim_now` für die Profil-Lookups nach UTC, um den Sommerzeit-Versatz zu vermeiden, der vorher zu „PV vor Sonnenaufgang" führte.
- `config_flow.py`:
  - `import re`, `_OPENWB_CP_RE`, `_EVCC_INTG_DOMAIN`, `_autodetect_evcc()`, `_autodetect_openwb_wallbox()` hinzugefügt.
  - Neu: `_RSCP_SUFFIX_MAP`, `_RSCP_SYSTEM_PARAM_MAP`, `_RSCP_SYSTEM_PARAM_LABELS`, `_autodetect_rscp_sources()`, `_autodetect_rscp_system_params()`, `_format_sources_detection()`, `_format_system_detection()`.
  - Beide Flows (Setup + Optionen) geben Auto-Detect-Werte als `description_placeholders.detected_list` an die UI durch.
- `const.py`: neue Konstante `CONF_GRID_POWER_INVERT`.
- `coordinator.py`: invertiert `grid_power` wenn `CONF_GRID_POWER_INVERT=True` gesetzt ist.
- `__init__.py`: Config-Entry-Migration v2 → v3 für die Spreading-Default-Umstellung.
- `config_flow.py`: `VERSION = 3`.
- Alle README-Sektionen (DE + EN) aktualisiert: Schritt 1 (Auto-Erkennung), Schritt 7 (Wallbox-Split, neue Tabellen-Felder, neue Sensoren).
- Dashboard-Hilfe-Karte `/e3dc-maestro/help-wallbox` um Erklärung der Verbrauchstrennung erweitert.

## ⬆️ Upgrade-Hinweis

Nach dem Update empfiehlt sich ein einmaliger Durchlauf des Konfigurations-Wizards
(**Einstellungen → Geräte & Dienste → E3DC Maestro → Konfigurieren**),
damit die Auto-Erkennung für Wallbox-Sensor, EVCC und die RSCP-Quellen/Systemparameter ausgeführt wird und die
neuen Felder mit sinnvollen Werten vorbelegt werden.

**Wichtig für Bestandsuser:**
- Wenn `Netzbezug heute` bisher 0 kWh anzeigte, im Schritt „Quell-Entities" auf den RSCP-Sensor `sensor.*_transfer_to_from_grid` umstellen und die neue Option **„Vorzeichen Netzleistung invertieren"** aktivieren (Auto-Detect schlägt das automatisch vor).
- Beim ersten HA-Start nach dem Update läuft eine einmalige Config-Entry-Migration (v2 → v3), die den Spreading-Switch automatisch aktiviert. Wer das nicht möchte, kann ihn anschließend im UI wieder ausschalten.

Ein HA-Neustart ist **nicht** erforderlich (HA lädt die Integration nach dem Update selbst neu; die Migration läuft dabei automatisch).

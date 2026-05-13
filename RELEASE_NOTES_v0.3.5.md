# v0.3.5 – Schnelllade-Boden & Erweiterter Ladekorridor

Feature-Release: Zwei neue Mechanismen für mehr Kontrolle über das
Ladeverhalten unterhalb des Tagesziel-SoC. Keine Breaking Changes, keine
Migration nötig. Alle neuen Entities werden beim ersten Start automatisch
angelegt.

## ⬆️ Upgrade-Hinweis

Via HACS aktualisieren. HA lädt die Integration automatisch neu. Neue
Entities erscheinen sofort mit ihren Standardwerten (Schnelllade-Boden:
deaktiviert, 40 %; Erweiterter Ladekorridor: deaktiviert). Das Dashboard
wird automatisch um die neuen Karten-Entries erweitert – Dashboard-YAML
in HA neu laden, falls nötig.

---

## ✨ Neues Feature: Schnelllade-Boden (`fast_charge_floor`)

### Problem

Die zeitbasierte Tagesrampe (`target_soc_for_time()`) startet morgens bei
~20 % und steigt linear auf den Ziel-SoC an. Das führt dazu, dass am
Vormittag ein absichtlich niedriger Ziel-SoC berechnet wird – z. B. 47 %
um 10 Uhr bei Ladeende 18 Uhr. Der Ladekorridor bremst die Ladeleistung
entsprechend, obwohl reichlich PV-Überschuss vorhanden ist.

### Lösung

Neue **Regelphase 6.95 `fast_floor`**: Solange der SoC unter dem
konfigurierbaren Boden-SoC liegt, wird `charge_power_limit =
max_charge_power` gesetzt. Der E3DC lädt dann mit dem vollen verfügbaren
PV-Überschuss, ohne künstliche Korridor-Drosselung. Sobald der Boden-SoC
erreicht ist, übernimmt die normale Tagesrampe – die nun vom Boden-SoC
statt von 20 % startet.

### Neue Entities

| Entity | Beschreibung | Standard |
|---|---|---|
| `switch.e3dc_maestro_schnelllade_boden` | Schnelllade-Boden aktivieren | aus |
| `number.e3dc_maestro_schnelllade_boden_soc` | Ziel-SoC für Schnellladung (%) | 40 % |

### Verhalten im Detail

- **Priorität 6.95** – nach Hard-SoC-Limit (6.9), vor normalem
  Ladekorridor (7).
- **Curtailment Guard hat Vorrang**: Ist der Abregelschutz aktiv, wirkt
  `fast_floor` nicht (der Guard setzt ohnehin `max_charge_power`).
- **Tagesrampe angepasst**: `target_soc_for_time()` hebt den
  `morning_anchor` auf den Boden-SoC an, sodass die Rampe nahtlos ab dem
  Floor-SoC startet statt von 20 %.
- **Neue Regelphase `fast_floor`** in der Sensor-Anzeige
  `sensor.e3dc_maestro_regelphase`.

---

## ✨ Neues Feature: Erweiterter Ladekorridor (`advanced_corridor`)

### Problem

Der Standard-Ladekorridor regelt die Ladeleistung auf einen festen Wert
(z. B. 200 W Anlauf bis zur Zielleistung). Es gab keine Möglichkeit, die
Leistung proportional zum aktuellen SoC-Abstand zum Ziel zu variieren.

### Lösung

Neuer Schalter **Erweiterter Ladekorridor**: Aktiviert eine lineare
Interpolation zwischen unterem Ladekorridor (bei SoC = 0 % Delta zum Ziel)
und oberem Ladekorridor (bei SoC = 100 % Delta). Damit lädt der Akku bei
großem Abstand zum Ziel mit voller Leistung und drosselt automatisch beim
Annähern.

### Neue Entities

| Entity | Beschreibung | Standard |
|---|---|---|
| `switch.e3dc_maestro_erweiterter_ladekorridor` | Erweiterter Ladekorridor aktivieren | aus |
| `number.e3dc_maestro_unterer_ladekorridor` | Untere Korridorgrenze (W) | 1500 W |
| `number.e3dc_maestro_oberer_ladekorridor` | Obere Korridorgrenze (W) | 9000 W |

---

## 🗂️ Dashboard-Erweiterungen

Der **Ladekorridor**-Abschnitt im Dashboard wurde um alle neuen Entities
erweitert:

- `switch.e3dc_maestro_erweiterter_ladekorridor`
- `number.e3dc_maestro_unterer_ladekorridor`
- `number.e3dc_maestro_oberer_ladekorridor`
- `switch.e3dc_maestro_schnelllade_boden`
- `number.e3dc_maestro_schnelllade_boden_soc`

---

## 🔧 Technische Details

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `const.py` | `CONF_FAST_CHARGE_FLOOR_ENABLED/SOC`, `PHASE_FAST_FLOOR`, `DEFAULT_*` + in `ALL_PHASES` |
| `control_engine.py` | `MaestroParams`-Felder, `morning_anchor`-Anpassung, Phase 6.95 in `decide()` |
| `switch.py` | Neue Switches für `advanced_corridor` und `fast_charge_floor_enabled` |
| `number.py` | Neue Number-Entity für `fast_charge_floor_soc` |
| `strings.json` / `de.json` | Entity-Namen, Phase-State `fast_floor`, `hard_soc_limit` |
| `dashboards/maestro_dashboard.yaml` | Ladekorridor-Block erweitert |

### Regelphase-Prioritäten (aktuell)

| Prio | Phase | Auslöser |
|---|---|---|
| 1 | `off` | Regelung deaktiviert |
| 2 | `emergency` | SoC < Ladeschwelle |
| 3 | `feed_in_limit` | Netzeinspeisung überschritten |
| 4 | `reserve_protection` | Notstromreserve |
| 5 | `ht_protection` | HT-Schutz |
| 6 | `curtailment_guard` | Abregelschutz |
| 6.9 | `hard_soc_limit` | SoC ≥ Hard-SoC-Limit |
| **6.95** | **`fast_floor`** | **SoC < Schnelllade-Boden** |
| 7 | `corridor` | Normaler Ladekorridor |
| 7d | `corridor` (bypass) | Nach Ladeende-Stunde, SoC < Ziel |
| 8 | `pv_delay` | PV-Prognose-Verzögerung |
| … | … | … |

---

## ⚠️ Bekannte Limitierungen

- Der Schnelllade-Boden wirkt nur bei aktivem PV-Überschuss – die
  Netzladesperre (Tarif-Modus `fixed`) bleibt weiterhin aktiv.
- `advanced_corridor` und `fast_charge_floor` sind unabhängig voneinander
  aktivierbar; bei gleichzeitiger Aktivierung greift unterhalb des
  Floor-SoC immer `fast_floor` (Prio 6.95 > Prio 7).

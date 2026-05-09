# v0.3.0 – Forward-Looking Auto-Optimierung & Solcast-Integration

Großes Feature-Release: Die Auto-Optimierung kann jetzt **48 h vorausschauen**, nutzt **echte PV-Prognosen** statt 90-Tage-Mittel, behält Tarifkosten persistent über Neustarts und erkennt **Sub-Stunden-Einspeise-Peaks** dank höherer Profil-Auflösung.

## ✨ Neue Features

### Forward-Looking Auto-Optimierung mit Solcast/Forecast.Solar
- **48 h-Horizont** wird automatisch aktiviert, sobald ein Day-2-Forecast verfügbar ist – verhindert, dass Tag 1 auf Kosten von Tag 2 leergefahren wird
- **Drei separate PV-Prognose-Sensoren** konfigurierbar: heute / morgen / Tag-2 (z. B. Solcast `prognose_heute`, `prognose_morgen`, `prognose_tag_3`)
- **Auto-Erkennung** scannt alle Sensoren mit `detailedHourly` / `forecast` / `watt_hours` als Fallback
- Optimizer testet jetzt **210 Strategie-Kombinationen** aus `morning_cap_soc × optimization_until_h × gentle_charge_factor` und wählt die kostenoptimale (oder autarkie-/curtailment-optimale, je nach Ziel)
- Neuer Sensor `Auto: Aktive Strategie` mit Detail-Attributen (Score, Curtailment, Feed-In, Autarkie, geschätzte Einsparung)

### Höhere Profil-Auflösung (Sub-Stunden-Peaks)
- PV-Prognosen werden jetzt mit **30-Min- oder 15-Min-Auflösung** verarbeitet, wenn der Sensor sie liefert (`period_start`-basiert)
- **Wichtig für strenge Einspeisegrenzen** (z. B. 70 %-Regel): kurze Mittagspeaks über dem Cap werden nicht mehr durch Stundenmittel weggeglättet → Auto kann jetzt korrekt gegensteuern
- Simulator (`simulate_next_24h`) akzeptiert nun 24-/48-/96-Element-PV-Profile, Auflösung wird automatisch erkannt

### Persistente Kosten-Statistiken
- Kosten und Einspeise-Erlöse bleiben jetzt **über Home-Assistant-Neustarts erhalten** (Storage-basiert)
- `state_class = total_increasing` für korrekte Energy-Dashboard-Integration

## 💡 Empfehlung: Auto reicht meistens aus

In den meisten Setups (genügend PV, moderater Hausverbrauch, fester Tarif) liefert die **Auto-Optimierung allein** bereits das optimale Ladeverhalten. Wenn das Auto-Sensor-Attribut **`Baseline optimal`** mit `sim_self_sufficiency = 100 %` und `sim_curtailed_kwh = 0` zeigt, gibt es nichts zu verbessern – die Standard-Korridor-Logik (zeitgestreckte Ladung bis Sonnenuntergang, Tagesziel `ladeende_soc`) erfüllt das Ziel bereits.

**Folgende Features können in diesem Fall ausgeschaltet bleiben:**
- Vorentladung (Tibber/manuell)
- Ladeverteilung (Spreading)
- Morgens-SoC-Deckel (Morning-Cap)
- Hard-SoC-Limit
- Abregelschutz

**Wann sich diese Features lohnen:**
- **Vorentladung / Spreading**: dynamischer Tarif (Tibber) mit großen Preisunterschieden, oder gezieltes Niedrig-SoC vor günstigen Stunden
- **Morning-Cap**: knappe Akku-Kapazität gegenüber PV-Tagesertrag (Curtailment-Risiko trotz Forward-Looking)
- **Hard-SoC-Limit**: Lebensdauer-Schonung des Akkus
- **Abregelschutz**: Sondersituation bei aktivem Wechselrichter-Abregeln durch Netzbetreiber

Die Auto-Optimierung selbst aktiviert intern bei Bedarf `morning_cap_soc` und `gentle_charge_factor` automatisch – manuelle Settings sind nur nötig, wenn du **abweichendes** Verhalten willst.

## 🐛 Bugfixes

- **Tag-2-Auto-Erkennung deaktiviert** für unkonfigurierte Sensoren – verhinderte stilles Erweitern auf 48 h, wenn Solcast `prognose_tag_3..7` automatisch erzeugt hatte (irreführender 145 kWh-Forecast)
- **Sub-Stunden-Curtailment** wurde durch Hourly-Bucket-Mittelung verschluckt → Auto sah keinen Optimierungsgrund obwohl Peaks > Einspeise-Cap (siehe „Höhere Profil-Auflösung")
- JSON-Quote-Bug in `strings.json` / `translations/de.json` (Anführungszeichen ersetzt durch `:` und `–`)

## 🎨 UI / UX

- Settings-Reihenfolge im Options-Flow überarbeitet: enabled → heute → morgen → Tag-2 → Schwellen → Spreading → Forward-Looking
- Vollständige deutsche Labels für alle drei PV-Sensoren im Options-Flow
- Dashboard-Erweiterungen: Auto-Strategie-Card, SoC-Trajektorie-Chart, Kosten-/Erlös-Anzeigen, Forward-Looking-Switch-Reihe
- Logging zeigt jetzt die genutzte Auflösung (`Auflösung=30 min` / `60 min`)

## 🔧 Technisch

- Lizenzwechsel: **MIT → AGPL-3.0**
- 226 Tests grün (vorher 223) — neue Tests in `TestPvForecastResolution` für 24/48/96-Element-Profile
- README mit deutsch/englischer Sprachumschaltung
- Ausführliches `[decide]`-Debug-Log dokumentiert

## ⚙️ Migration

- Bestehende Configs laufen unverändert weiter (Tag-2-Sensor und Forward-Looking sind opt-in)
- Empfehlung für Nutzer mit strenger Einspeisegrenze (70 %): konfiguriere einen Solcast-Sensor mit 30-Min-Detail (`detailedHourly`) als „PV-Prognose heute", damit Auto Mittagspeaks erkennt

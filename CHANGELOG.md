# Changelog

Alle nennenswerten Änderungen an der GarageButler-Integration für Home Assistant.
Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach
[Semantic Versioning](https://semver.org/lang/de/). Neue Einträge kommen unter
„Unveröffentlicht“; `tool/release.sh` macht daraus beim Release die Versionsüberschrift.

## [Unveröffentlicht]

### Neu

- Favicon (`brand/favicon.png`, 32 × 32) im Stil des App-Favicons mit Haus-Badge.
- Installation und Updates über HACS: öffentlicher GitHub-Mirror
  (`exashox/garage-butler-homeassistant`), Button „Open in HACS“, GitHub-Release bei jedem
  `tool/release.sh`.

### Geändert

- Dokumentation, Fehlermeldungen und Blueprint-Import verweisen auf GitHub statt auf das
  nicht öffentliche Gitea.
- README: nummerierte Buttons „1. Add to HACS“ und „2. Configure after install“,
  Blueprint-Import beim Blueprint.

## [0.1.0] – 2026-11-03

### Neu

- Ein Gerät pro Fahrzeug (Besitzer oder Mechaniker, inaktive Fahrzeuge ausgenommen).
- Sensoren: Kilometerstand, Wartungsstatus (überfällig / bald fällig / ok, gleiche
  Regeln wie die App), nächste Wartung, nächste Hauptuntersuchung, Kilometer bis zur
  nächsten Wartung, offene ToDos.
- Problem-Sensor „Wartung überfällig“.
- ToDo-Liste pro Fahrzeug: anlegen, bearbeiten, abhaken, wieder öffnen, löschen.
- Kalender mit den Fälligkeiten offener Wartungen und Hauptuntersuchungen.
- Dienst `garagebutler.update_mileage` und Blueprint „Kilometerstand vom Auto übernehmen“.
- Einrichtung per Verbindungscode aus der App, Neuanmeldung bei widerrufenem Token.
- Eigenes Logo und Icon (hell und dunkel), ab Home Assistant 2026.3 direkt aus der Integration.
- API-Vertrag (`docs/api.md`) und Entwurf der Supabase-Seite (`supabase/ha_api.sql`).

# Changelog

Alle nennenswerten Änderungen an der GarageButler-Integration für Home Assistant.
Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach
[Semantic Versioning](https://semver.org/lang/de/). Neue Einträge kommen unter
„Unveröffentlicht“; `tool/release.sh` macht daraus beim Release die Versionsüberschrift.

## [Unveröffentlicht]

### Neu

- Favicon (`brand/favicon.png`, 32 × 32) im Stil des App-Favicons mit Haus-Badge.

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

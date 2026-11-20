---
id: ticket-840
title: "The bell and the run thread show run anomalies"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-839]
estimated_days: 1
created: 2026-11-05
---

# ticket-840 — La cloche et le fil du run montrent les anomalies

## Objectif

Une anomalie sort de l'IDE comme une notification de la cloche, réglable comme les autres, et
reste lisible dans le fil du run (ADR-078).

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`, section « Où elle
s'affiche ». Les notifications se calculent dans `lib/notifications.ts`, pure : l'avant et l'après
d'un instantané de supervision. `RunActif.anomalies` (ticket-834) est dans cet instantané. Les
cases par type sont réglées dans la cloche (ticket-554, ticket-779).

## Solution

- `types/api.ts` : `RunActif.anomalies` et le type `Anomalie` de la spec.
- `lib/notifications.ts` : `TYPES_NOTIF` gagne `"anomalie"` ; `notificationsPour` rend **une**
  notification par anomalie apparue entre l'instantané précédent et le courant. Sans instantané
  précédent, aucune : ce qui existe à la connexion est la base.
- `lib/reglagesNotifications.ts` : réglage par défaut pour `anomalie` (cloche et notification
  système actives, son coupé). Un réglage mémorisé avant ce ticket, sans la clé, la reçoit par
  défaut au lieu d'être rejeté.
- `components/Sidebar/ContenuDeLaCloche.tsx` : le libellé du type, dans l'onglet des réglages.
- `components/FilDuRun/` : une ligne par `run_anomaly`, avec le libellé de la règle et le
  `message`, en ambre (ADR-026), sans couleur violette sur le texte.
- Le test de contrat des types (ticket-765) couvre le champ ajouté.

## Critères d'acceptation

- [x] `test_notificationsPour_reports_one_notification_for_a_new_anomaly`
- [x] `test_notificationsPour_is_silent_when_the_anomaly_was_already_in_the_previous_snapshot`
- [x] `test_notificationsPour_without_a_previous_snapshot_reports_no_anomaly`
- [x] `test_notificationsPour_reports_two_notifications_for_two_new_anomalies`
- [x] `test_reglagesParDefaut_includes_anomalie` et
      `test_estReglagesParType_accepts_a_stored_setting_without_anomalie`
- [x] `test_cloche_settings_tab_lists_the_anomalie_type_with_its_switches`
- [x] `test_fil_du_run_renders_a_run_anomaly_line_with_rule_and_message`
- [x] `test_fil_du_run_ignores_a_run_anomaly_without_a_known_rule_label_gracefully` : une règle
      inconnue se rend avec son identifiant brut, sans planter
- [x] `test_run_anomaly_text_uses_amber_never_violet`

## Ce que ça ne fait pas

Ni Bureau ni salle Tessera (tickets 801 et 833). Aucun nouveau panneau : la cloche et le fil
existent.

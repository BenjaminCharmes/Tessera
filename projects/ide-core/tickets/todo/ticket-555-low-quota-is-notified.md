---
id: ticket-555
title: "A session or weekly quota under 10 % is notified"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-550"]
estimated_days: 0.25
created: 2026-10-23
---

# ticket-555 — Un quota bas est notifié

## Objectif
Être prévenu quand le quota de la session ou de la semaine passe sous 10 %,
avant qu'un run ne s'arrête faute de quota.

## Contexte
`QuotaTracker` ne garde qu'un relevé, toutes fenêtres confondues. La
conception du ticket-550 crée le ticket backend qui garde un relevé par
fenêtre (session, semaine). **À ne lancer qu'une fois ce ticket mergé** :
ajouter son id à `depends_on` au triage.

## Solution proposée
`notificationsPour` produit une notification au passage sous 10 % d'une
fenêtre, une fois par fenêtre et par période de reprise, avec l'heure de
reprise.

## Critères d'acceptation
- [ ] Un test montre une notification au passage de 11 % à 9 % restants sur la fenêtre de la semaine, avec l'heure de reprise dans le texte
- [ ] Un test montre qu'un second relevé à 8 % sur la même période ne produit pas de seconde notification
- [ ] Un test montre que la session et la semaine se notifient séparément

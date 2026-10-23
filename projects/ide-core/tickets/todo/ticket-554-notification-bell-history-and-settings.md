---
id: ticket-554
title: "A bell keeps the day's notifications and lets each event be switched on or off"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-552", "ticket-553"]
estimated_days: 1
created: 2026-10-23
plan: true
---

# ticket-554 — La cloche : historique du jour et réglages

## Objectif
Retrouver ce qui s'est passé pendant une absence, et choisir événement par
événement ce qui sort de l'appli et ce qui sonne.

## Contexte
Un toast disparaît, une notification système aussi. Le réglage actuel
(`useNotificationsSysteme`, ticket-193) est un seul interrupteur, mémorisé
par onglet.

## Maquette
`design/maquette/Notifications.dc.html` —
https://claude.ai/artifact/WMqxQRWx8ndc7Jm2RWMPaE (écran « Cloche »).

## Solution proposée
- Une cloche en bas du rail de navigation, avec le nombre de non-lus en
  pastille violette.
- Panneau « Aujourd'hui » : chaque notification produite par
  `notificationsPour`, envoyée au système ou non, de la plus récente à la
  plus ancienne, non-lus en gras ; « Tout marquer comme lu » ; un clic
  ouvre le projet. L'historique se garde pour la journée, en stockage local.
- Panneau « Réglages » : une ligne par type d'événement (question, figé,
  bloqué, terminé, mergé, CI rouge ou merge refusé, quota bas), une case
  « Système » et une case « Son ». Défaut : système partout, son pour la
  question et la CI rouge.

## Critères d'acceptation
- [ ] Le rail affiche une cloche avec le nombre de non-lus, et un test React Testing Library le vérifie
- [ ] Une notification produite pendant que le projet est affiché entre quand même dans l'historique, et un test le vérifie
- [ ] « Tout marquer comme lu » remet le compteur à zéro, et un test le vérifie
- [ ] Une case « Système » décochée empêche l'envoi au système de ce type d'événement, et un test le vérifie
- [ ] L'historique d'un jour précédent est vidé au chargement, et un test le vérifie avec une date simulée

## Ce que ça ne fait pas
- Ne touche pas au backend : l'historique ne vit que dans le navigateur.

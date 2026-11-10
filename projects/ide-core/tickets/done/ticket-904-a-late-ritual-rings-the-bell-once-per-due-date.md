---
agent: codeur
created: 2026-11-10
depends_on:
- ticket-903
estimated_days: 0.5
id: ticket-904
pr_number: null
priority: medium
status: done
title: A late ritual rings the bell once per due date
type: feat
---

# ticket-904 — Un rituel en retard sonne la cloche une fois par échéance

## Objectif

Qu'un rituel qui passe en retard le dise une fois, dans la cloche et en
notification système si Benjamin l'a choisi, sans dépendre de la vue Rituels
ouverte.

## Contexte

Le ticket-903 lit les rituels (`useRituels`) et pose la pastille de l'onglet.
La cloche (ticket-554) a un historique du jour et des réglages par type
(`TYPES_NOTIF` de `lib/notifications.ts`, `LIBELLES_TYPE` de
`lib/reglagesNotifications.ts`). Maquette : `Rituels-Alerte.dc.html` dans
`projects/ide-core/design/maquette/`. La pastille reste la trace durable ; la
notification n'est qu'un signal ponctuel.

## Solution proposée

- Un type `rituel` rejoint `TYPES_NOTIF`, libellé « Rituel en retard »,
  système coché par défaut, sans son.
- Une fonction pure `notificationsRituels(avant, apres)` rend une `Notif` pour
  chaque rituel `en_retard` dont la clé `id + derniere` n'était pas déjà
  notifiée ; les clés notifiées se gardent dans `localStorage` (lecture et
  écriture sous `try`), pour qu'un rechargement ne renotifie pas.
- Titre : le titre du rituel ; corps : « En retard depuis <heure>. Dire à
  Claude : « <phrase> ». » Un clic sur l'entrée ouvre la vue Rituels.

## Critères d'acceptation

- [ ] `frontend/src/lib/notifications.ts` contient `"rituel"` dans `TYPES_NOTIF`
      et `frontend/src/lib/reglagesNotifications.ts` lui donne le libellé
      « Rituel en retard ».
- [ ] Un test vérifie que `notificationsRituels` rend une notification pour un
      rituel `en_retard` nouveau, et aucune pour le même `id` et la même
      `derniere` déjà notifiés.
- [ ] Un test vérifie qu'une nouvelle `derniere` pour le même `id` produit une
      nouvelle notification.
- [ ] Un test vérifie qu'un clic sur une entrée de type `rituel` dans la cloche
      ouvre le panneau `rituels`.

## Ce que ça ne fait pas

- Pas de relance répétée : une notification par échéance, la pastille fait le
  reste.

## Dépendances

ticket-903 (`useRituels`, le panneau `rituels`).

## Estimation

Une demi-journée.

## Risques

Aucun identifié.
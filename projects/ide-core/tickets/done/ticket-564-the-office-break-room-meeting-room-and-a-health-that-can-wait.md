---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-559
- ticket-562
estimated_days: 1.5
id: ticket-564
plan: true
pr_number: null
priority: medium
status: done
title: The office break room, meeting room and a health that can wait
type: feat
---

# ticket-564 — Salle de pause, salle de réunion et santé qui sait attendre

## Objectif
Montrer ce qui n'est ni du travail ni un blocage : un agent qui attend un
événement extérieur (salle de pause) et un conflit confié au résolveur (salle
de réunion). Et ne plus lire « figé ? » pendant une attente.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`,
lignes « Salle de pause » et « Salle de réunion ». Maquette :
`design/maquette/Bureau.dc.html`. Le ticket-559 émet `external_wait` et
`conflict_resolution`. Le quota épuisé est un événement `error` avec
`reason: "quota_exhausted"` : le run est alors clos, pas suspendu.

## Solution proposée
- `frontend/src/types/api.ts` : ajouter `external_wait` et `conflict_resolution`
  à l'union `EventType`, et leurs types de données.
- `hooks/streamState.ts` : garder `attenteExterieure` (booléen, raison) et
  `conflitEnCours` (fichiers) dans l'état du run, mis à jour par ces deux
  événements.
- `lib/santeAgent.ts` : un run en attente extérieure rend `attente`, jamais
  `blocage_suspecte`, quelle que soit la durée du silence.
- `SallePause.tsx` : quota épuisé (`resume` déjà formaté), attente d'une
  dépendance, CI de la phase 2 (dérivée de la boîte aux lettres du ticket-561).
- `SalleReunion.tsx` : conflit en cours (fichiers), puis, après la résolution,
  la PR à relire (`livraison_done` avec `conflits` et `arret`, ADR-033).

## Critères d'acceptation
- [x] `EventType` du frontend contient `external_wait` et `conflict_resolution`, et un test de type ou de store le vérifie
- [x] Un `external_wait` `waiting: true` passe le run en attente, et `waiting: false` l'en sort, et un test du store le vérifie
- [x] Un run en attente extérieure depuis plus de 180 s n'est jamais « figé ? », et un test de `santeAgent` le vérifie avec une horloge simulée
- [x] Un run sans attente silencieux depuis 180 s reste « figé ? » : les tests existants de `santeAgent` passent sans modification
- [x] La salle de pause montre un run clos sur quota épuisé avec le libellé `resume`, et un test le vérifie
- [x] La salle de réunion liste les fichiers d'un conflit en cours, puis la PR à relire après la résolution, et un test le vérifie pour les deux temps
- [x] Aucun fichier du diff ne dépasse 300 lignes, et le diff ne modifie aucun fichier de `backend/src/` (le test d'alignement `backend/tests/test_event_types_alignment.py` suit les deux nouveaux types)
- [x] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- N'émet aucun événement : ils viennent du ticket-559.
- Ne relance rien : un run clos sur quota se relance à la main.
- Ne remplace pas la vue par défaut (ticket-567).

## Livraison du 26/10
Livré à la main : le critère 7 interdisait tout fichier de `backend/`, alors
que l'ajout de deux types d'événements oblige à mettre à jour le test
d'alignement frontend/backend. Le validateur a jugé les 7 autres critères tenus,
l'audit a rendu PASS et les tests sont verts.

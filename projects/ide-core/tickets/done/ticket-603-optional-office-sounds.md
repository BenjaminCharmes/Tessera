---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-598
estimated_days: 0.25
id: ticket-603
pr_number: null
priority: low
status: done
title: 'Optional office sounds: a fanfare on merge, an alarm on red CI, a coffee pour,
  a few keystrokes'
type: feat
---

# ticket-603 — Les sons du bureau, optionnels

## Objectif
Idée 8 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`, bouton
« Son »), validée le 27/10.

## Contexte
Le Bureau a déjà un réglage de son (`InterrupteurSon` dans
`components/BureauView/ColonneAToi.tsx`, ticket-566, « Son coupé » par
défaut) et une alerte sonore. Aucun fichier audio n'est ajouté : les sons
sont synthétisés avec la Web Audio API (quelques oscillateurs courts).

## Ce que dit la maquette
Quand le son est activé, et seulement alors :
- fanfare courte (3 notes montantes, < 1 s) sur un merge (`ci_merge_done`
  `merged: true`, ticket-598) ;
- deux bips graves sur une CI rouge ;
- un « glouglou » bref quand un agent arrive à la machine à café (ticket-596) ;
- trois frappes de clavier très douces quand un agent commence à travailler
  (`agent_started`).
Au plus un son par seconde et par pièce ; aucun son pendant les 2 premières
secondes après l'ouverture de la vue (pas de rafale en rejouant l'historique).

## Critères d'acceptation
- [ ] Son coupé, aucun des quatre événements ne crée d'oscillateur ; un test le vérifie avec un `AudioContext` simulé
- [ ] Son activé, un `ci_merge_done` `merged: true` joue la fanfare (3 notes) ; un test le vérifie
- [ ] Deux événements sonores à moins d'une seconde dans la même pièce n'en jouent qu'un ; un test le vérifie
- [ ] Les événements reçus pendant les 2 premières secondes ne jouent rien ; un test le vérifie
- [ ] Le diff n'ajoute aucun fichier audio et ne modifie aucun fichier de `backend/`
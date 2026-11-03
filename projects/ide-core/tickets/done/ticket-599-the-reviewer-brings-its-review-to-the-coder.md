---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-596
estimated_days: 0.25
id: ticket-599
pr_number: 680
priority: medium
status: done
title: When changes are requested, the reviewer brings its review to the coder's desk
type: feat
---

# ticket-599 — Le reviewer rapporte sa copie au codeur

## Objectif
Idée 2 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`, bouton
« Retour du reviewer »), validée le 27/10 : voir les allers-retours.

## Contexte
Le verdict du reviewer est dans les entrées du `StreamState` (`verdict`,
ADR-009) ; `currentRound` donne le tour. Le validateur peut aussi renvoyer
au codeur (`validation_done`, `approved: false`).

## Ce que dit la maquette
Quand un tour se termine par `CHANGES_REQUESTED` (reviewer) ou par une
validation refusée, et que le codeur repart (`agent_started` du codeur au
tour suivant), l'agent qui a renvoyé le travail se lève, marche jusqu'au
poste du codeur et s'y tient avec une feuille annotée pendant 15 s, puis
retourne à son poste. La pastille dit « tour N — le reviewer rend sa copie »
(ou « le validateur »).

## Critères d'acceptation
- [ ] Après un verdict `CHANGES_REQUESTED` du reviewer puis `agent_started` du codeur au tour 2, le reviewer est rendu debout près du poste du codeur avec `data-objet="feuille"` ; un test le vérifie
- [ ] La pastille de la pièce dit « tour 2 — le reviewer rend sa copie » ; un test le vérifie
- [ ] 15 s plus tard (temps simulé), le reviewer est revenu à son poste ; un test le vérifie
- [ ] Une validation refusée suivie du tour suivant fait le même trajet pour le validateur ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`
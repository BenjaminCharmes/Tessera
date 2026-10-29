---
id: ticket-672
title: "The running apps view shows one room per app, with its state only"
type: feat
status: blocked
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-29
---

# ticket-672 — La vue « En cours » montre une salle par app

## Objectif
Qu'une app lancée ait sa salle dans « En cours », avec ce que Tessera sait déjà
d'elle et rien d'autre.

## Contexte
**Bloqué tant que la maquette n'est pas faite et validée** : elle se fait sur le
compte de Benjamin, avant toute interface (étape 0 de
`docs/superpowers/specs/2026-10-29-salle-des-serveurs-design.md`). Le déblocage
est un geste humain : déplacer ce fichier dans `todo/` et passer `status: todo`.
La maquette fixe le dessin ; ce ticket en reprend les critères.

## Solution proposée
Une salle par entrée de `useAppsEnCours` (`AppEnCours`), avec ses ports, sa
mémoire et son démarrage, et l'état de ses services (`ServiceActif`). Le mobilier
suit ADR-058 : fixe, sans voyant. La vue Liste existante reste dans le sélecteur.

## Critères d'acceptation
- [ ] La vue rend une salle par app de `useAppsEnCours`, et aucune quand la liste est vide, avec un test Testing Library
- [ ] Chaque salle affiche le nom du projet, les ports, la mémoire et l'heure de démarrage de l'app, lus de `AppEnCours`
- [ ] Une app arrêtée ou `en_cours: false` dans `ServiceActif` se distingue d'une app qui tourne
- [ ] Aucun agent n'est dessiné : un test affirme qu'une salle sans fichier d'activité ne contient aucun sprite d'agent
- [ ] Les couleurs d'état n'utilisent que `zinc`, `red`, `amber`, `green`, `blue` (ADR-026), et le test existant qui le verrouille passe

## Ce que ça ne fait pas
- Ne lit aucun fichier d'activité : c'est ticket-673.
- Ne remplace pas la vue Liste.

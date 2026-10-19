---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-471
estimated_days: 1.5
id: ticket-472
priority: medium
status: done
title: A project that declares online resources gets a Put online button with the
  state of each step, built from a validated mockup
type: feat
---

# ticket-472 — Bouton « Mettre en ligne » et état par étape

## Objectif

Lancer la mise en ligne d'un projet depuis l'IDE et voir, étape par étape, ce
qui est fait, ce qui attend, et ce que l'utilisateur doit faire lui-même.

## Contexte

ADR-053, ticket-471. **L'écran passe par une maquette** (règle du dépôt : pas
d'interface sans maquette validée, `docs/architecture.md`, « Design et
maquettes »). Le codeur ne dessine pas l'écran : si
`projects/ide-core/design/maquette/` ne contient pas la maquette « Mettre en
ligne » validée par Benjamin, il s'arrête et le dit dans son rapport.

La maquette doit montrer : le bouton (carte de projet ou en-tête, au choix de
Benjamin), la confirmation, la liste des étapes avec leurs sept états
(`todo`, `done`, `skipped`, `pending`, `manual`, `needs_human`, `failed`), et
le détail à lire pour `manual` et `needs_human` (enregistrements DNS à poser,
ressource à supprimer, clé à créer). Couleurs d'état d'ADR-026.

## Solution proposée

- `ProjectOverview` gagne `online_declared: bool` (comme `services_declares`,
  ticket-410) ; le type de `frontend/src/types/api.ts` suit.
- Un composant d'étapes, des pastilles et boutons partagés (`design/ui/`) ; la
  confirmation nomme le domaine et le **mode Stripe** (`test` ou `live`).
- Le clic appelle `POST …/provision` ; les étapes se mettent à jour par les
  événements `provisioning_step` de la WebSocket d'observation ; l'état initial
  vient de `GET …/provision`.

## Critères d'acceptation

- [ ] La maquette « Mettre en ligne » validée existe :
      `projects/ide-core/design/maquette/MettreEnLigne-Carte.dc.html`
      (posée par la PR #483, avant toute ligne d'interface)
- [ ] Un test vérifie que le bouton n'apparaît que si `online_declared` est vrai
- [ ] Un test vérifie que la confirmation affiche le domaine et le mode Stripe,
      et que rien n'est appelé avant la confirmation
- [ ] Un test vérifie que chaque état d'étape s'affiche avec sa couleur
      d'ADR-026, et que `manual` et `needs_human` montrent leur `detail`
- [ ] Un test vérifie qu'un 409 ou un échec affiche un message court et laisse
      le bouton réactivé, désactivé pendant la mise en ligne
- [ ] Un test vérifie que `ProjectOverview.online_declared` vaut `true` pour un
      projet dont `agents.json` déclare `online`, et `false` sinon

## Ce que ça ne fait pas

Ne produit pas la maquette. N'affiche aucune valeur de jeton ni de secret.

## Dépendances

ticket-471. Maquette validée par Benjamin.
---
agent: codeur
created: 2026-10-13
depends_on:
- ticket-407
estimated_days: 0.5
id: ticket-408
pr_number: 389
priority: high
status: done
title: A Report button in the project header sends a Tessera bug or idea to ide-core
type: feat
---

# ticket-408 — Bouton « Signaler » dans l'en-tête de projet

## Objectif

Pouvoir signaler un défaut ou une idée sur Tessera depuis n'importe quel
projet ouvert dans l'IDE, en deux clics, sans quitter le projet.

## Contexte

Le ticket-407 expose `POST /api/v1/signalements`, qui crée un ticket dans
`ide-core` en gardant trace du projet source. L'IDE n'a encore aucun moyen
de l'appeler. L'en-tête de projet (`components/Sidebar/ProjectHeader.tsx`)
porte déjà les boutons Services, VSCode et Git : c'est là que le signalement
se trouve sans chercher.

## Solution proposée

- `lib/api.ts` : une fonction `signalerATessera(payload)` qui appelle
  `POST /signalements` et renvoie le ticket créé ; type du payload dans
  `types/api.ts` (`nature: "bug" | "idee"`).
- Un nouveau composant `components/Sidebar/SignalementModal.tsx` : choix
  Bug / Idée, champ titre, zone description. Le bouton d'envoi reste
  désactivé tant que titre ou description sont vides. Succès : la modale
  affiche l'id du ticket créé (« Signalé : ticket-NNN ») et se ferme sur
  action. Échec : message d'erreur lisible, formulaire conservé.
- `ProjectHeader.tsx` : un bouton « Signaler », au style des boutons voisins,
  qui ouvre la modale avec le projet courant. Il n'apparaît pas quand le
  projet ouvert est `ide-core`.
- Couleurs : uniquement les familles autorisées par ADR-026 (`zinc` pour la
  structure, `red` pour l'erreur, `green` pour le succès).

## Critères d'acceptation

- [ ] `SignalementModal.tsx` existe, et un test vérifie qu'un envoi appelle
      `signalerATessera` avec `projet`, `nature`, `titre` et `description` saisis
- [ ] Un test vérifie que le bouton d'envoi est désactivé tant que le titre est vide
- [ ] Un test vérifie qu'après un succès la modale affiche l'id du ticket renvoyé
- [ ] Un test vérifie qu'un échec de l'API affiche un message d'erreur et
      conserve le texte saisi
- [ ] Un test de `ProjectHeader` vérifie que le bouton « Signaler » est présent
      pour un projet quelconque et absent pour `ide-core`
- [ ] `lib/api.ts` exporte l'appel vers `/signalements`

## Dépendances

ticket-407 (l'endpoint).

## Estimation

Une demi-journée.

## Risques

- `ProjectHeader.test.tsx` existe déjà : ajouter les cas sans casser les
  existants.

## Ce que ça ne fait pas

- Pas de capture d'écran jointe ni de pré-remplissage depuis un run.
- Pas de liste des signalements envoyés : ils se lisent dans le Kanban
  d'ide-core.
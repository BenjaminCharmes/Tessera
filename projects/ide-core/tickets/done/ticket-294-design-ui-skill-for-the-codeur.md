---
agent: codeur
created: 2026-10-01
depends_on:
- ticket-293
estimated_days: 1
id: ticket-294
pr_number: null
priority: medium
status: done
title: Agents load a UI design skill, declared by default in new projects
type: feat
---

# ticket-294 — Un skill de design d'interface pour le codeur et l'architect

## Objectif

Le codeur et l'architect des projets construits par Tessera disposent d'un
skill `tessera:design-ui`. Il fixe une direction visuelle avant d'écrire de
l'UI, puis empêche de s'en écarter.

## Contexte

La plupart des apps construites depuis l'IDE ont une interface médiocre.
Aucun prompt du produit ne parle de design : sans direction, le modèle produit
l'interface la plus probable (cartes ombrées, dégradé violet, réglages
Tailwind par défaut). Chaque ticket choisit en plus sa propre couleur et sa
propre taille, et l'interface dérive. C'est la dérive qu'ADR-026 a corrigée
dans Tessera, ticket après ticket.

Mettre ces règles dans `codeur.md` les ferait payer à chaque appel, y compris
sur un ticket purement backend. Un skill ne se charge que quand sa
`description` correspond à la tâche (ticket-242). Le ticket-293 permet de le
livrer une seule fois pour tous les projets.

## Solution proposée

`agents/plugin/skills/design-ui/SKILL.md` : `description` en anglais, qui
déclenche sur toute création ou modification d'interface ; corps en français
(ADR-044). Le corps dit, dans cet ordre :

1. **Charte d'abord.** Avant d'écrire de l'UI, chercher la charte du projet :
   tokens dans le code (variables CSS ou `@theme` Tailwind) et justification
   dans `memory/design.md`. Si elle existe, n'en sortir sur aucune valeur. Si
   elle n'existe pas, l'écrire **avant** l'UI :
   - une direction en une phrase, avec une référence nommée et ce qu'on en
     retient ;
   - au plus cinq familles de couleurs, chacune avec un rôle ;
   - une échelle typographique ;
   - une échelle d'espacement et des rayons.
2. **Aucune valeur en dur** hors des tokens : couleur, taille de texte,
   espacement.
3. **Les défauts à éviter, nommés** : dégradé décoratif, cartes ombrées
   partout, emoji en guise d'icônes, tout centré, une couleur différente par
   section.
4. **Hiérarchie** : une seule action principale par vue ; états vide,
   chargement et erreur prévus ; contraste AA.
5. **Densité** : une vue de travail montre des données, pas des marges.

Dans `_default_agents_json` (`services/project_loader.py`), ajouter
`"skills": ["tessera:design-ui"]` aux rôles `codeur` et `architect`, et à
eux seuls.

## Critères d'acceptation

- [ ] `agents/plugin/skills/design-ui/SKILL.md` existe, avec `name: design-ui` et une `description` en anglais qui commence par « Use when »
- [ ] Le corps du skill couvre les cinq points ci-dessus, chacun sous son propre titre
- [ ] Un test vérifie que `_default_agents_json` déclare `tessera:design-ui` pour `codeur` et pour `architect`
- [ ] Un test vérifie que `_default_agents_json` ne déclare aucun skill pour les autres rôles (`reviewer`, `securite`, `validateur`)

## Ce que ça ne fait pas

- **Les projets existants ne sont pas migrés.** Un agent ne peut pas écrire
  `agents.json` (ADR-027). Pour les activer, ajouter à la main
  `"tessera:design-ui"` dans les `skills` du codeur et de l'architect de
  chaque `agents.json`.
- Aucun agent ne voit le rendu : pas de capture d'écran ni de navigateur.
  Le skill pose des règles ; il ne contrôle pas le résultat.
- Ça ne remplace pas une décision de direction prise par l'utilisateur.
  Sur un projet existant, une refonte commence par un ticket `design` qui
  écrit la charte, relue par l'utilisateur avant le premier écran.
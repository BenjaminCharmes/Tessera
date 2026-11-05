---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-851
pr_number: null
priority: high
status: done
title: A module holds the supervisor closed action registry and its guards
type: feat
---

# ticket-851 — Le registre fermé des actions du superviseur, et ses gardes

## Objectif

`backend/src/tessera/services/supervision/superviseur_actions.py` : fonctions pures qui disent
ce que le superviseur peut faire. Aucun appel de modèle, aucune écriture.

## Contexte

ADR-080, spec §2 et §6 (signatures). `services/supervision/` est le domaine de rang 18
(ADR-076) ; créer le dossier avec un `__init__.py` vide s'il n'existe pas encore (le
ticket-828 y déplace d'autres modules).

## Ce qu'il faut faire

- `Action`, `Verdict`, `Decision` et `SCHEMA_DECISION` tels que la spec les donne.
- `lire_decision(brut)` : `ValueError` hors schéma, hors registre, ou `raison` > 300 caractères.
- `est_sensible(texte)` : vrai si le texte nomme une porte (ADR-027, 031, 037, 039, 053, 055,
  067, 073, 080), un des mots `secret`, `jeton`, `budget`, `quota`, `suppress`,
  `professionnel`, `force`, ou le superviseur.
- `chemins_permis(action)` et `refus_de_chemin(modifies, action)` : `trier` → `tickets/**` ;
  `decider` → `memory/lecons.md`, `memory/contraintes.md`, `memory/supervision.md` ;
  jamais `agents.json`, `.github/`, `CLAUDE.md`, `.claude/settings*`, `.git/`,
  `memory/decisions.md`. Les chemins se normalisent avant comparaison (`..`, `\`).
- `deplacement_pur(avant, apres, bloc, vers)` : vrai seulement si `apres` est `avant` dont
  le bloc a quitté `## Proposées` pour la section `vers`, octet pour octet, sans autre ligne
  changée.

## Critères d'acceptation

- [ ] `test_superviseur_actions.py::test_decision_off_schema_is_refused`
- [ ] `test_superviseur_actions.py::test_unknown_action_is_refused`
- [ ] `test_superviseur_actions.py::test_sensitive_text_is_flagged` (une règle par porte et par mot)
- [ ] `test_superviseur_actions.py::test_path_guard_refuses_agents_json_github_claude_md_and_git`
- [ ] `test_superviseur_actions.py::test_path_guard_normalises_dotdot_and_backslashes`
- [ ] `test_superviseur_actions.py::test_pure_move_accepts_a_block_moved_and_nothing_else`
- [ ] `test_superviseur_actions.py::test_pure_move_refuses_an_edited_block_or_extra_line`

## Ce que ça ne fait pas

N'exécute aucune action ; le modèle n'est pas appelé ici.
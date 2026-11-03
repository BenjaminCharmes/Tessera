---
agent: codeur
created: 2026-10-23
depends_on: []
id: ticket-540
pr_number: 608
priority: high
status: done
title: 'Documentation code material: a filtered, bounded diff per ticket, and the
  files it touches'
type: feat
---

## Objectif

Produire ce que les agents de documentation liront en plus des tickets : le
diff livré de chaque ticket et le contenu des fichiers qu'il touche, bornés
(ADR-057, spec `docs/superpowers/specs/2026-10-23-documentation-depuis-le-code-design.md`).
Ce ticket ne change pas `_brief` : c'est 541.

## Critères d'acceptation

- [ ] Un module `services/documentation_code.py` expose une fonction asynchrone qui, pour une liste de tickets, rend par ticket son diff filtré, la liste de ses fichiers, et à part les tickets sans diff retrouvable
- [ ] Le diff exclut `tickets/`, `memory/`, `agents.json`, `README.md` et `docs/`, et réduit les lockfiles à une ligne comme `_resumer_lockfiles`
- [ ] Pour un projet `git_root: ancestor`, le diff se prend depuis la racine du dépôt et les exclusions portent le chemin du projet : un test avec un projet sous `projects/` montre un fichier de `backend/` présent et un `tickets/` du projet absent
- [ ] `diff_du_ticket` accepte une base explicite ; pour le ticket du run, encore sur sa branche, le diff est pris contre cette base et non contre `main`. Les appelants existants (historique) gardent leur comportement, test à l'appui
- [ ] Un diff de plus de 12 000 caractères est tronqué par ticket, le total du lot à 60 000, et chaque troncature nomme les fichiers non montrés
- [ ] Le contenu des fichiers modifiés ou ajoutés (jamais supprimés) est fourni jusqu'à 8 000 caractères chacun et 40 000 au total, par nombre de lignes changées décroissant ; un fichier trop long reste représenté par ses hunks
- [ ] Un ticket dont le diff filtré est vide, ou introuvable, figure dans la liste des tickets sans diff
- [ ] Un test par comportement ci-dessus, sur un dépôt git temporaire

## Ce que ça ne fait pas

- Ne modifie ni `_brief`, ni `_PLAFOND`, ni les prompts, ni `appliquer_editions` (541 et 542).
- Ne lit aucun fichier hors de la racine du dépôt.
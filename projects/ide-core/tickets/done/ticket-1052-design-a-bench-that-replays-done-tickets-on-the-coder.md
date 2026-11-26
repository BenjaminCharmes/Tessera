---
agent: architect
created: 2026-11-26
depends_on: []
estimated_days: 1
id: ticket-1052
pr_number: 1273
priority: medium
status: done
title: Design a bench that replays done tickets on the coder with several models and
  prompts
type: design
---

# ticket-1052 — Concevoir un banc d'essai qui rejoue des tickets faits sur le codeur

## Objectif

Choisir le modèle et le prompt du codeur sur des chiffres mesurés
(approbation au premier tour, coût, durée), et non sur une impression.

## Contexte

Le modèle de chaque rôle se choisit aujourd'hui à l'usage : Sonnet 5.5 en
production, Opus 5.5 pour le reviewer d'ide-core, Haiku 4.5 pour l'audit,
la doc et le validateur. Ollama a été retiré partout le 06/11, après un essai.

Un banc existe déjà, pour le reviewer seulement : `scripts/seconde_revue.py`,
avec `seconde_revue_corpus.py`, `seconde_revue_lecture.py` et
`seconde_revue_decision.py` (tickets 844 à 846, ADR-079 dans
`memory/decisions-archive.md`, spec
`docs/superpowers/specs/2026-11-05-seconde-revue-design.md`). Il fige un
corpus d'avance, rejoue sans toucher au produit, plafonne la dépense, écrit
un JSONL qui se reprend, et applique une règle de décision fixée avant les
résultats. Le codeur, qui coûte le plus et décide le plus de tours, n'a rien
d'équivalent.

Le quota de la semaine du 26/11 le permet. Benjamin a choisi ce chantier
parmi six propositions de l'Orchestrateur.

## Ce que la conception doit trancher

1. **Corpus** : quels tickets faits (projets, nombre, types), à quel commit
   de base (le parent du merge), avec quel texte de ticket (celui de la base,
   pas celui d'après). Écarter les tickets à `preuve_reelle` et ceux qui
   touchent le compte agent.
2. **Ce qu'on rejoue** : le codeur seul, jugé par la suite de tests du projet
   et par le validateur actuel ; ou une boucle codeur puis reviewer complète.
   Dans un worktree jetable hors de `IDE_WORKTREES_DIR`, sans push, sans PR,
   sans `RunLock` pris sur le projet.
3. **Bras** : au moins le couple actuel (modèle et prompt de `agents.json`),
   un autre modèle, et une variante de prompt. Comment une variante de prompt
   se déclare sans toucher `agents/prompts/` du produit.
4. **Mesures** : approbation au premier tour, nombre de tours, coût en
   dollars et en jetons, durée, et tests verts après le rejeu.
5. **Règle de décision fixée d'avance**, comme ADR-079 : quel écart adopte,
   et quel taux de reproduction du bras actuel rend l'essai non concluant.
6. **Plafond de dépense** par essai et reprise après coupure.
7. **Découpage** en tickets de réalisation de six critères au plus chacun,
   le dernier étant l'essai lancé, lu par un humain, et conclu.

## Solution proposée

Partir du banc de la seconde revue et réutiliser ce qui se réutilise
(corpus figé, JSONL, plafond, règle). Rien n'entre dans `backend/src`,
`agents.json` ni le pipeline avant la conclusion, comme pour ADR-079 :
une adoption est une autre ADR.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décide le
      périmètre du banc, ce qu'il rejoue, ses bras, ses mesures, son plafond
      et sa règle de décision.
- [ ] L'ADR dit que le banc ne modifie ni `backend/src`, ni `agents.json`,
      ni `agents/prompts/` avant la conclusion de l'essai.
- [ ] Des fiches de réalisation existent dans `tickets/todo/`, chacune avec
      six critères d'acceptation au plus et ses `depends_on`.
- [ ] La dernière fiche décrit l'essai lancé, son plafond en dollars et le
      rapport qu'un humain lit pour conclure.
- [ ] Une fiche dit comment le corpus fige, pour chaque ticket, le commit de
      base et le texte du ticket à ce commit.

## Ce que ça ne fait pas

- N'écrit aucun code : conception seulement.
- Ne change aucun modèle ni prompt en service.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

Un rejeu complet coûte cher : un corpus trop grand mange le quota avant de
conclure. La règle de décision doit tenir sur une vingtaine de tickets.
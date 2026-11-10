---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-910
pr_number: null
priority: medium
status: todo
title: A weekly report lists what each public project shipped, read from its own files
type: feat
---

# ticket-910 — Un relevé de la semaine dit ce que chaque projet public a livré

## Objectif

Donner à la mise à jour hebdomadaire du portfolio des faits sûrs, tirés des
fichiers des projets, sans LLM : ce qui a été livré, quand, avec quels numéros.

## Contexte

Le portfolio doit suivre les projets (articles, pages projets). Le 04/11, la
relecture des brouillons a trouvé des chiffres plausibles mais inventés : un
agent qui rédige sans source invente. Les faits existent déjà dans chaque
projet : `memory/pipeline-log.md` (tickets approuvés, PR mergées, avec la
date), `tickets/done/`, l'historique git. Il manque une lecture qui les
rassemble pour une période donnée.

Ce qui ne se lit pas dans ces sources (un bug coriace, une surprise, une
mesure) s'écrit, quand ça en vaut la peine, dans `memory/faits-notables.md` du
projet : une ligne `- AAAA-MM-JJ — texte`. Le fichier est facultatif.

## Solution proposée

- Un module `services/projets/releve_semaine.py` et un script
  `scripts/releve_semaine.py` qui l'appelle :
  `python scripts/releve_semaine.py --du 2026-11-03 --au 2026-11-09 [--exclure a,b]`.
- Projets lus : chaque dossier de `projects/` qui porte un `CLAUDE.md`. Sont
  exclus ceux dont `agents.json` déclare `"confidentiality": "professional"`,
  et ceux passés à `--exclure`.
- Pour chaque projet, sur la période (bornes incluses, dates UTC du journal) :
  - les tickets approuvés (`[ticket-XXX] APPROVED`) et leur titre, lu dans
    `tickets/**/ticket-XXX-*.md` ;
  - les PR mergées (`PR #N mergée`) ;
  - le nombre de commits de la période dans le dépôt du projet
    (`git log --since --until`), sur la branche de base déclarée
    (`base_branch`), sinon `HEAD` ;
  - les lignes de `memory/faits-notables.md` datées dans la période.
- Sortie Markdown sur la sortie standard : un titre par projet, rien pour un
  projet sans activité, une ligne finale qui liste les projets exclus.
- Un dépôt git illisible ou un journal absent n'arrête pas le relevé : le
  projet porte la mention « source illisible : … ».

## Critères d'acceptation

- [ ] `backend/src/tessera/services/projets/releve_semaine.py` expose une
      fonction publique qui prend une racine de projets, deux dates et une
      liste d'exclusions, et rend le Markdown.
- [ ] Un test vérifie qu'un projet `"confidentiality": "professional"`
      n'apparaît pas dans le relevé, sauf dans la ligne des exclus.
- [ ] Un test vérifie qu'un projet passé dans les exclusions n'apparaît pas.
- [ ] Un test vérifie que seules les lignes `APPROVED` et `PR #N mergée`
      datées dans la période sont reprises, bornes incluses.
- [ ] Un test vérifie que le titre d'un ticket approuvé est lu dans son
      fichier de ticket.
- [ ] Un test vérifie que les lignes de `memory/faits-notables.md` hors
      période sont ignorées, et qu'un fichier absent ne produit pas d'erreur.
- [ ] Un test vérifie qu'un projet sans dépôt git porte la mention
      « source illisible » sans faire échouer le relevé.
- [ ] `scripts/releve_semaine.py` accepte `--du`, `--au` et `--exclure`, et
      un test l'exécute sur un dossier temporaire.

## Ce que ça ne fait pas

- Aucun appel LLM, aucun appel GitHub : ni releases ni statistiques de
  trafic. L'agent du portfolio les lit lui-même s'il en a besoin.
- N'écrit rien : ni dans les projets, ni dans le portfolio.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le format des lignes du journal peut évoluer : le module lit les deux motifs
par des expressions nommées, testées sur des lignes réelles du journal.

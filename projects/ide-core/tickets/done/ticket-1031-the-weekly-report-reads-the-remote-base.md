---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 1
id: ticket-1031
pr_number: 1228
priority: medium
status: done
title: The weekly report reads the remote base and frontmatter titles
type: fix
---

# ticket-1031 — Le relevé hebdomadaire lit la base distante et les titres du frontmatter

## Signalement

- Projet source : portfolio (relevé du 16 au 20/11)
- Deux défauts de `scripts/releve_semaine.py` (ticket-910), vérifiés le 20/11
  dans `backend/src/tessera/services/projets/releve_semaine.py`.

## Contexte

**1. Le relevé lit le checkout, pas la base.** `_lire_journal` lit
`memory/pipeline-log.md` et `_titre_ticket` parcourt `tickets/` dans le
dossier du projet. Pour un projet à worktree (ADR-056), les runs n'écrivent
jamais dans ce checkout : il reste en arrière. Le 20/11, le checkout de
kadoomi était 56 commits derrière `origin/develop` et le projet manquait en
entier du relevé de la semaine, alors que quinze tickets y étaient livrés.

**2. « titre introuvable ».** `TITRE_TICKET` n'accepte que
`# ticket-N — titre`. Une fiche dont le corps commence autrement (celles
écrites par `signaler` commencent par `## Signalement`) n'a pas de titre lu,
alors que son frontmatter porte `title:`. Une quarantaine de tickets d'ide-core
étaient dans ce cas.

## Solution proposée

Dans `releve_semaine.py` (le découper si le plafond de 300 lignes approche) :

- Quand `agents.json` déclare `base_branch` et que la référence
  `origin/<base_branch>` existe dans le dépôt du projet, le journal se lit par
  `git show origin/<base_branch>:./memory/pipeline-log.md` et les fiches par
  `git ls-tree -r --name-only origin/<base_branch> -- tickets` puis
  `git show origin/<base_branch>:./<chemin>` (lancés avec `-C <projet>` : le
  `./` rend le chemin relatif au projet, y compris pour un projet logé dans
  un dépôt ancêtre). Passer par `build_command`, comme `_compter_commits`.
- Les lignes du journal local s'ajoutent à celles de la base, sans doublon :
  un projet sans worktree y garde des lignes pas encore commitées.
- Sans `base_branch`, sans référence distante ou sur un échec de git, la
  lecture se fait dans les fichiers comme aujourd'hui.
- `_compter_commits` compte sur `origin/<base_branch>` quand la référence
  existe, sinon sur ce qu'il compte aujourd'hui.
- `_titre_ticket` : si `TITRE_TICKET` ne trouve rien, le titre vient du champ
  `title:` du frontmatter YAML de la fiche. « titre introuvable » seulement si
  les deux manquent.
- Aucun `git fetch` : le script reste sans réseau.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_releve_semaine.py` construit, dans
      `tmp_path`, un dépôt « distant » et son clone : une ligne `APPROVED` de
      la période et sa fiche sont poussées sur la base après le clone, le
      clone fait `git fetch` sans avancer son checkout ; le relevé du clone
      contient ce ticket et son titre.
- [ ] Un test : une ligne `APPROVED` présente seulement dans le journal local
      du clone figure aussi au relevé, et une ligne présente des deux côtés
      n'y figure qu'une fois.
- [ ] Un test : un projet sans dépôt git ou sans `base_branch` est lu dans ses
      fichiers, comme avant.
- [ ] Un test : une fiche sans ligne `# ticket-N — titre` mais avec `title:`
      au frontmatter rend ce titre ; sans les deux, « titre introuvable ».
- [ ] Les tests existants de `backend/tests/test_releve_semaine.py` passent
      sans être modifiés.
- [ ] `pytest` et `mypy` passent.

## Ce que ça ne fait pas

- Ne lance aucun `git fetch` et n'appelle pas GitHub : une référence distante
  ancienne donne un relevé ancien.
- Ne change ni le format du relevé ni `releve_menage`.
- Ne lit pas `faits-notables.md` depuis la base (fichier tenu à la main dans
  le checkout).

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Les tests créent de vrais dépôts git dans `tmp_path` : leur donner une
identité inventée (`user.name`, `user.email` d'exemple) par `git -c`, sans
toucher à la configuration de la machine.
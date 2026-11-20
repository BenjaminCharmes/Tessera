---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 2
id: ticket-933
plan: true
pr_number: 1050
priority: high
status: done
title: A run is blocked when an agent call changes a protected file, git hooks or
  git config
type: fix
---

# ticket-933 — Un run passe en `blocked` quand un appel d'agent modifie un fichier protégé, les hooks ou la config git

## Objectif

Qu'une modification d'un fichier protégé faite par une voie que les gardes
lexicales ne lisent pas soit vue après coup, et arrête le run.

## Contexte

Audit du 11/11, rejoué sur `origin/develop`. Les gardes d'écriture
(`backend/src/tessera/services/providers/perimetre.py`,
`backend/src/tessera/services/providers/redirections_bash.py`) ne lisent que
`>`, `>>`, `tee`, `cp`, `mv`, `rm` et `python -c`/`node -e` (ADR-031 : elles
attrapent une erreur, pas une évasion). Passent, par exemple :
`sed -i s/commit/merge/ agents.json`,
`printf '…' | dd of=.git/hooks/pre-commit`,
`install -D x .claude/settings.json`, ou un heredoc donné à `python -`.

Ce que le backend fait déjà, vérifié :

- Les commandes git **en écriture** du backend passent
  `-c core.hooksPath=<dossier vide>`
  (`backend/src/tessera/services/git_workspace/git_runner.py`, l. 87-92 ;
  `backend/src/tessera/services/git_workspace/socle.py`, l. 201-215) : un
  `pre-commit` déposé ne tourne pas au commit de fin de run. Aucune commande
  n'utilise `--no-verify`.
- Les **lectures** (`status`, `diff`, `log`…, liste `_READS`) partent sans
  ces options. Une clé de `.git/config` écrite par `sed -i` —
  `core.fsmonitor`, `diff.external`, un `filter.*` — s'exécute alors sous le
  compte du backend dès le `git status` ou le `git diff` qui suit le run.
- Un hook déposé reste en place pour la session humaine suivante dans le
  checkout.
- Un `agents.json` réécrit ne change pas la racine figée du run (ticket-119),
  mais part dans le diff et vaut pour les runs suivants.

Sous worktree (ADR-056), `.git` est un fichier : la config et les hooks sont
ceux du dépôt commun (`git rev-parse --git-common-dir`), hors de la racine
d'écriture mais à portée d'un `sed -i` sur un chemin absolu.

## Solution proposée

À trancher au tour de plan ; piste :

- Une empreinte (contenu haché, présence/absence) des fichiers protégés
  existants du projet — `agents.json`, `CLAUDE.md`, `CLAUDE.local.md`,
  `.claude/settings*.json`, `.claude/{skills,commands,agents,hooks}/`,
  `.mcp.json`, `.github/workflows/`, le script de `test_command` —, de
  `.git/hooks/` et de `.git/config` du dépôt commun.
- Prise avant et après chaque appel d'agent du pipeline (production, tests,
  revue, validateur…). Une différence → run en `blocked` avec commit, comme
  toute porte (ADR-037), motif nommant les fichiers changés, sans leur
  contenu.
- La relecture git du backend qui suit (`status`, `diff`) ne part qu'après la
  comparaison ; envisager de passer aussi `-c core.fsmonitor=false` aux
  lectures.

## Critères d'acceptation

- [ ] Un test vérifie que l'empreinte change quand `.git/hooks/pre-commit`
      est créé.
- [ ] Un test vérifie que l'empreinte change quand `.git/config` est modifié.
- [ ] Un test vérifie, avec des doubles, qu'un appel d'agent qui modifie
      `agents.json` met le run en `blocked` et que le motif nomme
      `agents.json`.
- [ ] Un test vérifie, avec des doubles, qu'un appel d'agent qui ne modifie
      aucun fichier protégé laisse le run continuer.
- [ ] Un test vérifie que, sous worktree, l'empreinte couvre la config du
      dépôt commun.
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le
      contrôle par empreinte et ce qu'il ne voit pas.

## Ce que ça ne fait pas

- N'empêche pas l'écriture : il la constate après l'appel. Un code exécuté
  pendant l'appel lui-même (sous le compte de l'agent) n'est pas rattrapé.
- Ne couvre pas les fichiers hors du projet et du dépôt (`~/.bashrc`) :
  ticket-931 pour la garde, compte dédié (ticket-915) pour le plafond.

## Dépendances

Aucune. Le ticket-930 ajoute `.mcp.json` et `.claude/hooks/` aux chemins
protégés ; la liste de l'empreinte doit suivre `chemins_proteges.py`, pas en
être une copie.

## Estimation

Deux jours.

## Risques

Coût d'un hachage par appel sur un `.github/workflows/` ou un `.claude/skills/`
volumineux : rester sur des fichiers, pas sur l'arbre entier. Un faux
positif si le pipeline lui-même écrit un de ces fichiers pendant un appel :
le plan doit l'exclure explicitement.
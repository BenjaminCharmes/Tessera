---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-941
pr_number: 1067
priority: high
status: done
title: The git config fingerprint is read by git itself, and every backend git call
  neutralises fsmonitor
type: fix
---

# ticket-941 — L'empreinte de la config git est lue par git, et tout appel git du backend neutralise fsmonitor

## Objectif

Fermer le contournement de l'empreinte de `.git/config` (ADR-084) ouvert par
le ticket-937, avant la release vers main.

## Contexte

Audit sans contexte du 12/11 (F4), vérifié à la main : git accepte un en-tête
et une clé sur la même ligne. Dans un dépôt neuf, la ligne
`[branch "x"] [core]` suivie de `fsmonitor = echo-injecte` donne
`git config --get core.fsmonitor` → `echo-injecte`. Or
`pipeline_empreinte.py` (`sans_sections_de_branche`) retire toute ligne qui
commence par `[branch "` et ce qui la suit jusqu'au prochain en-tête : la
modification échappe à l'empreinte. Même chose avec `[include] path = …`.

De plus, `GitCore._run` (`git_workspace/socle.py`), qui sert au commit de fin
de run et à `bloquer()`, ne pose pas `-c core.fsmonitor=false` : seul
`git_runner.py` le fait (ticket-933). D'autres appels directs
(`create_subprocess_exec("git", …)`) ne le font pas non plus. Un fsmonitor
écrit par un agent s'exécute donc sous le compte du backend, avec son
environnement, même quand l'empreinte l'a détecté.

## Solution proposée

1. L'empreinte se calcule sur la sortie triée de
   `git config --file <config> --list --includes`, en n'excluant que les clés
   `branch.<nom>.(remote|merge|rebase|vscode-merge-base)`. Toute clé
   `include.*` ou `includeIf.*` compte, et le contenu des fichiers inclus
   aussi.
2. Toute commande git lancée par le backend passe par la même construction
   que `git_runner.build_command`, avec au minimum `-c core.fsmonitor=false`.
   Un test parcourt `backend/src` et refuse tout lancement direct de `git`
   hors de ce point unique.

## Critères d'acceptation

- [ ] Un test : ajouter `[branch "x"] [core]` puis `fsmonitor = x` à un
      `.git/config` change l'empreinte.
- [ ] Un test : ajouter `[branch "x"] [include] path = cfg` change
      l'empreinte, et modifier ensuite `cfg` la change encore.
- [ ] Un test : changer `branch.main.remote` ou `branch.main.merge` ne la
      change pas (comportement du ticket-937 conservé).
- [ ] Un test : `GitCore._run` construit une commande qui contient
      `core.fsmonitor=false`.
- [ ] Un test structurel : aucun lancement direct de `git` hors du point
      unique dans `backend/src/tessera`.

## Ce que ça ne fait pas

- Ne ferme pas l'écriture de `.git/` par une évasion lexicale de `Bash` en
  mode « même compte » (ADR-031) : il rend son effet visible et inoffensif.
- Ne neutralise pas les autres clés sensibles au push (`credential.helper`) :
  l'empreinte les couvre, le run passe en `blocked`.
---
id: ticket-932
title: "The git guard reads a command name the way the shell does, empty quotes and backslashes removed"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-11
---

# ticket-932 — La garde git lit le nom de commande comme le shell, guillemets vides et antislashs retirés

## Objectif

Que `g''it push` ou `g\it push` soient lus comme `git push` par la garde, comme
le shell les exécute.

## Contexte

Audit du 11/11, vérifié sur `origin/develop` :
`jetons` (`backend/src/tessera/services/providers/git_guard_lexique.py`,
l. 85-97) découpe en `shlex.split(…, posix=False)` pour garder les antislashs
d'un chemin Windows, et `_sans_guillemets` ne retire que des guillemets qui
entourent **tout** le jeton. `nom_de_commande` (l. 106-109) coupe ensuite sur
`\` et `/`. Résultat :

- `g''it push` → nom `g''it` : passe. Bash exécute `git push`.
- `g''h pr merge 1` → nom `g''h` : passe.
- `g\it push` → coupé sur l'antislash, nom `it` : passe. Bash exécute
  `git push` (vérifié : `g\it --version` répond).
- `'g'it push`, `g"i"t push` : même famille.

Constat écarté : `git\ push` passe la garde, mais bash cherche alors une
commande nommée `git push` et échoue (« command not found ») ; ce n'est pas
une évasion.

`nom_de_commande` sert aussi à `kill_guard.py` : la correction ferme la même
classe pour lui.

ADR-031 : `x=git; $x push` et `python -c "subprocess.run(['git','push'])"`
passent toujours ; la garde attrape une erreur, pas une évasion.

## Solution proposée

- Pour juger un nom de commande, en calculer deux lectures : la lecture
  actuelle (chemin Windows coupé sur `\` et `/`) et une lecture POSIX du
  jeton brut (guillemets concaténés retirés, antislash d'échappement retiré,
  puis coupé sur `/`). Le segment est interdit si **l'une ou l'autre** désigne
  une commande interdite.
- Appliquer la même double lecture aux enveloppes et aux shells
  (`sans_enveloppe`, `ligne_derriere_c`), qui passent par `nom_de_commande`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_git_guard.py` vérifie que `g''it push`
      est refusé.
- [ ] Un test vérifie que `g\it push` est refusé.
- [ ] Un test vérifie que `g''h pr merge 1` est refusé.
- [ ] Un test vérifie que `C:\Git\bin\git.exe status` reste admis comme
      lecture.
- [ ] Un test vérifie que `e''nv git push` est refusé (enveloppe lue de la
      même façon).

## Ce que ça ne fait pas

- Ne suit ni les variables (`$x push`) ni les interpréteurs : ADR-031.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Une double lecture peut refuser un jeton Windows exotique qui, lu en POSIX,
devient `git` : c'est le sens voulu, un faux refus plutôt qu'un passage.

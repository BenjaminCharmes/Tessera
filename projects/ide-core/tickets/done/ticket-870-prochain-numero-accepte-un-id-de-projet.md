---
agent: codeur
created: 2026-11-06
depends_on:
- ticket-869
estimated_days: 0.5
id: ticket-870
pr_number: 964
priority: medium
status: done
title: prochain_numero.py accepts a project id and refuses a missing folder
type: fix
---

# ticket-870 — `prochain_numero.py --projet` accepte un id de projet

## Objectif

`python scripts/prochain_numero.py ticket --projet ide-core` doit rendre le
prochain numéro d'ide-core au lieu de planter, et un dossier introuvable doit
donner un message clair, jamais une trace.

## Contexte

Dans `scripts/prochain_numero.py`, `--projet` est un `Path` relatif au dossier
courant. Lancé depuis la racine du dépôt avec `--projet ide-core`, il désigne
`./ide-core`, qui n'existe pas : le premier `git` lancé avec ce `cwd` lève
`NotADirectoryError: [WinError 267]` (reproduit le 06/11).

Un second défaut va avec : sans `--projet`, depuis un dossier qui n'est pas un
projet (par exemple `backend/` via `uv run --directory backend`), le script
répond `1` sans rien signaler, un numéro faux qu'on risque d'utiliser.

## Solution proposée

Une fonction publique `resoudre_projet(valeur: Path) -> Path | None` dans le
script : un dossier existant est gardé tel quel ; sinon, une valeur sans
séparateur est traitée comme un id et passée à `dossier_du_projet` du
ticket-869 (`tessera.services.projets.ticket_check`). `main()` sort avec le
code 2 et un message sur `stderr` qui cite la valeur reçue quand rien ne
résout, ou quand le dossier retenu n'a ni `tickets/` (genre `ticket`) ni
`memory/` (genre `adr`).

## Critères d'acceptation

- [ ] `scripts/prochain_numero.py` définit `resoudre_projet(valeur)`.
- [ ] Un test de `backend/tests/test_prochain_numero.py` vérifie qu'un dossier
      existant passé à `resoudre_projet` est rendu tel quel.
- [ ] Un test vérifie, en simulant `dossier_du_projet`, qu'un id comme
      `ide-core` est résolu par lui.
- [ ] Un test vérifie que `main(["ticket", "--projet", "absent", "--sans-reserver"])`
      renvoie 2 et écrit `absent` sur `stderr`, sans lever d'exception.
- [ ] Un test vérifie que `main(["ticket", "--projet", <dossier sans tickets/>, "--sans-reserver"])`
      renvoie 2.

## Dépendances

ticket-869 (`dossier_du_projet`).

## Estimation

Une demi-journée au plus.

## Risques

Le skill `new-ticket` et des briefs lancent le script depuis le dossier du
projet sans `--projet` : ce cas, qui a un `tickets/`, doit continuer de
marcher (les tests existants de `test_prochain_numero.py` le couvrent).

## Ce que ça ne fait pas

Ne change ni la réservation (ticket-848) ni le calcul des numéros pris.
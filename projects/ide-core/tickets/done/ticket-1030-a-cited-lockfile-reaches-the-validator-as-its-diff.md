---
agent: codeur
depends_on: []
id: ticket-1030
priority: medium
status: done
title: A lockfile cited by a criterion reaches the validator as its diff
type: fix
---

# ticket-1030 — Un verrou cité par un critère arrive au validateur par son diff

## Signalement

- Projet source : repo-health (ticket-077, tour 1, 20/11)
- Nature : idée

## Contexte

Un critère qui cite `frontend/package-lock.json` entre backticks fait joindre
le fichier au validateur (`build_cited_files_section`,
`services/verdicts/validator_cited_files.py`). Un verrou pèse des centaines de
milliers de caractères ; la section est bornée par `CITED_FILES_MAX_CHARS`
(20 000) : le validateur n'en reçoit que le début, n'y lit pas les versions
que le critère nomme, et refuse. Le ticket source n'a été approuvé qu'après
réécriture de ses critères sans backticks.

## À faire

- Dans `validator_cited_files.py`, un fichier cité dont le nom est un verrou
  connu (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `uv.lock`,
  `poetry.lock`, `Cargo.lock`) n'est plus joint par son contenu : à sa place,
  les lignes du diff du run qui le concernent, bornées par le même budget.
- Sans diff pour ce verrou, une ligne le dit (« verrou cité, non modifié par
  le run ») : le fichier entier n'est jamais joint.
- La ligne de journal (`format_cited_files_log`) marque ces entrées
  « (diff) ».
- Le skill `new-ticket` gagne une phrase : un critère sur une version de
  dépendance cite le manifeste, pas le verrou.

## Critères d'acceptation

- [ ] Un test : un critère citant `package-lock.json`, un diff qui le modifie
      → la section porte les lignes du diff de ce fichier, pas son début.
- [ ] Un test : le même critère sans diff du verrou → la section porte la
      ligne « non modifié par le run », et aucun contenu du fichier.
- [ ] Un test : un fichier cité qui n'est pas un verrou est joint comme
      avant.
- [ ] Un test : la ligne de journal marque le verrou « (diff) ».
- [ ] `pytest` et `mypy` passent.

## Ce que ça ne fait pas

- Ne relève pas `CITED_FILES_MAX_CHARS`.
- Ne change rien pour les fichiers qui ne sont pas des verrous.
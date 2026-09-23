---
id: ticket-144
title: "Un service mort de lui-même doit rester visible"
type: fix
status: done
pr_number: 163
priority: high
agent: codeur
depends_on: ["ticket-138"]
estimated_days: 1
created: 2026-09-23
---

# ticket-144 — Un service mort doit rester visible

## Objectif

Qu'un service qui s'arrête tout seul se voie, au lieu de disparaître.

## Contexte

**Trouvé au premier essai réel.** `ide-core` déclare deux services ; son
`backend` veut le port 8000, déjà pris par celui qui fait tourner l'IDE. Il
meurt donc aussitôt — et dix secondes plus tard, `GET /services` ne renvoie
plus que le `frontend` :

```
frontend  pid=35196  en_cours=True  code=None
```

Le `backend` n'est ni en rouge, ni marqué en échec : il a **disparu**. Vu de
l'IDE, le lancement paraît avoir à moitié réussi, sans rien dire de l'autre
moitié.

`ProcessRegistry.services_de` filtre sur `if s.en_cours`, et `instantane`
fait de même.

## Ce que l'épisode apprend

Les tests des deux côtés passaient. Ceux de ticket-138 vérifient qu'un
service `en_cours: false` avec un `code_de_sortie` non nul s'affiche en rouge
— mais ils **fournissaient** cet objet à la main. Le backend ne le renvoie
jamais. Chaque moitié respectait un contrat que l'autre ne tenait pas, et
seul un lancement réel pouvait le montrer.

## Solution proposée

`services_de` et `instantane` renvoient les services **enregistrés**, vivants
ou non. `en_cours` et `code_de_sortie` disent lequel est lequel — c'est déjà
ce que l'affichage attend.

Reste à borner l'accumulation :

- un nouveau `start` purge les entrées terminées portant le même nom avant
  d'ajouter la nouvelle ;
- `stop` vide tout, comme aujourd'hui.

Ainsi la liste ne contient jamais plus d'une entrée par service déclaré.

## Critères d'acceptation

- [ ] Un test vérifie qu'un service qui s'arrête seul reste dans
      `GET /services`, avec `en_cours: false` et son code de sortie
- [ ] Un test vérifie qu'un `start` après un échec ne laisse **qu'une** entrée
      pour ce service
- [ ] Un test vérifie que `stop` vide toujours la liste
- [ ] Un test vérifie qu'un service tué par `stop` n'apparaît pas en échec —
      il a été arrêté, il n'a pas échoué
- [ ] `uv run pytest` et `uv run mypy src/` passent
- [ ] Vérifié en lançant réellement `ide-core` : le `backend` apparaît en
      échec, le `frontend` en cours

## Dépendances

ticket-138.

## Estimation

1 jour.

## Risques

La distinction « arrêté » / « mort tout seul » repose sur le code de sortie,
et `terminate()` en produit un non nul sur certaines plateformes. Le test sur
`stop` est ce qui empêche d'afficher un échec là où il n'y en a pas.

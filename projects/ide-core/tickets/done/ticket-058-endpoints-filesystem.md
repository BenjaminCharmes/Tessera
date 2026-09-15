---
id: ticket-058
title: "L'éditeur Monaco n'a jamais fonctionné en mode web : endpoints fs manquants"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-058 — Endpoints filesystem manquants

## Objectif

Rendre l'éditeur de fichiers utilisable en mode web, et le faire sans ouvrir
une faille de traversée de répertoire.

## Contexte

Signalé à l'usage : ouvrir un ticket dans l'éditeur affiche

```
Impossible de lire le fichier : Failed to read
C:\...\projects\fluentdb\tickets\todo\ticket-001-....md: Not Found
```

Le fichier existe. `frontend/src/lib/fs.ts` fonctionne en deux modes : `invoke`
Tauri en desktop, et un repli REST sur `/api/v1/fs/read` en web. **Ce repli
appelle des routes qui n'existent pas** — le backend n'expose aucun endpoint
`/fs`.

Conséquence : l'éditeur Monaco, annoncé depuis ticket-011 (« Monaco branché sur
le filesystem réel ») et présenté comme fonctionnel dans le README, **n'a
jamais marché hors mode desktop**. Le mode web est pourtant celui que la
documentation recommande en premier.

C'est exactement la classe de défaut visée par ticket-053 : le service et le
composant existaient chacun de leur côté, l'assemblage n'était testé nulle part.

## Le point de sécurité

Un endpoint qui lit un chemin arbitraire fourni par le client est une **faille
de traversée de répertoire** : `?path=C:/Users/moi/.ssh/id_rsa` lirait la clef.
L'écriture est pire encore.

Tout chemin doit donc être **résolu puis vérifié comme appartenant au
workspace**, après résolution des liens symboliques — sinon un lien posé dans
le workspace contourne le contrôle.

Nuance : les projets importés en mode `symlink` pointent **hors** du workspace
par construction. La racine autorisée d'un projet est donc la cible résolue de
son propre dossier, pas le workspace brut.

## Solution proposée

1. Un routeur `fs` avec `read`, `write` et `list`, tous confinés.
2. Un helper de résolution partagé, testé pour lui-même : il porte la sécurité
   de l'ensemble.
3. Refus explicites : 403 hors périmètre, 404 absent, 413 au-delà d'une taille
   raisonnable.
4. Un test end-to-end qui ouvre réellement un ticket via l'API — la
   non-régression qui manquait.

## Critères d'acceptation

- [x] `GET /api/v1/fs/read` renvoie le contenu d'un fichier du workspace
- [x] `PUT /api/v1/fs/write` écrit un fichier du workspace
- [x] `GET /api/v1/fs/list` liste un dossier du workspace
- [x] Un chemin hors workspace est refusé en **403**, en lecture comme en écriture
- [x] Une traversée par `..` est refusée
- [x] Une traversée via un lien symbolique posé dans le workspace est refusée
- [x] Un projet importé en mode `symlink` reste lisible
- [x] Un fichier trop volumineux est refusé en 413 plutôt que de saturer la mémoire
- [x] Ouvrir un ticket depuis l'UI fonctionne en mode web
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Élevé si mal fait** — c'est un endpoint de lecture/écriture de fichiers
  piloté par le client. Le confinement est la fonctionnalité, pas un détail.

## Livré

`routers/fs.py` — `read`, `write`, `list`, tous passant par le même helper de
résolution `_resolve_inside_workspace`.

### Le confinement, en détail

La résolution se fait **avant** le contrôle et **suit les liens symboliques**.
Contrôler la chaîne brute laisserait passer deux contournements : les segments
`..`, et un lien déposé dans le workspace qui pointe dehors. Les deux ont leur
test.

Nuance : un projet importé en mode `symlink` pointe hors du workspace **par
construction**. `_workspace_roots()` ajoute donc la cible résolue de chaque
projet lié, sinon l'éditeur refuserait d'ouvrir les fichiers d'un projet
pourtant importé volontairement.

### Vérifié en réel

| Requête | Résultat |
|---|---|
| Le ticket signalé (`fluentdb/tickets/todo/ticket-001-...`) | **200**, contenu servi |
| `~/.ssh/id_rsa` | **403** |
| `.env` du dépôt lui-même | **403** |

## Ce que ce défaut dit

L'éditeur Monaco était annoncé fonctionnel depuis ticket-011 et décrit comme
tel dans le README. Il ne l'était que sous Tauri — alors que le mode web est
celui que la documentation recommande en premier.

Le service et le composant existaient chacun de leur côté ; **l'assemblage
n'était testé nulle part**. C'est exactement ce que ticket-053 avait identifié
comme angle mort, et cette panne-ci était hors de son périmètre puisqu'aucun
routeur `fs` n'existait à couvrir.

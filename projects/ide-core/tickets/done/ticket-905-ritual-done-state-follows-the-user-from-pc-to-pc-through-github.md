---
agent: codeur
created: 2026-11-10
depends_on:
- ticket-902
estimated_days: 1
id: ticket-905
pr_number: 1016
priority: medium
status: done
title: Ritual done state follows the user from PC to PC through GitHub
type: feat
---

# ticket-905 — L'état « fait » d'un rituel suit Benjamin d'un PC à l'autre, par GitHub

## Objectif

Qu'un rituel marqué « Fait » ou reporté sur un PC le soit aussi sur les autres
où tourne Tessera, sans dépendre d'un compte Anthropic ni d'un serveur à soi.

## Contexte

Le ticket-902 garde l'état des rituels (`fait_le`, `reporte_jusqua`) dans la
table SQLite `rituels_etat`, locale à chaque PC : un rituel fait sur un poste
réapparaît en retard sur un autre. Benjamin change de PC et de compte
Anthropic, mais garde son compte GitHub, et Tessera a déjà un jeton qui écrit
dans son propre dépôt (`settings.github_token`, `settings.github_repo`), lu par
`GitHubService` (`services/github/github_service.py`).

## Solution proposée

- **Où** : un fichier `rituels-etat.json` sur une branche dédiée
  `etat-rituels` du dépôt de Tessera, lu et écrit par l'API Contents de GitHub
  (`GET`/`PUT /repos/{repo}/contents/rituels-etat.json?ref=etat-rituels`), sans
  toucher au checkout ni à aucun worktree. La CI ne part que sur les PR : un
  commit sur cette branche ne déclenche rien.
- **Quoi** : `{"version": 1, "rituels": {"<id>": {"fait_le": "<ISO>|null",
  "reporte_jusqua": "<ISO>|null"}}}`, validé par un modèle Pydantic ; rien
  d'autre n'y est écrit (ni titre, ni phrase, ni détail).
- **Fusion** : l'état n'avance que dans un sens. Pour chaque `id`, garder le
  plus récent des deux `fait_le` et le plus récent des deux `reporte_jusqua`.
  Un `fait_le` postérieur au report l'emporte comme dans le ticket-902.
- **Quand** : un module `services/github/rituels_sync.py` tire l'état distant à
  chaque `GET /api/v1/rituels` (au plus une fois par minute, mémorisé), le
  fusionne dans `rituels_etat`, et pousse l'état fusionné après chaque
  `fait` / `reporter`. Un `PUT` refusé pour conflit (409 ou 422 sur un `sha`
  périmé) relit, refusionne et réessaie une fois.
- **Création** : la branche et le fichier se créent au premier `fait` ou
  `reporter` (une action de Benjamin, ADR-073), depuis la tête de la branche
  par défaut, par `POST /repos/{repo}/git/refs`.
- **Hors ligne** : sans jeton, sans réseau ou sur une erreur GitHub, l'état
  local fait foi, la réponse porte `"synchro": "locale"` au lieu de
  `"github"`, et rien n'échoue. Le jeton n'apparaît dans aucun log.

## Critères d'acceptation

- [ ] Un test de la fusion vérifie que, pour un même `id`, le `fait_le` le plus
      récent des deux côtés est gardé, et qu'un `id` présent d'un seul côté est
      conservé.
- [ ] Un test, avec un double de `GitHubService`, vérifie qu'un `POST
      /api/v1/rituels/{id}/fait` pousse un `rituels-etat.json` qui contient ce
      `fait_le`, et rien d'autre que `version` et `rituels`.
- [ ] Un test vérifie qu'un `PUT` refusé pour `sha` périmé relit le distant,
      refusionne et réessaie une fois.
- [ ] Un test vérifie que, sans jeton GitHub ou sur une erreur réseau,
      `GET /api/v1/rituels` répond 200 avec `"synchro": "locale"`.
- [ ] Un test vérifie que la branche `etat-rituels` n'est créée que par
      `fait` ou `reporter`, jamais par un `GET`.
- [ ] Le diff ne modifie pas `rituels.md`.

## Ce que ça ne fait pas

- Pas de synchronisation de la liste : elle suit déjà le dépôt.
- Pas d'historique consultable des rituels faits : l'historique git de la
  branche le garde, sans écran.
- Pas de temps réel : un autre PC voit le changement à sa lecture suivante.

## Dépendances

ticket-902 (la table `rituels_etat` et les routes).

## Estimation

1 jour.

## Risques

- Un jeton sans droit `contents: write` sur le dépôt de Tessera : synchro
  `locale`, signalée par le champ de la réponse.
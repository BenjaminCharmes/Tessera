---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 0.5
id: ticket-908
pr_number: 1021
priority: medium
status: done
title: Ritual sync finds its repository without a setting, and the view says when
  it stays local
type: feat
---

# ticket-908 — La synchro des rituels trouve son dépôt sans réglage, et la vue dit quand elle reste locale

## Objectif

Que l'état « Fait » des rituels se synchronise sur tout PC où Tessera tourne
avec un `GITHUB_TOKEN`, sans réglage de plus, et qu'une synchro coupée se voie.

## Contexte

Le ticket-905 synchronise l'état par `services/github/rituels_sync.py`, mais
`creer_service()` exige `settings.github_repo` (`GITHUB_REPO`), vide par défaut
et documenté comme optionnel dans `.env.example`. Sans lui, la réponse dit
`"synchro": "locale"` sans rien journaliser, et la vue ne l'affiche pas :
le 10/11, la synchro est restée locale sans que personne le voie. Benjamin
change de PC : un réglage à reposer sur chacun, c'est la panne qui revient.

Or `rituels.md` vit dans le dépôt de Tessera (`_REPO_ROOT` de `config.py`) :
le dépôt où garder son état est l'`origin` de ce même dépôt.

## Solution proposée

- Dans `rituels_sync.py`, le dépôt vient de `settings.github_repo` s'il est
  renseigné ; sinon de `git remote get-url origin` lancé à `_REPO_ROOT`, lu une
  fois puis gardé en mémoire. Une fonction pure `depot_de_l_url(url) -> str | None`
  rend `owner/repo` pour une URL GitHub HTTPS (`https://github.com/o/r(.git)?`)
  ou SSH (`git@github.com:o/r(.git)?`), `None` pour toute autre forge ou forme.
  Respecter l'ordre des domaines de `services/` (ADR-076).
- Sans jeton ou sans dépôt trouvé : `locale`, comme aujourd'hui, mais avec un
  avertissement journalisé une seule fois (`rituels_synchro_inactive`, avec la
  raison : `sans_jeton` ou `sans_depot`), jamais le jeton.
- Frontend : `ListeRituels` (`lib/apiRituels.ts`) gagne
  `synchro: "github" | "locale"`. La vue Rituels affiche sous son titre, quand
  `synchro` vaut `locale`, une ligne en `zinc` : « État gardé sur ce PC
  seulement : la synchronisation GitHub n'est pas active. » Rien quand elle
  vaut `github`.

## Critères d'acceptation

- [ ] Un test vérifie que `depot_de_l_url` rend `BenjaminCharmes/Tessera` pour
      `https://github.com/BenjaminCharmes/Tessera.git` et pour
      `git@github.com:BenjaminCharmes/Tessera.git`, et `None` pour une URL
      `https://gitlab.com/o/r.git`.
- [ ] Un test vérifie, avec `settings.github_repo` vide, un jeton renseigné et
      une lecture de l'`origin` remplacée par un double, que `creer_service()`
      rend un client pour le dépôt lu dans l'`origin`.
- [ ] Un test vérifie que `settings.github_repo`, quand il est renseigné,
      l'emporte sur l'`origin`.
- [ ] `frontend/src/lib/apiRituels.ts` déclare `synchro` dans `ListeRituels`,
      et un test de `RituelsView` vérifie que la ligne « sur ce PC seulement »
      est affichée pour `locale` et absente pour `github`.
- [ ] Le diff ne modifie ni `rituels.md` ni `backend/src/tessera/config.py`.

## Ce que ça ne fait pas

- Pas de dépôt choisi depuis l'interface : l'`origin` du dépôt suffit.
- Pas d'autre forge que GitHub : ailleurs, la synchro reste locale et le dit.

## Dépendances

Aucune : 902 à 905 sont mergés.

## Estimation

Une demi-journée.

## Risques

- `git` absent du PATH ou dépôt sans `origin` : la lecture échoue fermée en
  `locale`, avec la raison `sans_depot`, sans lever.
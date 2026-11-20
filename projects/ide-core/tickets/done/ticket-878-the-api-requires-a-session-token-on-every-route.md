---
agent: codeur
created: 2026-11-06
depends_on:
- ticket-877
estimated_days: 1
id: ticket-878
plan: true
pr_number: 978
priority: critical
status: done
title: The API requires a per-boot session token on every route, and the open mode
  disappears
type: feat
---

# ticket-878 — L'API exige un jeton de session sur toute route

## Objectif

Aucune requête HTTP ni WebSocket n'atteint un routeur sans le jeton effectif,
y compris quand `STATIC_TOKEN` est vide : un agent qui lance
`curl -X PATCH …/pipeline` reçoit un 401.

## Contexte

Audit externe du 06/11, vérifié. `STATIC_TOKEN` vide (le défaut) :
`StaticTokenMiddleware` (`backend/src/tessera/auth.py`) laisse tout passer, et
`_is_trusted_origin_and_host` admet toute requête sans `Origin`. Depuis `Bash`,
un agent peut donc baisser les portes d'un projet (`PATCH
/api/v1/projects/<id>/pipeline` : `securite_enabled`, `validateur_enabled`,
`autonomy`, `merge_without_ci`, `test_command`), écrire un rôle, supprimer un
projet, écrire dans le workspace par `/fs/write`, lancer un run. L'`Origin`
exigé sur `/api/v1/reglages` se forge. Les gardes lexicaux n'attrapent pas une
requête HTTP.

## Solution proposée

- Nouveau module `backend/src/tessera/services/noyau/jeton_de_session.py` :
  `demarrer()` dans le `lifespan` de `main.py` fixe le jeton effectif,
  `settings.static_token` s'il est renseigné, sinon
  `secrets.token_urlsafe(32)` gardé en mémoire ; `courant()` le rend. Un jeton
  généré s'écrit dans `ide_state_dir / "jeton-de-session"` et le fichier est
  supprimé à l'arrêt ; un `STATIC_TOKEN` n'écrit aucun fichier. Le jeton est
  ajouté aux valeurs masquées des journaux (même mécanisme que les secrets,
  ticket-758).
- `StaticTokenMiddleware` compare à `jeton_de_session.courant()` : plus de
  chemin « jeton vide, on laisse passer ». `/health` et `OPTIONS` restent
  ouverts. `HostOriginMiddleware` est inchangé.
- Le jeton n'entre jamais dans l'environnement d'un agent, une ligne de
  commande ou la base.
- `backend/tests/conftest.py` : une fixture autouse fixe le jeton à une
  valeur de test et fait porter `Authorization: Bearer` (et `?token=` aux
  WebSockets) par défaut au `TestClient`, pour que la suite existante passe
  sans retoucher chaque fichier. Les tests qui posaient `static_token=""`
  pour une API ouverte testent désormais le 401 sans en-tête.
- Une ADR au prochain numéro libre de `memory/decisions.md` (base : le
  brouillon de conception résumé ci-dessus ; alternatives écartées :
  injection par le proxy Vite, vérification du processus pair, `Origin`) ; la
  règle va sous `## Proposées` de `memory/contraintes.md`.

La phrase « vide (le défaut), l'API est ouverte » du `CLAUDE.md` racine sera
corrigée à la main après le merge (fichier interdit aux agents).

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_jeton_de_session.py` vérifie qu'avec
      `STATIC_TOKEN` vide, `GET /api/v1/projects` sans en-tête rend 401, et
      200 avec `Bearer <courant()>`.
- [ ] Un test vérifie que la WebSocket `/api/v1/orchestrator/observe` sans
      `?token=` est refusée.
- [ ] Un test de `backend/tests/test_invariant_routes_jeton.py` parcourt
      **toutes** les routes de `app.routes` sauf `/health`, et vérifie que
      chacune refuse une requête sans jeton : une route ajoutée plus tard est
      couverte d'office.
- [ ] Un test vérifie qu'avec `STATIC_TOKEN="x"`, `x` est requis et aucun
      fichier `jeton-de-session` n'est écrit ; avec `STATIC_TOKEN` vide, le
      fichier existe pendant le `lifespan` et disparaît après.
- [ ] Un test de `backend/tests/test_env_sdk.py` vérifie que l'environnement
      d'un agent ne contient pas la valeur du jeton de session.
- [ ] Le diff ajoute une ADR à `memory/decisions.md` et une règle sous
      `## Proposées` de `memory/contraintes.md`.

## Dépendances

ticket-877 : l'interface doit savoir porter le jeton avant qu'il soit exigé.

## Estimation

Une journée.

## Risques

79 fichiers de tests construisent un `TestClient` : la fixture autouse doit
les couvrir sans les modifier un à un. Les tests e2e du frontend simulent les
routes (`page.route`) et ne sont pas concernés.
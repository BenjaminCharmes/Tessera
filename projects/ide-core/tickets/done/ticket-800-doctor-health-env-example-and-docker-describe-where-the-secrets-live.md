---
id: ticket-800
title: "Doctor, health, the env example and Docker describe where the secrets live"
type: chore
status: done
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-797"]
estimated_days: 1
created: 2026-11-05
---

# ticket-800 — `doctor`, `/health`, `.env.example` et Docker disent où vivent les secrets

## Objectif

Un utilisateur voit où chaque secret est rangé, et un clone neuf, Docker ou une machine sans
trousseau sait quoi déclarer.

## Contexte

Design §3 et §5. Le ticket-795 lit le coffre en mode `auto` par défaut (repli sur `.env` avec un
avertissement, refus si un secret migré manque) : `doctor` doit dire d'où vient chaque secret,
au lieu de « renseigne `.env` » pour une clé qui n'y est plus.

## Ce que le ticket fait

- `backend/src/tessera/doctor.py` : une vérification « Secrets » — mode, coffre joignable ou
  non, noms encore en clair dans `.env` avec la commande `tessera.ps1 secrets migrer`. Les
  messages existants qui renvoient à `.env` pour `ANTHROPIC_API_KEY` disent « coffre ou `.env` ».
- `GET /health` : un champ `secrets` valant `coffre`, `env` ou `env-repli` (mode `auto` sans
  coffre), jamais un nom ni une valeur.
- `.env.example` : les secrets restent en exemple commenté pour le mode `env` ; un bloc explique le
  coffre, `SECRETS_SOURCE` et `tessera.ps1 secrets`. `scripts/tessera.ps1 setup` indique la
  commande de migration après la copie.
- `docker-compose.yml` : `SECRETS_SOURCE=env` dans `environment`.

## Tests

- `backend/tests/test_doctor.py` (existant) : `test_doctor_reports_the_secrets_mode`,
  `test_doctor_names_secrets_still_in_clear_in_dotenv`,
  `test_doctor_never_prints_a_secret_value`.
- `backend/tests/test_health.py` (existant) : `test_health_reports_the_secrets_mode_only`.
- `test_env_example_documents_secrets_source` : le fichier cite `SECRETS_SOURCE`.
- `test_docker_compose_declares_the_env_secrets_mode`.

## Critères d'acceptation

- [x] Les tests ci-dessus passent
- [x] `.github/workflows/ci.yml` n'est pas modifié : la suite pose `SECRETS_SOURCE=env` par
      `conftest.py` (ticket-795), et un agent n'écrit pas dans `.github/workflows/`

## Ce que ça ne fait pas

Aucune documentation de guide : la mise à jour par lot (ADR-035) s'en charge.

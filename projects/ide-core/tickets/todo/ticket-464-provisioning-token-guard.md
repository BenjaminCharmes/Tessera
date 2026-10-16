---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 1
id: ticket-464
priority: high
status: todo
title: Online service tokens are read by the backend only and never reach an agent,
  a log or a push
type: feat
---

# ticket-464 — Garde des jetons de mise en ligne

## Objectif

Poser la garde d'ADR-053 **avant** qu'un seul jeton existe dans le `.env` :
aucun agent ne le reçoit ni ne le lit, aucun log ne le montre, aucun push ne
l'emporte.

## Contexte

ADR-053. Aujourd'hui `Read`, `Glob` et `Grep` ne passent par aucun hook, et
ADR-031 permet de lire hors du projet : le `.env` de Tessera (à la racine du
dépôt, ancêtre de `projects/`) se lit. `config.Settings` n'exporte pas le
`.env` dans `os.environ`, mais un jeton déjà exporté dans le shell serait
hérité par le CLI de l'agent. `utils/logger.py` ne masque rien.

Jetons : `VERCEL_TOKEN`, `NEON_API_KEY`, `RESEND_API_KEY`, `STRIPE_API_KEY`,
`CLOUDFLARE_API_TOKEN` (+ `VERCEL_TEAM_ID`, non secret).

## Solution proposée

- `config.Settings` : cinq champs `SecretStr`, vides par défaut ; `.env.example`
  les documente avec leur portée minimale (docs/architecture.md, « Mise en
  ligne ») et la consigne d'expiration.
- Un `SecretRegistry` (`utils/secrets.py`) : les valeurs de `Settings` y sont
  inscrites au démarrage, et `register(valeur)` y ajoute un secret reçu d'une
  API pendant l'exécution. Un filtre du logger remplace toute valeur inscrite
  par `***`.
- Un hook `PreToolUse` (`services/providers/`, à côté de `perimetre.py`) sur
  `Read|Glob|Grep|Bash` : refuse le `.env` de Tessera (`Settings.env_file`),
  chemin résolu contre le `cwd` du run. Pour `Bash`, repérage lexical des
  chemins de la commande ; il attrape une erreur, pas une évasion (ADR-031) —
  dire ce plafond dans le message de refus et dans la docstring.
- `agent_sdk` vide les cinq variables dans `env`, comme `ANTHROPIC_API_KEY`.
- `TermesInterditsService` ajoute les valeurs des jetons configurés aux termes
  contrôlés ; `Livraison.arret` localise sans nommer la valeur (ADR-048).
- `ADR-053` s'ajoute à `_CONTRAINTES` dans `tests/test_adr_pertinents.py`.

## Critères d'acceptation

- [ ] Un test vérifie que `repr(settings)` et `settings.model_dump()` ne
      contiennent la valeur d'aucun des cinq jetons
- [ ] Un test vérifie que le logger remplace par `***` la valeur d'un jeton
      configuré et celle d'un secret passé à `SecretRegistry.register`
- [ ] Un test vérifie que le hook refuse `Read`, `Glob` et `Grep` du `.env` de
      Tessera par chemin absolu, relatif et avec `..`, et laisse passer
      `.env.example` ainsi que le `.env` du projet courant
- [ ] Un test vérifie que le hook refuse un `Bash` qui lit le `.env` de Tessera
      (`cat`, `type`, `Get-Content`) et laisse passer une commande sans lien
- [ ] Un test vérifie que les options du SDK vident les cinq variables dans
      `env`, même exportées dans l'environnement du backend
- [ ] Un test vérifie qu'un diff ajoutant la valeur d'un jeton configuré arrête
      le push, sans que `Livraison.arret` contienne cette valeur

## Ce que ça ne fait pas

N'appelle aucun service. Ne protège pas d'un `Bash` qui contourne le repérage
lexical : le plafond réel d'un jeton est sa portée et son expiration.

## Dépendances

Aucune. Tous les tickets de mise en ligne en dépendent.

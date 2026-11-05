---
id: ticket-798
title: "The pre-push hook and the history scan read the forbidden terms through the backend"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-797"]
estimated_days: 1
created: 2026-11-05
---

# ticket-798 — Le hook `pre-push` et le scan d'historique lisent les termes interdits par le backend

## Objectif

`FORBIDDEN_TERMS` vit dans le coffre sans que la porte de push perde un contrôle, y compris
depuis un worktree.

## Contexte

Design §6, ADR-050. Le hook lit `Path(".env")` relatif au dossier courant (absent d'un worktree) ;
`scripts/scan_historique.py` lit `.env` du dépôt. Le hook est en bibliothèque standard seule.

## Ce que le ticket fait

- Sous-commande `termes` de `backend/src/tessera/coffre_cli.py` : applique l'ordre variable
  d'environnement, coffre, `.env`, écrit la liste (virgules) sur la sortie standard. Code 0 et
  sortie vide : aucune liste. Code non nul : n'a pas pu juger.
- `scripts/hooks/pre-push` : `load_forbidden_terms` appelle
  `uv run --project <racine>/backend python -m tessera.coffre_cli termes`, la racine déduite du
  chemin du hook. Code non nul, `uv` introuvable ou délai dépassé : push refusé, message qui cite
  `uv sync` et `SECRETS_SOURCE=env`, jamais un terme. Plus aucune lecture de `.env`.
- `scripts/scan_historique.py` : même appel.

## Tests

- `backend/tests/test_hook_pre_push.py` (existant) :
  `test_hook_uses_the_terms_printed_by_the_backend`,
  `test_hook_without_a_list_does_not_control_locally` (code 0, sortie vide),
  `test_hook_refuses_when_the_backend_cannot_judge` (code non nul),
  `test_hook_refuses_when_uv_is_missing`, `test_hook_message_never_holds_a_term`.
  Le lanceur du sous-processus s'injecte, aucun vrai `uv` n'est appelé.
- `backend/tests/test_coffre_cli.py` : `test_termes_prints_the_vault_list`,
  `test_termes_env_variable_wins_over_the_vault`, `test_termes_exits_non_zero_without_a_vault_in_coffre_mode`,
  `test_termes_falls_back_to_dotenv_when_the_vault_has_no_entry`.
- `test_scan_historique_reads_terms_through_the_resolver` pour le script.

## Critères d'acceptation

- [ ] Un push de test depuis un worktree, avec la liste dans le coffre, est arrêté sur un terme
      factice ; le résultat est noté dans le message de commit
- [ ] `termes_interdits_ci.py` et la CI ne changent pas (le secret GitHub reste l'environnement)
- [ ] Le hook reste sans import hors de la bibliothèque standard

## Ce que ça ne fait pas

Le garde de lecture qui refuse `coffre_cli` aux agents (ticket-799) : `termes` est la seule
commande qui écrit une valeur de coffre, et sa sortie ne va qu'au hook.

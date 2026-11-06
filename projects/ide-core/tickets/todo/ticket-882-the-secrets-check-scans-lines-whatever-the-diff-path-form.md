---
id: ticket-882
title: "The secrets check scans added lines even when the diff path is quoted or unprefixed"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-06
---

# ticket-882 — The secrets check scans added lines even when the diff path is quoted or unprefixed

## Objectif

Le contrôle des secrets avant push ne laisse plus passer les lignes ajoutées d'un fichier dont l'en-tête de diff n'a pas la forme `+++ b/…`.

## Contexte

Trouvé par l'essai de seconde revue (ticket-846, `docs/essais/seconde-revue.md`) : le reviewer l'a relevé sur un commit classé sain, un humain l'a confirmé, et le défaut est toujours sur `develop` le 06/11. Entrée s02, ticket-547.

Dans `backend/src/tessera/services/gardes/secrets_diff.py`, `_parcourir` ne retient un fichier que si la cible commence par `b/` ; sinon `fichier` vaut `None` et toutes ses lignes ajoutées sont sautées. Un nom contenant un guillemet ou une barre oblique inverse est mis entre guillemets par git (`+++ "b/…"`), et un `diff.noprefix` global supprime le `b/`. `diff_de_branche` (`backend/src/tessera/services/git_workspace/historique.py`) ne force pas les préfixes. La porte échoue ouverte, contre ADR-039.

## Solution proposée

- `_parcourir` décode un chemin `+++ "b/…"` (échappements octaux compris).
- Un en-tête `+++ ` qu'il ne sait pas lire fait refuser le diff par `refus_secrets` au lieu de sauter ses lignes.
- `diff_de_branche` passe `--src-prefix=a/ --dst-prefix=b/` à `git diff`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_secrets_diff.py` vérifie qu'un secret ajouté sous un en-tête `+++ "b/dossier/na\303\257f.py"` donne une `ViolationSecret` dont le chemin est décodé (`dossier/naïf.py`).
- [ ] Un test vérifie qu'un diff dont l'en-tête est `+++ fichier.py` (sans préfixe) fait renvoyer un refus non vide par `refus_secrets`.
- [ ] Un test vérifie que la commande lancée par `diff_de_branche` contient `--src-prefix=a/` et `--dst-prefix=b/`.

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus.

## Ce que ça ne fait pas

Ne revoit pas le reste du ticket d'origine : seulement le défaut confirmé.

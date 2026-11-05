---
id: ticket-844
title: "A replay script runs a candidate reviewer on the corpus with a spending cap"
type: chore
status: done
priority: low
agent: codeur
created: 2026-11-05
depends_on: [ticket-841, ticket-843]
estimated_days: 1
pr_number: null
---

# ticket-844 — Un script rejoue un reviewer candidat sur le corpus, sous plafond de dépense

## Objectif

Rejouer, entrée par entrée, le reviewer actuel (bras B) ou un candidat (bras C) et consigner
chaque appel, sans toucher à un run, à un worktree ni à `agents.json` (ADR-079, spec §3).

## Interface à respecter

Nouveau fichier `scripts/seconde_revue.py` (300 lignes au plus), lancé depuis `backend/` :

```
python ../scripts/seconde_revue.py rejouer --bras B
python ../scripts/seconde_revue.py rejouer --bras C --candidat ollama:qwen3-coder:30b \
       --fenetre-caracteres N --budget-usd 10
```

```python
def agents_json_temporaire(dossier: Path, bras: str, provider: str, modele: str) -> Path: ...
    # écrit <dossier>/agents.json avec UN rôle (`reviewer` pour B, `candidat` pour C),
    # sans clé `fallback`, et rend le dossier du « projet »

async def rejouer(
    corpus: Corpus, bras: str, provider: str, modele: str, *,
    depot: Path, racine_tickets: Path, sortie: Path,
    budget_usd: float, fenetre_caracteres: int | None,
    construire: Callable[[Path, str], LLMProvider] = ...,   # défaut : provider_pour_role
) -> list[Resultat]: ...
```

Règles :

- le provider se construit par `provider_pour_role(projet_temporaire, role, allow_tools=False)`
  (ADR-046) ; jamais `get_provider`, jamais le `agents.json` d'ide-core ; le dossier
  temporaire se supprime à la fin
- l'appel passe le prompt de `agents/prompts/reviewer.md` et `REVIEWER_SCHEMA`
  (`complete(..., schema=...)` : lire sa signature dans `providers/base.py`)
- un prompt plus long que `fenetre_caracteres` n'est pas envoyé : `hors_fenetre` ; l'option est
  obligatoire pour un candidat `ollama`
- une indisponibilité du provider consigne `indisponible` : pas de repli, pas de nouvel essai
- une sortie absente ou hors schéma consigne `hors_schema`
- avant chaque appel, la somme des `cout_usd` déjà consignés plus l'appel ne doit pas dépasser
  `budget_usd` ; sinon le script s'arrête, code de sortie non nul, message qui dit combien
  reste d'entrées
- une entrée déjà consignée pour ce couple (`id`, `bras`) et ce `gel_sha256` n'est pas
  rejouée : le script se reprend
- un `gel_sha256` du fichier de résultats différent de celui du corpus refuse de continuer

## Critères d'acceptation

- [x] `scripts/seconde_revue.py` porte les deux fonctions et la commande `rejouer`
- [x] `backend/tests/test_seconde_revue.py`, avec un faux `LLMProvider` injecté par `construire`,
      couvre : une ligne `ok` consignée avec coût et durée ; `hors_fenetre` sans appel ;
      `indisponible` sans second appel ; `hors_schema` ; arrêt avant l'appel qui dépasserait
      le plafond, avec les lignes déjà écrites conservées ; reprise qui ne rejoue pas une
      entrée faite ; refus d'un fichier de résultats d'un autre `gel_sha256`
- [x] Un test lit le `agents.json` écrit : un seul rôle, aucune clé `fallback`
- [x] Un test vérifie que le dossier temporaire est supprimé, y compris sur erreur, et que le
      `agents.json` d'ide-core est inchangé (octets identiques)
- [x] `grep get_provider scripts/seconde_revue.py` ne rend rien ; aucun fichier de
      `backend/src` ne mentionne `seconde_revue`

## Ce que ça ne fait pas

Ne lance aucun rejeu réel (ticket-846), n'écrit pas le rapport (ticket-845), ne juge rien.

## Dépendances

tickets 805 et 807.

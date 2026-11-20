---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-848
pr_number: null
priority: high
status: done
title: prochain_numero reserves the number it returns
type: feat
---

# ticket-848 — `prochain_numero` réserve le numéro qu'il rend

## Objectif

Deux designs lancés en parallèle ne reçoivent jamais le même numéro de ticket ou d'ADR.

## Contexte

ADR-080, spec `docs/superpowers/specs/2026-11-05-superviseur-design.md` §5. Le 05/11, les
tickets 801-804 et ADR-074 ont été pris par trois designs parallèles puis renumérotés après
coup (`pipeline-log`, 11:19). `numerotation.py` (ticket-659) lit l'arbre, `origin/<base>` et
les branches `origin/ticket-*` : un numéro choisi mais pas encore poussé reste invisible.

## Ce qu'il faut faire

- `numerotation.reserver(depot, genre, base, dossier_etat) -> int` : plus grand numéro pris
  (existant) ou réservé, plus un ; l'écrit dans `<dossier_etat>/numeros_reserves.json`
  (écriture atomique `tmp` + `replace`, un verrou de fichier le temps de lire-écrire). Un
  numéro réservé n'est jamais rendu deux fois, utilisé ou non.
- `scripts/prochain_numero.py` appelle `reserver` par défaut ; `--sans-reserver` garde la lecture
  seule. `dossier_etat` vient de `IDE_STATE_DIR` (défaut : celui de `settings`) ; le module reste
  en bibliothèque standard seule.
- Fichier illisible : mis de côté en `.corrompu` et recréé, jamais écrasé en silence.

## Critères d'acceptation

- [ ] `test_prochain_numero.py::test_two_calls_return_distinct_numbers` : deux appels de suite
      rendent n puis n+1 sans rien écrire dans l'arbre
- [ ] `test_prochain_numero.py::test_reserved_number_is_never_reissued_after_tree_catches_up` :
      un numéro réservé puis écrit dans l'arbre n'est pas rendu à nouveau
- [ ] `test_prochain_numero.py::test_without_reserve_reads_only` : `--sans-reserver` ne crée aucun
      fichier
- [ ] `test_prochain_numero.py::test_corrupt_reservation_file_is_set_aside`

## Ce que ça ne fait pas

Ne libère aucun numéro réservé : un trou dans la numérotation est sans importance.
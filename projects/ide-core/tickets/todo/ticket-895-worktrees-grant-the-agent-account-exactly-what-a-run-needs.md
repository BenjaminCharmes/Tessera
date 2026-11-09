---
id: ticket-895
title: "Worktrees grant the agent account exactly what a run needs"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-09
---

# ticket-895 — Un worktree accorde au compte agent exactement ce qu'un run demande

## Objectif

Que le compte `tessera-agent` puisse écrire le code d'un run et rien d'autre :
ni `.git`, ni les fichiers de politique, ni le script des tests.

## Contexte

Le ticket-894 fait tourner le CLI sous le compte `tessera-agent`. Sans droits
posés, ce compte ne peut rien écrire dans un worktree créé par le backend sous le
compte de Benjamin. La phase 0 du 09/11 a posé ces droits à la main sur le projet
jetable `proto-isolation`, sans élévation (Benjamin est propriétaire de ses
dossiers) :
- `icacls <dossier> /grant tessera-agent:(OI)(CI)M` : modifier, jamais `F`, qui
  inclut la suppression des enfants ;
- `.git` en lecture seule : héritage désactivé, droits de l'agent retirés, puis
  `(OI)(CI)RX` ; mesuré : le commit de l'agent échoue (code 128) ;
- `agents.json` : `/deny tessera-agent:(W,D)` ; mesuré : l'écriture échoue et le
  hash ne change pas.

`backend/src/tessera/services/providers/chemins_proteges.py` liste déjà les
fichiers de politique (`motif_de_protection`).

## Solution proposée

- Un module de droits (domaine `worktrees` ou plus bas, selon `ORDRE` de
  `test_domaines_services.py`) qui pose ces trois règles par `icacls`, appelé à la
  création d'un worktree quand `AGENT_USER` est renseigné.
- Le refus `(W,D)` couvre chaque fichier existant que `motif_de_protection`
  désigne dans le worktree, plus le script de `test_command` (ADR-072).
- Un worktree dont un fichier a été créé par l'agent reste supprimable par le
  backend.
- Sans `AGENT_USER`, rien n'est posé.

## Critères d'acceptation

- [ ] Avec `AGENT_USER` vide, la création d'un worktree n'appelle pas `icacls` ;
      un test doublé le vérifie.
- [ ] Avec `AGENT_USER` renseigné, un test doublé vérifie les appels : `M` hérité
      sur le worktree, `RX` sur son `.git` après retrait des droits hérités de
      l'agent, `(W,D)` refusé sur `agents.json`, un `CLAUDE.md` et le script de
      `test_command`.
- [ ] Aucun appel n'accorde `F` ; un test le vérifie sur la liste des arguments.
- [ ] La liste des fichiers refusés vient de `motif_de_protection` de
      `chemins_proteges.py` ; le diff n'ajoute pas de liste de noms en double.
- [ ] Un échec d'`icacls` lève une erreur qui met le run en `blocked` (ADR-037) ;
      un test le vérifie.

## Dépendances

Aucune pour l'écrire ; il ne sert qu'avec le ticket-894.

## Estimation

Un jour.

## Risques

Un fichier de politique créé par l'agent pendant le run n'a pas de refus posé :
la revue (ADR-072) et le hook restent la porte pour ceux-là.

## Ce que ça ne fait pas

- Ne crée pas le compte : c'est le script d'installation (ticket-896).
- Ne touche pas aux projets sans `worktree` : un run sous le compte agent y est
  refusé tant qu'un ticket ne l'ouvre pas.

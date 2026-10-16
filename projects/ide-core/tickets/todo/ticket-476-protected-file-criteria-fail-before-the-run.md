---
id: ticket-476
title: "A criterion that needs a protected file stops the run before it starts, and guard refusals reach the reviewer"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-16
---

# ticket-476 — Un critère sur un fichier protégé ne brûle plus trois tours

## Objectif

Un ticket dont un critère exige de modifier un fichier que le garde-fou
refuse aux agents s'arrête avant le premier tour, avec un message clair ; et
quand le garde-fou refuse une écriture pendant un tour, le reviewer et le
validateur le savent.

## Contexte

make-your-call (Devinoo), 16/10, ticket-017 : le dernier critère exigeait de
modifier `CLAUDE.md`. Au tour 1, le codeur a tenté l'Edit, refusé par le
garde-fou (« un run ne modifie pas ses propres règles »), et l'a écrit dans
son rapport aux trois tours. Le reviewer et le validateur, qui ne voient pas
ce refus, ont redemandé la modification à chaque tour : 3 tours (≈ 7 $)
perdus sur un critère impossible. Déjà vu : ticket-276 (un skill), 001 de
`carriere`/`freelance` (la CI), ticket-326.

Les chemins protégés sont listés dans
`backend/src/tessera/services/chemins_proteges.py` (`CLAUDE.md`,
`CLAUDE.local.md`, `agents.json`, `.claude/`, `.github/workflows/`,
`.git/`).

## Solution proposée

1. **Avant le premier tour** : si un critère d'acceptation cite entre
   backticks un chemin protégé avec un verbe d'écriture (modifier, mettre à
   jour, ajouter, créer, supprimer, contient…) ou si son seul livrable est un
   chemin protégé, le run s'arrête en `blocked` avant le codeur, avec « le
   critère N demande d'écrire <chemin>, que le pipeline refuse aux agents :
   à faire à la main ». Le plan précise la règle exacte, sans faux positif
   sur un critère qui se contente de lire ou de citer le fichier.
2. **Pendant un tour** : les refus du garde-fou (chemin, raison) sont
   collectés et passés au reviewer et au validateur avec le diff, sous un
   titre « Écritures refusées par le garde-fou pendant ce tour ». Le prompt
   leur dit de ne pas redemander une écriture que le pipeline interdit.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket dont un critère dit « `CLAUDE.md` contient
      la nouvelle section » s'arrête avant l'appel au codeur, avec le chemin
      dans l'arrêt
- [ ] Un test vérifie qu'un critère qui cite `CLAUDE.md` sans l'écrire
      (« d'après `CLAUDE.md` ») ne bloque pas
- [ ] Un test vérifie qu'un refus du garde-fou pendant le tour apparaît dans
      le message envoyé au reviewer et au validateur
- [ ] La règle de détection est décrite dans la PR

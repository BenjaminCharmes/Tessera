---
id: ticket-747
title: "Protected names are compared after Windows name normalization"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-747 — Les noms protégés se comparent après normalisation Windows

## Objectif

Aucune variante de nom Win32 ne permet d'écrire un fichier protégé qui n'existe pas encore.

## Contexte

Audit du 30/10 (relecture du 03/11), tickets 706-707 ; reprend C-10 de
`docs/audit/securite.md`, jamais ticketée. `motif_de_protection`
(`backend/src/tessera/services/chemins_proteges.py`) compare `settings*.json`, `.claude`,
`CLAUDE.md` avec la casse et le nom exacts ; `_is_self_executing`
(`backend/src/tessera/routers/fs.py`) teste `endswith(".json")`. Quand la cible n'existe
pas, `resolve()` ne normalise rien. Passent les deux gardes (vérifié) :
`.claude/settings.json.` (point final), `.claude/settings.json::$DATA`,
`.claude/settings.local.json ` (espace final), `sub/CLAUDE.md.`, `.GitHub/workflows/x.yml` ;
côté hook agent, `.Claude/Settings.json`. Windows crée pourtant `settings.json`, que
`setting_sources=["project"]` charge à la session agent suivante du run.

## Solution proposée

Une fonction de normalisation commune aux deux gardes, appliquée à chaque segment avant
toute comparaison : retirer un suffixe `::…` (flux NTFS), retirer points et espaces finaux,
comparer en `casefold()`.

## Critères d'acceptation

- [ ] Un test paramétré vérifie que `.claude/settings.json.`, `.claude/settings.json::$DATA`,
      `.claude/settings.local.json ` (espace final), `.Claude/Settings.json` et
      `sub/CLAUDE.md.`, fichiers absents, sont refusés par `motif_de_protection`
- [ ] Le même jeu est refusé par le garde d'écriture de `routers/fs.py`
- [ ] Un test vérifie que `.GitHub/Workflows/x.yml` est refusé
- [ ] Un test vérifie que `settings.md` et `notes/claude-notes.md` passent

## Risques

Aucun : on refuse plus, jamais moins.

---
id: ticket-737
title: "Stopping Tessera reads a launcher input that starts with a BOM"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-737 — L'arrêt de Tessera lit une entrée qui commence par un BOM

## Objectif

`.\scripts\tessera.ps1 stop` fonctionne aussi sous Windows PowerShell 5.1.

## Contexte

03/11 : `powershell -File scripts\tessera.ps1 stop` échoue avec
`JSONDecodeError: Unexpected UTF-8 BOM` dans `scripts/arreter_tessera.py`. Windows
PowerShell 5.1 préfixe le tube d'un BOM malgré le `$OutputEncoding` sans BOM que
pose `tessera.ps1` ; pwsh 7 n'en met pas, d'où un défaut resté invisible.

## Solution proposée

`main` décode l'entrée en `utf-8-sig` : le BOM est retiré s'il est là, et rien ne
change sans lui. Correctif fait à la main (petit, isolé).

## Critères d'acceptation

- [x] `test_main_accepts_stdin_starting_with_a_utf8_bom` (`backend/tests/test_arreter_tessera.py`)
      passe une entrée préfixée d'un BOM à `main` et obtient la sélection attendue
- [x] Un JSON passé par un tube Windows PowerShell 5.1 à `scripts/arreter_tessera.py`
      donne `[]` et le code 0 (vérifié à la main le 03/11)

## Ce que ça ne fait pas

Ne change rien à la sélection des processus ni à `tessera.ps1`.

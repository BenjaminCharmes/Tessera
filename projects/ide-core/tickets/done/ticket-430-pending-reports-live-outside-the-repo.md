---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-430
pr_number: null
priority: critical
status: done
title: Pending reports are kept outside the repository, so a run can never commit
  them nor a branch switch lose them
type: fix
---

# ticket-430 — La file d'attente des signalements vit hors du dépôt

## Objectif

Qu'un signalement mis en attente pendant un run ide-core (ticket-421) ne
puisse ni partir dans le commit de ce run, ni disparaître au changement de
branche.

## Contexte

Le 2026-10-14, quatre signalements (affût et vigie) ont reçu
`202 {"en_attente": true}` pendant le run du ticket-429. Le fichier
d'attente est écrit par `services/signalements_en_attente.py` dans
`settings.ide_db_path.parent / "signalements_en_attente.json"`, soit
`backend/`, **dans le dépôt** et non ignoré par git. Le commit de suivi du
run l'a emporté dans la PR #426 ; puis, l'arbre revenu sur `develop`, le
fichier a disparu du disque : aucun des quatre signalements n'est devenu un
ticket. Ils ont été récupérés à la main depuis la PR (tickets 431 à 433).

## Solution proposée

- Le fichier d'attente va dans un dossier de données **hors du dépôt** :
  un réglage `ide_state_dir` (défaut : `%LOCALAPPDATA%\Tessera` sous
  Windows, `~/.local/state/tessera` ailleurs, créé au besoin).
- Au démarrage, si un ancien fichier `backend/signalements_en_attente.json`
  existe, son contenu est déplacé dans le nouveau fichier puis l'ancien est
  supprimé.
- `.gitignore` : `backend/signalements_en_attente.json`, filet de sécurité.

## Critères d'acceptation

- [ ] Un test vérifie que le chemin du fichier d'attente n'est pas sous la
      racine du dépôt (`_REPO_ROOT`)
- [ ] Un test vérifie qu'un ancien fichier sous `backend/` est repris dans le
      nouveau emplacement puis supprimé, sans perte ni doublon
- [ ] `.gitignore` contient `backend/signalements_en_attente.json`
- [ ] Les tests du ticket-421 restent verts

## Dépendances

Aucune.
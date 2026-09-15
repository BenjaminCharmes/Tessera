---
id: ticket-056
title: "Rendre le lancement fiable sous Windows"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-056 — Robustesse du lancement sous Windows

## Objectif

Que la procédure documentée fonctionne telle quelle sous Windows, qui est la
plateforme de développement réellement utilisée.

## Contexte

Plusieurs frictions constatées à l'usage le 2026-09-15 :

- **`make run` se comporte mal** — il repose sur `trap 'kill 0'` et `wait`,
  sémantiques POSIX. Sous Windows il faut lancer les deux processus à la main,
  ce que le README ne dit pas.
- **Le worker `uvicorn --reload` orphelin** — tuer le parent laisse l'enfant
  vivant, qui garde le port 8000 et sert le code tel qu'il était à son dernier
  rechargement. Symptômes : des `500` inexplicables, un port impossible à
  libérer, et un PID que `Get-Process` ne trouve pas. Le piège est documenté
  dans le skill `run-vibe-ide`, mais il reste un piège.
- **Les symlinks** exigent le mode développeur. Traité côté message d'erreur
  (ticket-050), pas côté procédure.
- **Le build Tauri** n'a pas été vérifié depuis ticket-039.

## Solution proposée

1. **Une cible `make run` qui marche partout**, ou une alternative documentée
   explicitement pour Windows — pas un script POSIX qui échoue en silence.
2. **Un `make stop`** qui termine proprement les processus, worker orphelin
   compris, au lieu de laisser l'utilisateur chercher un PID.
3. **Détection au démarrage** : si le port 8000 est déjà occupé, le dire
   clairement plutôt que d'échouer sur une trace de `bind`.
4. **Vérifier le build Tauri** sur la machine et consigner ce qui manque.
5. **Un `make doctor`** qui contrôle les prérequis : versions, `.env`,
   résolution de `IDE_PROMPTS_DIR`, provider joignable, mode développeur. Les
   deux pannes de ticket-050 étaient l'une et l'autre détectables en amont.

## Critères d'acceptation

- [x] `make run` fonctionne sous Windows, ou la procédure Windows est
      documentée et vérifiée
- [x] `make stop` termine backend et frontend, worker orphelin compris
- [x] Un port déjà occupé produit un message explicite, pas une trace de `bind`
- [x] `make doctor` détecte : provider injoignable, prompts introuvables,
      `.env` absent, symlinks indisponibles
- [x] L'état du build Tauri est vérifié et consigné
- [x] Le README décrit la procédure Windows sans approximation

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Faible** — outillage uniquement, aucun code produit n'est touché.

## Le constat qui change tout

**`make` n'est installé nulle part sur la machine de développement.** Ni dans
Git Bash, ni dans PowerShell, ni via scoop. Toute la procédure du README —
`make setup`, `make run`, `make test`, `make lint` — était donc **inutilisable
telle quelle** sur la plateforme réellement utilisée.

Le ticket parlait d'adapter `make run` ; le vrai problème était l'absence de
`make`. D'où `scripts/vibe.ps1`, un équivalent sans dépendance.

## Livré

| Élément | Rôle |
|---|---|
| `backend/src/vibe_ide/doctor.py` | 8 contrôles de prérequis, avec le correctif à appliquer |
| `scripts/vibe.ps1` | Équivalent du Makefile pour Windows |
| `Makefile` | Cibles `doctor`, `run-windows`, `stop` |
| README, guide utilisateur | Procédure Windows, piège du worker orphelin |

## Deux défauts trouvés en lançant le doctor une seule fois

1. **`env_file=".env"` était relatif au cwd.** Lancé depuis `backend/`, un
   réglage pourtant présent dans `.env` était silencieusement ignoré et le
   défaut s'appliquait — le doctor affichait le mauvais workspace. Même classe
   de bug que `IDE_PROMPTS_DIR` en ticket-050. Ancré sur la racine du dépôt.
2. **Le doctor plantait sur la console cp1252** en affichant une flèche — l'outil
   censé diagnostiquer les problèmes d'encodage en était lui-même victime.
   `sys.stdout.reconfigure(encoding="utf-8")`.

## Non vérifié

**Le build Tauri reste invérifiable sur cette machine : Rust/cargo est absent.**
Le doctor le signale sans bloquer — l'IDE tourne en web sans Tauri. Installer
une toolchain complète sortait du périmètre d'un ticket d'outillage.

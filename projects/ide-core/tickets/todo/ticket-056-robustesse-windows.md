---
id: ticket-056
title: "Rendre le lancement fiable sous Windows"
type: chore
status: todo
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

- [ ] `make run` fonctionne sous Windows, ou la procédure Windows est
      documentée et vérifiée
- [ ] `make stop` termine backend et frontend, worker orphelin compris
- [ ] Un port déjà occupé produit un message explicite, pas une trace de `bind`
- [ ] `make doctor` détecte : provider injoignable, prompts introuvables,
      `.env` absent, symlinks indisponibles
- [ ] L'état du build Tauri est vérifié et consigné
- [ ] Le README décrit la procédure Windows sans approximation

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Faible** — outillage uniquement, aucun code produit n'est touché.

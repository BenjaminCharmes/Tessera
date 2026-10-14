---
id: ticket-434
title: "The validator is given the files a criterion cites whatever its provider, and the log says which files it received"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-14
plan: true
---

# ticket-434 — Le validateur reçoit les fichiers cités, quel que soit son modèle

## Objectif

Qu'un critère d'acceptation portant sur un fichier existant, inchangé par le
run, ne puisse plus être refusé faute pour le validateur d'avoir vu ce
fichier — et qu'on sache, en lisant le journal, ce qu'il a reçu.

## Contexte

Signalement d'affût, 2026-10-14 (arrivé par `/signalements`, renuméroté de
430 en 434) : ticket-052 d'affût, critère « `charter-contrast.test.ts`
vérifie les 8 lignes du tableau des contrastes… ». Le fichier existe
(`projects/affut/frontend/src/charter-contrast.test.ts`) et n'avait pas à
changer. Le validateur local (Ollama, qwen3-coder) a répondu
CHANGES_REQUESTED : « le fichier s'appelle charter.test.ts au lieu de
charter-contrast.test.ts ». Tests, sécurité et reviewer étaient verts ; les
3 tours se sont épuisés et la file s'est arrêtée. Livré à la main (PR affut
#73).

Le ticket-316 (`services/validator.py` : `extract_file_refs`,
`_find_file_in_project`, `_build_cited_files_section`) joint déjà au
message les fichiers cités entre backticks. Il reste à établir si la
section est arrivée au modèle (provider Ollama, troncature à
`_CITED_FILES_MAX_CHARS`, contexte du modèle local) ou si le modèle a mal
lu.

## Solution proposée

- Tour de plan : rejouer la construction du message du validateur pour le
  ticket-052 d'affût et dire si `charter-contrast.test.ts` y figure en
  entier.
- Corriger ce qui empêche la section d'arriver, quel que soit le provider
  (Claude, Ollama, repli).
- Le journal du pipeline indique, à chaque validation, les fichiers cités
  joints (et ceux introuvables ou tronqués) :
  `validateur: fichiers cités joints : a, b ; absents : c`.
- Si la section était complète : le documenter dans le ticket (refus dû au
  modèle) — la décision de garder un validateur local sur un projet reste
  une décision de configuration, hors de ce ticket.

## Critères d'acceptation

- [ ] Un test vérifie que, pour un critère citant un fichier existant non
      modifié par le diff, le message envoyé au validateur contient le
      contenu de ce fichier, avec un provider Ollama simulé
- [ ] Un test vérifie que la ligne de journal `fichiers cités joints` liste
      les fichiers joints et les absents
- [ ] Un test vérifie qu'un fichier cité trop long pour la limite est
      signalé « tronqué » dans cette ligne

## Dépendances

Aucune.

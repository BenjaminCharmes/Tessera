---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-612
estimated_days: 1.5
id: ticket-614
priority: medium
status: done
title: The reviewer verdict comes from a structured output and the keyword parser
  is removed
type: feat
---

# ticket-614 — Le verdict du reviewer sur un schéma

## Objectif
Le reviewer rend un objet validé ; le pipeline en tire le verdict, le texte que
lit le codeur et le champ que lit l'interface. Le parseur par mot-clé (ADR-009)
disparaît (ADR-061).

## Schéma (draft-07, sans `minimum` ni `maximum`)
Requis : `verdict`, `summary`, `blocking`.
- `verdict` : enum `APPROVED` | `CHANGES_REQUESTED`
- `summary` : chaîne
- `blocking[]` : `text` (chaîne), `location` (chaîne, optionnelle),
  `confidence` (entier) ; requis : `text`, `confidence`
- `suggestions[]` : chaînes, optionnel

## Lecture du verdict (fonction pure, testable sans provider)
`lire_verdict(structured, seuil) -> tuple[bool, str]` — `(approuvé, raison)` :
- `structured is None`, champ requis absent, `verdict` hors enum, `confidence`
  hors de 0–100 → refus, raison = la cause.
- `CHANGES_REQUESTED` et au moins une remarque `confidence >= seuil` → refus.
- `CHANGES_REQUESTED` et toutes les remarques sous le seuil → approuvé avec
  remarques (règle du ticket-574 ; seuil 0 = filtre éteint, donc refus).
- `CHANGES_REQUESTED` sans aucune remarque → refus, raison = `summary`.
- `APPROVED` avec une remarque `>= seuil` → refus : contradiction.
- Seuil : `reviewer_confidence_threshold`, inchangé (80).

`rendre_revue(structured) -> str` : le Markdown rendu pour le codeur et l'écran,
première ligne = verdict retenu, puis les remarques (`text`, `location`,
`confidence`), puis `summary`. Le retour au codeur (`_truncate_objection`,
ticket-474 et 599) lit ce texte.

## À faire
- `pipeline_stages.py` : le reviewer passe son schéma à `AgentRunner.run` ;
  `lire_verdict` remplace `_read_reviewer_verdict`.
- `AGENT_DONE` du reviewer porte `data["verdict"]` (`APPROVED` ou
  `CHANGES_REQUESTED`, **après** le seuil) en plus de `content` rendu.
- Retirer `_parse_reviewer_verdict`, `_verdict_line`, `_read_reviewer_verdict`
  et `services/reviewer_confidence.py`. Réécrire, sans les perdre,
  `test_confiance_reviewer.py`, `test_objection_du_reviewer.py` et la section
  `_parse_reviewer_verdict` de `test_orchestrator.py` sur `lire_verdict`.
- `agents/prompts/reviewer.md` : retirer le format de réponse (verdict en
  première ligne, `[confiance: NN]`) ; dire ce que `confidence` mesure (la
  probabilité que le problème soit réel) et qu'une remarque sous le seuil ne bloque pas.
- `memory/decisions.md` : amender ADR-009 (renvoi à ADR-061, parseur retiré),
  **en restant sous 160 mots** — condenser l'historique des amendements.
- Ne **pas** toucher à `contraintes.md` : la règle de remplacement est sous
  `## Proposées`, un humain l'accepte et retire l'ancienne (ADR-055).

## Critères d'acceptation
- [ ] `lire_verdict` couvre les sept cas ci-dessus, un test chacun, dont `APPROVED` + remarque au-dessus du seuil → refus et `structured is None` → refus
- [ ] Une réponse reviewer hors schéma ou absente refuse sans lire le texte : un test fournit un `content` « APPROVED » et `structured=None`, et attend un refus
- [ ] `AGENT_DONE` du reviewer porte `verdict`, et un test vérifie qu'un `CHANGES_REQUESTED` sous le seuil donne `APPROVED`
- [ ] `grep -r "_parse_reviewer_verdict\|reviewer_confidence" backend/src` ne trouve plus rien
- [ ] Les tests réécrits conservent les scénarios des tickets 122, 298, 474 et 574 sous leur forme structurée
- [ ] `agents/prompts/reviewer.md` ne demande plus de verdict en première ligne, et un test le vérifie
- [ ] ADR-009 renvoie à ADR-061 et reste sous 160 mots (`test_consignes_coherentes.py` passe)

## Ce que ça ne fait pas
- Ne touche pas au frontend : ticket-615 (le `content` rendu garde le verdict en première ligne, l'interface actuelle continue de fonctionner d'ici là).
- Ne change ni le modèle ni le nombre de tours du reviewer.
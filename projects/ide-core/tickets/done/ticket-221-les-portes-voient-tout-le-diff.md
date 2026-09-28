---
id: ticket-221
title: "L'audit sécurité et le validateur voient tout le diff d'une branche reprise"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: ["ticket-208"]
estimated_days: 0.5
created: 2026-09-28
---

# ticket-221 — Les portes voient tout le diff

## Objectif

Le diff remis à l'audit sécurité et au validateur n'est plus coupé avant la fin sur un ticket de taille ordinaire.

## Contexte

Depuis le ticket-208, les trois portes reçoivent tout ce que la branche ajoute à sa base. Or l'audit coupait à 16 000 caractères et le validateur à 8 000. Sur le ticket-213 (environ 700 lignes de diff), le validateur a refusé en déclarant la plupart des critères « non vérifiables à partir du diff ». Côté sécurité, la fin d'un gros diff passait sans aucun audit.

## Solution

Les deux services ont désormais la même borne, 120 000 caractères (environ 30 000 tokens), bien en deçà de la fenêtre de Haiku comme de qwen3-coder. Le prompt du validateur indique cette nouvelle borne.

## Critères d'acceptation

- [x] Un test : un diff de 70 000 caractères arrive entier à l'audit sécurité
- [x] Un test : le même diff arrive entier au validateur
- [x] `agents/prompts/validateur.md` annonce la borne de 120 000 caractères
- [x] `uv run pytest` passe

## Ce que ça ne fait pas

Au-delà de 120 000 caractères, la coupe demeure. Un ticket de cette taille se découpe (skill `new-ticket`).

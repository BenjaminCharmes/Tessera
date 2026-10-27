---
agent: codeur
created: 2026-10-24
depends_on: []
estimated_days: 0.5
id: ticket-575
plan: true
pr_number: 697
priority: medium
status: done
title: A system prompt too long for a Windows command line goes to the SDK through
  a file
type: fix
---

# ticket-575 — Un long prompt système passe par un fichier

## Objectif
Qu'un agent démarre même quand son prompt système dépasse la limite d'une
ligne de commande Windows.

## Contexte
Veille du 24/10 : la documentation de l'Agent SDK Python indique qu'un prompt
système passé en chaîne échoue au lancement du processus sous Windows au-delà
d'environ 32 Ko, et propose de le passer par fichier. Le prompt d'un rôle
réunit son fichier de `agents/prompts/`, `contraintes.md` (environ 10 Ko) et le
CLAUDE.md du projet : il s'en approche. `_build_options`
(`services/providers/agent_sdk.py`) passe toujours `system_prompt=system` en
chaîne, sans garde.

## Solution proposée
Au-delà d'un seuil (24 Ko, avec de la marge), le prompt part par fichier,
sous la forme que le SDK épinglé (0.2.159) accepte. Le tour de plan vérifie
cette forme dans le paquet installé. Le fichier temporaire est créé hors du
dépôt du projet et supprimé à la fin de l'appel.

## Critères d'acceptation
- [ ] Un test montre qu'un prompt de 40 Ko est passé au SDK par fichier, et qu'un prompt de 2 Ko reste en chaîne
- [ ] Un test montre que le fichier temporaire n'est pas dans le dossier du projet et qu'il est supprimé après l'appel, y compris quand l'appel lève une exception
- [ ] Le seuil est une constante nommée de `services/providers/agent_sdk.py`

## Ce que ça ne fait pas
- Ne raccourcit aucun prompt.
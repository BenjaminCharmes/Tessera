---
agent: codeur
created: 2026-11-02
depends_on: []
estimated_days: 1
id: ticket-731
pr_number: null
priority: medium
status: done
title: The security audit knows what the ticket leaves to the next one
type: feat
---

# ticket-731 — L'audit sécurité sait ce que le ticket laisse au suivant

## Objectif

Qu'un blocage de l'audit sur une faille annoncée pour un ticket suivant se lise et se
tranche vite, et que le découpage ne crée plus ce cas : sans assouplir la porte (ADR-039).

## Contexte

Signalé par la session Curio le 02/11 (run 20144514) : le ticket-074 de Curio rend les
cartes propres à chaque joueur et dit en toutes lettres que `/api/progress` et
`/api/stats` relèvent du ticket-075, qui le suit dans la file. L'audit a rendu BLOCK
(CRITICAL/HIGH) sur ces deux routes ; la file s'est arrêtée ; la session a relu et mergé à
la main.

L'audit ne reçoit que le diff : `SecurityAuditor.audit(code_diff, project_path)`
(`services/security_auditor.py`), appelé par `run_security_audit`
(`services/pipeline_controles.py`). Il ignore le ticket et la file.

On **n'assouplit pas** la porte : Curio merge sur `main` sans CI (autonomie `merge`) ; une
faille laissée au ticket suivant serait sur `main` jusqu'à lui, et pour de bon s'il échoue.

## Solution proposée

1. L'audit reçoit, en plus du diff : la section « Ce que ça ne fait pas » du ticket, et
   l'id et le titre des tickets qui le suivent dans la file. Son prompt
   (`agents/prompts/securite.md`) lui demande de **citer** dans le constat le ticket qui
   annonce la correction (« annoncée par ticket-075 ») ; le verdict ne change pas : une
   faille CRITICAL ou HIGH bloque toujours.
2. Le prompt du planificateur (`agents/prompts/planificateur.md`) interdit un découpage qui
   laisse une faille atteignable entre deux tickets : la protection va dans le même ticket,
   ou dans un ticket placé avant.

## Critères d'acceptation

- [ ] Un test : `SecurityAuditor.audit` met dans le message de l'agent la section « Ce que
      ça ne fait pas » du ticket et les tickets suivants de la file (id et titre)
- [ ] Un test : hors file, le message ne porte que le ticket, sans tickets suivants
- [ ] Un test : une faille CRITICAL annoncée par un ticket suivant donne toujours `BLOCK`
- [ ] `agents/prompts/securite.md` demande de citer le ticket qui annonce la correction
- [ ] `agents/prompts/planificateur.md` interdit de laisser une faille atteignable entre
      deux tickets

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le texte du ticket entre dans le prompt de l'audit : borné (2 000 signes), et l'audit reste
jugé par sa sortie structurée (ADR-061), jamais par ce texte.
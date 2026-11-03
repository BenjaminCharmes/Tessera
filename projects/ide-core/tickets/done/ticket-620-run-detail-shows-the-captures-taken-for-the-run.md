---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-618
id: ticket-620
pr_number: 735
priority: low
status: done
title: The run detail shows the captures taken for that run
type: feat
---

# ticket-620 — Voir les captures d'un run

## Objectif
Qu'un humain voie, dans le détail d'un run de l'historique, les images prises
par l'étape de capture. Les captures ne vont pas dans la PR (ADR-062) : sans cet
écran, elles existeraient sans qu'on puisse les ouvrir.

## À faire
- Un endpoint de liste des images du run, sous `captures/<projet>/<ticket>/`
  (le service d'une image existe, étendu par ticket-618) ; liste vide si le run
  n'a rien capturé.
- Dans `HistoriqueView/DetailDuRun`, une section « Captures » : une vignette par
  image, groupée par écran, légendée largeur et thème, qui s'ouvre en grand.
  Section absente si la liste est vide. Composants existants, jetons du
  `@theme` seulement (ADR-026).

## Critères d'acceptation
- [ ] Un run sans capture n'affiche aucune section « Captures »
- [ ] Un run avec captures affiche une vignette par image, avec largeur et thème en légende
- [ ] L'endpoint refuse un nom de ticket ou de fichier qui sort du dossier du run
- [ ] Un test frontend et un test backend

## Ce que ça ne fait pas
- N'affiche pas les captures manuelles de ticket-432 ailleurs que là où elles sont déjà.
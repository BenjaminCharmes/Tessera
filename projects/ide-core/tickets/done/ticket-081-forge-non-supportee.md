---
id: ticket-081
title: "Ne proposer la pull request que là où elle marche"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-080]
estimated_days: 1
created: 2026-09-18
---

# ticket-081 — La PR ne se propose que là où elle marche

## Pourquoi

Décision prise à l'usage : **pas de couche forge**. Sur les dépôts pro — GitLab
auto-hébergé chez l'un, Azure DevOps chez l'autre — les accès sont
spécifiques, et le push se fait à la main une fois le travail terminé.

Or le bouton « Pousser et ouvrir la PR » s'affichait sur **tout** ticket ayant
une branche, sans regarder l'hébergeur. Sur un de ces dépôts, il aurait :

1. **poussé la branche** — ce qui marche, c'est du git ordinaire,
2. puis échoué sur `api.github.com`, qui ne connaît pas ce dépôt.

Autrement dit, il poussait sans rien demander avant d'échouer. Sur le dépôt d'un
client, pousser est précisément la décision qui ne se prend pas par mégarde —
c'est le corollaire d'ADR-022.

## Décision

La capacité est calculée **côté serveur**, à partir du remote, et remontée dans
l'activité du ticket. L'interface ne devine pas : elle affiche ce que le backend
déclare possible.

Hors GitHub, l'IDE dit **où** est le dépôt — « Dépôt hébergé sur Azure
DevOps » — plutôt que « pas sur GitHub », qui n'aide personne à décider. Et il
rappelle que la branche du ticket est prête, à pousser quand on le décide.

## Vérifié

933 tests backend, mypy sur 65 fichiers, 375 tests frontend, 5 flows E2E,
`npm run build`.

---
id: ticket-673
title: "A product's agents are drawn in its room from the activity file alone"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-671, ticket-672]
estimated_days: 1
created: 2026-10-29
---

# ticket-673 — Les agents d'un produit se dessinent depuis son fichier d'activité

## Objectif
Qu'un agent déclaré par un produit apparaisse dans la salle de son app, et
qu'une salle sans donnée ne montre personne.

## Contexte
ADR-064 et la spec `docs/superpowers/specs/2026-10-29-salle-des-serveurs-design.md`.
ticket-671 fournit `GET /services/running/activite`, ticket-672 les salles. Un
sprite rend un état réel (ADR-058) : ici, l'entrée du fichier, pas une supposition.

## Solution proposée
- `useActiviteProduit()` relève la route toutes les 5 s, comme `useAppsEnCours`.
- `ActiviteDeService` et `AgentDeProduit` dans `frontend/src/types/api.ts`.
- Un bureau et un agent par entrée, sprites en SVG sous `design/bureau/`, tons en
  jetons `--sprite-*`. `actif` anime l'agent, `repos` le montre posé.
- Le nom et le libellé se rendent comme texte, jamais comme balisage.

## Critères d'acceptation
- [ ] Une salle dont l'app a une activité rend un agent par entrée, avec son `nom`, et le `libelle` quand il existe
- [ ] Un agent `actif` et un agent `repos` se distinguent au rendu, avec un test
- [ ] Test « sans donnée, rien » : réponse vide, erreur réseau ou service absent de la réponse, la salle ne contient aucun agent
- [ ] Un `libelle` contenant du balisage s'affiche en texte, avec un test
- [ ] Sous `prefers-reduced-motion`, aucun agent ne s'anime
- [ ] Les tons des sprites sont des jetons `--sprite-*` du `@theme`, jamais une famille CSS brute, et le test existant qui le verrouille passe

## Ce que ça ne fait pas
- N'écrit pas les émetteurs : chaque produit tient le sien (spec, section 6).
- Ne devine rien d'un produit sans fichier d'activité : sa salle reste sans agents.

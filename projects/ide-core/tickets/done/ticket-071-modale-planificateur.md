---
id: ticket-071
title: "Ne plus jeter le résultat du planificateur"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-070]
estimated_days: 1
created: 2026-09-17
---

# ticket-071 — Ne plus jeter le résultat du planificateur

## Ce qui a été observé

Trois défauts signalés à l'usage, sur la même fenêtre.

1. L'attente n'était signalée que par un spinner de douze pixels dans le
   bouton — rien ne disait ce qui se passait ni combien de temps ça prendrait.
2. Un clic à côté de la fenêtre la fermait, y compris pendant l'appel.
3. **Les brouillons s'affichaient puis disparaissaient au bout de quelques
   secondes**, et la fenêtre revenait à son état initial.

## La cause du troisième

`TicketList` faisait un `return` anticipé sur `loading` :

```tsx
if (loading) { return <SkeletonList /> }
```

Ce retour ne remplaçait pas la liste : il démontait **tout le sous-arbre**, et
les modales y étaient rendues. Au premier rafraîchissement des tickets — un
événement WebSocket, un `refresh()`, le polling — la modale disparaissait avec
son état, donc avec les brouillons.

Le résultat du planificateur est un appel LLM facturé. Le perdre parce qu'un
autre composant se recharge n'est pas une gêne d'affichage.

## Décision

**Le chargement et l'erreur remplacent la liste, pas le composant.** Ils sont
rendus *dans* la zone qui défile ; la structure qui accueille les modales ne
bouge plus.

**La fenêtre ne se ferme plus tant qu'il y a quelque chose à perdre** — pendant
l'appel, et tant que des brouillons sont à l'écran. Ni au clic extérieur, ni à
`Échap`. On ferme depuis un état où il n'y a rien à jeter.

**L'attente s'explique** : ce que fait le planificateur, l'ordre de grandeur, et
le fait que la fenêtre tiendra.

## En marge

Le verrou de cohérence visuelle laissait passer les opérateurs mathématiques :
`≡` et `+`, utilisés comme affordances, n'étaient dans aucune de ses plages. La
plage `U+2200–U+22FF` est ajoutée, et les deux boutons passent aux icônes.

## Vérifié

335 tests frontend, `npm run typecheck`, 5 flows E2E, `npm run build`.

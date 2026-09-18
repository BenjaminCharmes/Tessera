---
id: ticket-092
title: "Documenter par lot, en modifications ciblées"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-091]
estimated_days: 2
created: 2026-09-18
---

# ticket-092 — La documentation

## Ce qui a été trouvé

### Une mine

```python
_DOC_MAX_CHARS = 8_000     # ce que doc-updater voyait
_MAX_TOKENS    = 2048      # ~8 000 caractères qu'il pouvait écrire
```

Son prompt demandait le « contenu **complet** mis à jour », et `_write_files`
faisait un `write_text` qui écrase. `README.md` fait 24 098 caractères.

Activer `doc_updater_enabled` sur ce projet aurait remplacé un README de 24 ko
par au plus 8 ko, au premier run approuvé, sans erreur. L'agent ne pouvait pas
faire autrement : le contrat le lui imposait.

### La doc fonctionnelle n'était couverte par personne

`docs/guide-utilisateur.md` existe (3 284 mots) et n'apparaît dans le prompt
d'aucun agent. Elle a été écrite à la main et n'était mise à jour par rien.

### Le rythme

`run_doc_update` tournait à **chaque** run approuvé. Trois tickets sur une même
feature produisent trois réécritures partielles du même fichier.

## Critères d'acceptation

- [x] Les agents rendent des **modifications**, jamais un fichier entier
- [x] Un ancien texte absent, présent deux fois, ou dont le remplacement
      amputerait le fichier de moitié, rejette **tout le lot**
- [x] Une seule modification en échec n'écrit rien du tout — une doc à moitié
      à jour est pire qu'une doc en retard : elle a l'air à jour
- [x] Aucune écriture hors `README.md` et `docs/`
- [x] Deux agents : `doc-technique` et `doc-fonctionnelle`
- [x] Un appel par agent et par **lot** : dix tickets font deux appels
- [x] Un run unique ne déclenche rien — c'est un aller-retour rapide
- [x] Un lot sans ticket nouveau ne coûte aucun appel
- [x] Un agent qui se trompe n'empêche pas l'autre d'avoir raison
- [x] Une doc qui échoue ne casse pas la file
- [x] ADR-035 écrite

## Choix d'économie

Les agents reçoivent les **tickets**, pas les diffs. Un diff dit ce qui a bougé
ligne à ligne ; un ticket dit ce que le produit fait de plus. C'est la seconde
chose qu'on documente, et elle tient en dix fois moins de tokens.

## Ce que ça ne fait pas

`doc_updater` et son stage par run existent encore, désactivés partout. Les
retirer touche à `pipeline_stages`, `orchestrator` et quatre fichiers de tests
pour aucun gain de comportement : c'est un nettoyage, pas ce ticket.

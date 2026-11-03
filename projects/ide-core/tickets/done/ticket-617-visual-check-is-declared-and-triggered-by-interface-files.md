---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-616
id: ticket-617
pr_number: 730
priority: medium
status: done
title: A project declares its visual check and the interface files that trigger it
type: feat
---

# ticket-617 — Déclarer le contrôle visuel et ce qui le déclenche

## Objectif
Lire dans `agents.json` ce que l'ADR-062 demande, et décider, depuis la liste
des fichiers d'un diff, si un contrôle est dû. Que du pur : aucun processus,
aucune capture.

## Forme déclarée
```json
"pipeline": { "controle_visuel": "joindre" },
"captures": {
  "url": "http://localhost:{port}",
  "ecrans": [ { "nom": "accueil", "chemin": "/" } ],
  "largeurs": [390, 1024, 1440],
  "interface": ["app/", "components/", ".css"],
  "demarrage": { "commande": "corepack pnpm@10 exec next dev -p {port}", "delai_s": 120 }
}
```
`interface` : une entrée qui commence par `.` est une extension, sinon un
préfixe de chemin (comme `chaines_de_test.py`). Jamais de valeur par défaut :
sans `interface`, aucun diff ne déclenche.

## À faire
- Un module (par exemple `controle_visuel.py`) : `lire_le_controle(project_path)`
  renvoie le mode (`joindre`, `relire`) et la configuration, ou `None` ;
  `controle_du(chemins, config) -> bool`.
- `{port}` n'est substitué que par l'étape de run (ticket-618) ; la capture
  manuelle existante garde son `url` tel quel.
- `demarrage.delai_s` : défaut 120, plafond 300.

## Critères d'acceptation
- [ ] Sans `pipeline.controle_visuel`, `lire_le_controle` renvoie `None`, même si `captures` existe
- [ ] Une valeur autre que `joindre` ou `relire`, ou un `demarrage` sans `{port}` dans `commande`, renvoie `None` (la porte ne se devine pas)
- [ ] `controle_du` est vrai pour un chemin sous un préfixe déclaré ou à une extension déclarée, faux sinon et faux si `interface` est absent
- [ ] La capture manuelle (`POST .../captures`) se comporte comme avant sur un `agents.json` sans les nouveaux champs
- [ ] Un test par fonction publique

## Ce que ça ne fait pas
- Ne démarre rien et ne capture rien ; ne modifie aucun `agents.json` de projet
  (fichier protégé, ADR-027 : l'humain y ajoute la déclaration).
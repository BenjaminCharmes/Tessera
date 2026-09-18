---
id: ticket-080
title: "Choisir le modèle d'un agent, projet par projet"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-079]
estimated_days: 1
created: 2026-09-18
---

# ticket-080 — Le modèle se choisit par projet

## Pourquoi

Question posée à l'usage : « on parle de coûts par modèle, mais on ne choisit
le modèle nulle part ». C'était juste. Le modèle vivait dans le `agents.json` de
chaque projet, avec un repli sur Sonnet, et **aucune interface ne permettait de
le changer** — il fallait éditer le JSON à la main.

Afficher une ventilation par modèle sans pouvoir en choisir un était bancal.

## Décision

**Le réglage vit au niveau du projet**, pas du registre d'agents. Le même
`codeur` mérite un modèle lourd sur un backend métier et un modèle léger sur un
script personnel : c'est une propriété du projet, et le registre est global.

Le sélecteur apparaît néanmoins **dans le détail de l'agent**, là où on le
regarde déjà — et il se tait si le projet ne déclare pas cet agent : il n'y a
alors rien à régler.

**Seuls les modèles que l'application sait tarifer sont proposés.** En choisir
un hors grille fausserait la ventilation des dépenses, qui est justement ce sur
quoi on s'appuie pour décider où descendre en gamme. Le backend refuse aussi un
modèle inconnu : une liste d'options n'est pas une garantie.

Le `agents.json` est réécrit en préservant le reste — il porte aussi le mode des
artefacts, la racine git et la configuration du pipeline.

## Ce que ça ouvre

Plusieurs agents ne font que du texte→JSON : le validateur vérifie des critères,
l'auditeur cherche des motifs, le planificateur découpe. Ce sont de bons
candidats pour un modèle moins cher. Le codeur et le reviewer, non. La
ventilation par agent dit désormais où appuyer.

## Vérifié

923 tests backend, mypy sur 65 fichiers, 373 tests frontend, 5 flows E2E,
`npm run build`.

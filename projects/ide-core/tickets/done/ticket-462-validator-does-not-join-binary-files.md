---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.25
id: ticket-462
pr_number: 480
priority: high
status: done
title: The validator is told a cited binary file exists instead of receiving its bytes
type: fix
---

# ticket-462 — Un fichier binaire cité n'est pas joint comme du texte

## Objectif

Un critère qui cite une image ou tout fichier binaire donne au validateur
une ligne qui atteste son existence et sa taille, pas ses octets lus comme
du texte.

## Contexte

make-your-call, 15/10, 15:28:55 : « [ticket-014] validateur : fichiers cités
joints : hero-couple.png (tronqué) », puis « CHANGES_REQUESTED — Réponse du
validateur non parseable ». `_read_entry` dans
`backend/src/tessera/services/validator_cited_files.py` lit tout fichier
trouvé en texte (`errors="replace"`) : une image PNG devient des milliers de
caractères de remplacement, consomme le budget de 20 000 caractères et
noie le modèle local, dont la réponse n'est plus lisible.

## Solution proposée

Avant la lecture, détecter un fichier binaire (extension d'image, de police,
d'archive, ou octet nul dans les premiers 8 Ko). Pour un tel fichier,
l'entrée devient `### <ref>\n*(fichier binaire présent, N octets)*` : le
critère « l'image existe » reste vérifiable, sans joindre son contenu.

## Critères d'acceptation

- [ ] Un test cite un `.png` présent et vérifie que la section contient
      « fichier binaire présent » et sa taille, sans ses octets
- [ ] Un test vérifie qu'un fichier binaire sans extension connue (octet nul
      au début) est traité de même
- [ ] Un test vérifie qu'un fichier texte est toujours joint en entier
- [ ] Le rapport (`CitedFilesReport`) range le fichier binaire dans
      `joined`, pas dans `truncated`
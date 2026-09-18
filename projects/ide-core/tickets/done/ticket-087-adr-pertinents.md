---
id: ticket-087
title: "Chaque agent ne reçoit que les ADR qui le contraignent"
type: refactor
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-086]
estimated_days: 1
created: 2026-09-18
---

# ticket-087 — Des ADR pertinents, pas tous les ADR

## Pourquoi

Mesure avant : `decisions.md` pesait 3 686 mots, soit ~5 160 tokens, injectés
dans **chaque** appel d'agent — jusqu'à dix-huit par ticket, donc ~93 000
tokens d'ADR par ticket. Et le fichier grossit à chaque décision : douze ADR
sur trente et un dépassaient déjà le budget de 160 mots, dont trois écrits le
jour même.

Le coût n'est pas le vrai problème. C'est la **dilution** : un codeur recevait
la palette de couleurs (ADR-026), le choix de Tauri contre Electron (ADR-004)
et celui du gestionnaire de paquets Python (ADR-005), au milieu des quelques
contraintes qu'il doit réellement respecter. Les règles qui comptent se
noyaient dans celles qui ne le concernent pas.

## Critères d'acceptation

- [x] Un ADR peut porter `**Portée** : rôle, rôle`
- [x] Sans portée, il part à tous — le défaut protège
- [x] Le filtrage s'applique au moment de rédiger le prompt, seul endroit où
      le rôle est connu
- [x] Un contexte sans section de décisions traverse intact
- [x] Un test vérifie que le filtre est réellement branché sur le prompt
- [x] Un test **refuse** une portée posée sur une contrainte de comportement,
      par liste explicite
- [x] Un test vérifie que le vrai fichier reste découpable : s'il cessait de
      l'être, tous les agents perdraient toutes leurs contraintes d'un coup,
      sans erreur
- [x] Le skill `write-adr` enseigne le champ et la question qui le décide
- [x] ADR-032 écrite

## Résultat

| Rôle | Réduction |
|---|---|
| architect | 5 % |
| codeur | 10 % |
| reviewer | 14 % |
| tous les autres | **30 %** |

Les agents qui gardent le plus sont ceux qui ont le plus besoin des ADR de
conception. C'est le résultat voulu, pas un effet de bord.

## Ce que ça ne fait pas

Le budget de 160 mots reste à tenir : un ADR sans portée — donc toute
contrainte — part toujours dans les dix-huit appels. Douze ADR le dépassent
encore.

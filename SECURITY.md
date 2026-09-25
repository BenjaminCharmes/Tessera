# Signaler une faille

Merci de **ne pas ouvrir d'issue publique** pour une vulnérabilité : une issue
est lisible par tout le monde, y compris par ceux qui l'exploiteraient avant
qu'un correctif existe.

Utilisez l'onglet **Security → Report a vulnerability** du dépôt, qui ouvre un
signalement privé visible du seul mainteneur.

## Ce qui mérite un signalement

Tessera fait tourner des agents qui **écrivent sur le disque et exécutent des
commandes** dans les dépôts de ses utilisateurs — parfois ceux de leurs
clients. Les sujets sensibles sont donc :

- un contournement du périmètre d'écriture : un agent qui écrit hors de la
  racine de son projet (ADR-031) ;
- un contournement du garde-fou git : un agent qui commite, pousse ou merge
  alors que le hook doit le refuser (ADR-027) ;
- une fuite d'artefacts : des `tickets/`, `memory/` ou `CLAUDE.md` qui
  partent dans le dépôt d'un utilisateur alors que son projet les déclare
  locaux (ADR-021, ADR-023) ;
- une exposition de l'API : `STATIC_TOKEN` contourné — sur une route HTTP
  comme sur une WebSocket —, ou un endpoint qui lit ou écrit hors du
  workspace.

## Ce qui n'en est pas

Ces limites sont **connues et documentées**, pas des failles :

- **L'API est ouverte par défaut.** `STATIC_TOKEN` vide, toute requête est
  acceptée : Tessera se sert en local, sur `127.0.0.1`, et c'est ce que font
  `make dev` et `make run`. Il n'y a ni comptes ni multi-utilisateur, c'est
  hors périmètre.
- **Le token d'une WebSocket passe dans l'URL** (`?token=`), donc dans les
  logs d'accès : un navigateur ne peut pas poser d'en-tête sur
  `new WebSocket`. Qui lit ces logs lit le token ; c'est documenté dans
  `docs/configuration.md`.
- **Le contrôle d'écriture sur `Bash` attrape une erreur, pas une évasion.**
  `python -c "open('../x','w')"` passe, et ADR-031 le dit : refuser tout ce
  qui ne se lit pas avec certitude priverait l'agent de son moyen de vérifier
  son travail.
- **Du code bloqué par l'audit de sécurité entre dans l'historique**, confiné
  à la branche de son ticket et jamais sur `main` (ADR-018).

## Délai

Projet personnel, maintenu sur du temps libre : comptez quelques jours pour un
premier retour. Si une faille est confirmée, vous serez tenu au courant du
correctif et crédité si vous le souhaitez.

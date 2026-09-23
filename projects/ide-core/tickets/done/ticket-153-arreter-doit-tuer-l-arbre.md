---
id: ticket-153
title: "Arrêter doit tuer l'arbre, et relancer ne doit pas doubler"
type: fix
status: done
pr_number: 171
priority: high
agent: codeur
depends_on: ["ticket-151"]
estimated_days: 1
created: 2026-09-23
---

# ticket-153 — L'arbre de processus, et le double lancement

## Objectif

Qu'« Arrêter » libère vraiment les ports, et que « Lancer » ne crée pas un
second exemplaire de ce qui tourne déjà.

## Contexte

**Deux défauts trouvés en éprouvant le cycle complet.**

**`stop` ne tue que le parent.** `POST /services/stop` a répondu
`{"arretes": 2}` pendant que **douze processus** de `fluentdb` continuaient de
tourner. `npm run dev` lance `concurrently`, qui lance deux sous-processus :
`terminate()` frappe le premier maillon, et les descendants survivent avec
leurs ports.

Le job object de ticket-150 ne couvre pas ce cas : il tue à la **fermeture du
job**, c'est-à-dire à la mort du backend, pas sur un arrêt individuel.

**`start` sur un service déjà en cours le double.** Rien ne l'empêche : un
second processus démarre, et `GET /services` n'en montre qu'un seul, parce
qu'il indexe par nom dans un dictionnaire — les doublons s'écrasent. Deux
lancements de suite ont laissé douze processus là où trois suffisent.

L'interface protège aujourd'hui de ce cas, puisque le bouton affiche
« Arrêter » quand ça tourne. Mais une protection qui ne vit que dans
l'affichage n'en est pas une : deux clics rapides, ou un appel direct, passent
au travers.

## Solution proposée

**Un job object par service**, et non plus seulement un global. Le fermer tue
tout l'arbre d'un coup, ce que `terminate()` ne sait pas faire. Le job global
de ticket-150 reste, pour le cas où le backend est tué.

Hors Windows, `os.killpg` sur le groupe de processus joue le même rôle, à
condition de lancer avec `start_new_session`. À défaut, l'arrêt reste partiel
et le dit.

**`start` refuse un service déjà en cours**, avec un message qui nomme le
service et son pid. Relancer demande d'arrêter d'abord — c'est explicite, et
ça évite d'inventer une sémantique de redémarrage silencieux.

**`GET /services` cesse d'indexer par nom** : deux entrées de même nom ne
doivent plus s'écraser mutuellement, faute de quoi l'écran cache ce qui tourne.

## Critères d'acceptation

- [ ] Un test vérifie qu'après `stop`, aucun descendant du service ne survit
- [ ] Un test vérifie qu'un `start` sur un service en cours répond 409 en
      nommant le service
- [ ] Un test vérifie qu'aucun second processus n'est créé dans ce cas
- [ ] Un test vérifie que deux services de même nom ne s'écrasent pas dans la
      liste
- [ ] `uv run pytest` et `uv run mypy src/` passent
- [ ] Vérifié en vrai : lancer `fluentdb`, arrêter, constater zéro processus
      restant

## Dépendances

ticket-151.

## Estimation

1 jour.

## Risques

Tuer un arbre de processus est plus violent que terminer un processus : un
service qui écrit un fichier au moment de l'arrêt peut le laisser à moitié
écrit. C'est le prix de ports qui se libèrent — et la même violence que celle
qu'un Ctrl-C brutal produirait.

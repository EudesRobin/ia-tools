---
name: clean-android-tv
description: Réduire la consommation mémoire d'un téléviseur Android TV ou Google TV par adb, et le rendre plus réactif — relevé du stockage, de la mémoire et des paquets, désactivation réversible des applications préinstallées inutilisées, réglages de fluidité. À utiliser quand l'utilisateur demande d'optimiser, d'accélérer ou de nettoyer sa TV Android, se plaint qu'elle rame ou qu'elle est devenue lente, veut désactiver des applications préinstallées, ou veut connecter sa TV en adb.
allowed-tools:
  - Bash(adb:*)
  - Read
  - Write
---

# Accélérer un téléviseur Android TV par adb

Rendre un téléviseur Android TV ou Google TV plus réactif, depuis un poste du
même réseau local, par le pont de débogage adb.

L'objectif est de **libérer de la mémoire vive** en ne laissant tourner que les
applications réellement utilisées : les applications préinstallées inutilisées
sont désactivées, le travail de fond des applications conservées est réduit, et
quelques réglages raccourcissent les temps de réponse de l'interface. Toutes les
opérations prescrites ici s'exécutent **sans accès root** et sont
**réversibles**.

**Lire d'abord**, dans le dossier de la skill :
[reference-adb.md](reference-adb.md) pour les commandes,
[paquets.md](paquets.md) pour le classement des applications préinstallées et le
recensement des paquets critiques, auxquels il ne faut jamais toucher.

## Suivi de progression — impératif

Cette skill est une tâche en huit phases : la règle de suivi des tâches
s'applique. Créer la liste ci-dessous **avant la phase 1**, et la ré-afficher en
entier à chaque changement d'état, avec les marqueurs `[ ]` non commencée, `[~]`
en cours, `[x]` terminée, `[-]` abandonnée. Plusieurs `[~]` simultanées
seulement si les étapes sont réellement menées en parallèle. Quand la session
expose son propre outil de liste de tâches, c'est cet outil qui est employé et
qui fait l'affichage ; sinon le bloc est écrit dans la réponse. Aucun des deux
suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : vérifier adb sur le poste et le débogage sur le téléviseur
- [ ] Phase 2 : connecter le téléviseur et confirmer l'autorisation
- [ ] Phase 3 : relever l'état initial — modèle, stockage, mémoire, paquets
- [ ] Phase 4 : consigner l'inventaire restaurable dans un journal daté
- [ ] Phase 5 : classer les paquets et soumettre le lot de désactivations
- [ ] Phase 6 : appliquer le lot par groupes de risque homogène, après accord
- [ ] Phase 7 : redémarrer et vérifier que le téléviseur reste pilotable
- [ ] Phase 8 : appliquer les derniers leviers, puis refermer l'accès

La phase 7 est un contrôle : elle ne passe à `[x]` qu'après un redémarrage réel
suivi d'une reconnexion adb et de la vérification du lanceur, en nommant le
résultat (`[x] Phase 7 : redémarrer — lanceur et télécommande opérationnels`).

## Prérequis (à vérifier, ne rien installer sans accord)

- **adb** sur le poste : `adb version`. Absent sous Windows →
  `winget install Google.PlatformTools`. L'installateur ajoute `platform-tools`
  au PATH, mais un terminal ouvert avant l'installation ne voit pas le PATH
  modifié : rouvrir le terminal.
- **Un seul adb sur le PATH.** Deux binaires de versions différentes rendent le
  client et le serveur adb incompatibles. Contrôler par `where.exe adb` et
  retirer l'entrée surnuméraire.
- **Débogage ADB activé sur le téléviseur**, poste et téléviseur sur le même
  réseau local. La procédure d'activation, et le cas des téléviseurs sans option
  de débogage réseau, sont dans [reference-adb.md](reference-adb.md).

## Instructions

1. **Vérifier les prérequis.** Contrôler `adb version` et l'unicité du binaire.
   Guider l'utilisateur pour activer les options pour les développeurs puis le
   débogage, et lui demander l'adresse IP du téléviseur. Ne jamais supposer que
   le débogage est déjà actif.
2. **Connecter.** `adb connect <IP_TV>:5555`, puis `adb devices -l`. Le
   téléviseur affiche une demande d'autorisation de clé RSA : la faire accepter.
   Ne pas enchaîner tant que l'état n'est pas `device`. En cas d'échec, sonder
   les ports avant toute hypothèse ([reference-adb.md](reference-adb.md)) : la
   sonde distingue un démon inactif d'un problème de réseau et, sur un refus
   explicite, met hors de cause un VPN installé sur le téléviseur. Ne pas
   demander de redémarrage à ce stade : le réglage de débogage n'y survit pas
   toujours. Si le démon n'écoute pas et qu'aucune option de débogage réseau
   n'existe dans les menus, mettre adbd en écoute réseau depuis un shell local
   sur le téléviseur — procédure dans le même document.
3. **Relever l'état initial.** Modèle, version d'Android, occupation de `/data`,
   pression mémoire, paquets installés, processus en fond. Annoncer le résultat
   avant toute modification : quand `/data` est occupé à plus de 85 %, c'est le
   stockage qui explique le ralentissement, et la désactivation d'applications
   n'y changera presque rien. Ne pas lire le classement de `dumpsys meminfo`
   comme une liste de coupables : vérifier l'état de chaque processus volumineux
   avant de l'incriminer, car un processus en cache ne coûte rien.
4. **Consigner l'inventaire restaurable.** Écrire un journal daté
   `android-tv-<AAAA-MM-JJ>.md`, hors du dépôt d'outils, contenant la sortie
   brute de `pm list packages -e` **avant** toute modification, l'état initial
   de la phase 3, et un tableau « paquet ou réglage / action / restauration ».
   Ce journal est la garantie de réversibilité : ne pas passer à la phase
   suivante sans qu'il soit écrit.
5. **Classer et proposer.** Classer chaque paquet selon
   [paquets.md](paquets.md). Soumettre un lot à l'utilisateur, une ligne par
   paquet, avec son rôle réel et ce que sa désactivation retire. Interroger
   l'utilisateur sur ses usages — diffusion Chromecast, assistant vocal, lecture
   de fichiers locaux, services de vidéo à la demande — plutôt que de les
   déduire. Ne jamais désactiver un paquet dont le rôle n'a pas été identifié :
   le signaler comme inconnu et le laisser activé.
6. **Appliquer.** Après accord explicite, par groupes de risque homogène.
   Employer `pm disable-user --user 0`, jamais `pm uninstall` sauf demande
   expresse. Contrôler l'interface après chaque groupe par
   `dumpsys window | grep mCurrentFocus`. Consigner chaque commande et sa
   commande inverse dans le journal, à mesure.
7. **Redémarrer et vérifier.** Avertir d'abord que l'accès adb sera perdu s'il
   repose sur `service.adb.tcp.port`, propriété qui ne survit pas au
   redémarrage. Lancer ensuite `adb reboot`, attendre, reconnecter, et contrôler
   que le lanceur répond et que la télécommande pilote l'interface. Toute
   anomalie → réactiver le dernier groupe depuis le journal et reprendre à la
   phase 5 avec un lot plus étroit. Ne pas enchaîner sur la phase 8 tant que ce
   contrôle n'est pas concluant.
8. **Finir.** Réglages de fluidité, vidage des caches, puis les leviers qui ne
   passent pas par la désactivation — travail de fond des applications
   conservées, composants isolés, mise à jour automatique du magasin, services
   de localisation ([reference-adb.md](reference-adb.md)). Écrire dans le
   journal la marche à suivre pour tout réactiver, y compris depuis les menus du
   téléviseur seul. Refermer l'accès adb et rappeler de couper le débogage.

## Règles

- **Réversibilité avant tout.** Aucune modification avant que le journal de la
  phase 4 soit écrit. Chaque action est consignée avec sa commande inverse.
- **Accord explicite** avant toute désactivation, tout effacement de données et
  tout redémarrage. Énumérer ce qui va changer plutôt que de le résumer par
  « nettoyage ».
- **Par groupes de risque homogène**, et non par nombre fixe de paquets. Un
  groupe réunit des paquets de même nature — lanceur et ses satellites, chaîne
  média, applications d'accompagnement du constructeur — de sorte qu'une
  anomalie désigne le groupe fautif. Un groupe qui touche au lanceur, à la
  méthode de saisie ou à la chaîne vidéo s'applique seul.
- **Désactiver, ne pas désinstaller.** `pm disable-user --user 0` se défait par
  `pm enable`. Réserver `pm uninstall -k --user 0` à une demande expresse, après
  avoir signalé qu'une mise à jour du système peut réinstaller le paquet.
- **Ne jamais toucher aux paquets critiques** recensés dans
  [paquets.md](paquets.md) — interface système, services Google Play,
  fournisseurs de contenu, méthode de saisie, moteur de rendu web, chaîne vidéo
  du constructeur.
- **Ne présenter aucun gain de performance sans mesure** fondée sur des relevés
  effectués dans des conditions comparables. Ne pas qualifier de « plus rapide »
  ce qui n'a pas été mesuré.
- **Sécurité.** Le débogage réseau ouvre le port 5555 sur le réseau local. Ne
  jamais proposer de rediriger ce port depuis la box Internet, et rappeler de
  couper le débogage en fin d'intervention.

## Limites

- **Sans root.** Les caches internes des applications, les partitions système et
  les paquets non désactivables restent hors d'atteinte. L'état d'un composant
  isolé ne se modifie que sur une application portant le flag `SYSTEM`.
- **Le gain est borné.** Un téléviseur limité par sa mémoire vive ou par un
  stockage saturé ne redevient pas fluide par la désactivation d'applications.
  Le dire, plutôt que de laisser croire à un gain.
- **Les identifiants de paquets varient** selon le constructeur et la version
  d'Android. [paquets.md](paquets.md) couvre l'ossature commune à Android TV et
  à Google TV, et donne l'exemple d'un téléviseur TCL et celui du NVIDIA Shield
  comme modèles de transposition ; un paquet propre à un autre constructeur se
  classe au cas par cas et reste activé tant qu'il n'est pas identifié.
- **Beaucoup de téléviseurs n'exposent pas d'option de débogage réseau** et
  n'offrent que « Débogage ADB ». La connexion réseau reste souvent possible :
  tenter `adb connect` avant de conclure. Le câble USB n'est pas un repli sur un
  téléviseur, car ses ports USB sont des ports hôtes. Si le démon n'écoute
  toujours pas, une application de la catégorie « ADB » installée sur le
  téléviseur peut fournir un shell en UID 2000, depuis lequel la propriété
  `service.adb.tcp.port` se définit à la main
  ([reference-adb.md](reference-adb.md)). Ce contournement échoue si la console
  de l'application ne tourne pas en UID 2000 ; il reste alors les menus du
  téléviseur.
- **Hors périmètre** : le root, l'installation d'applications tierces, et toute
  modification de la partition système.

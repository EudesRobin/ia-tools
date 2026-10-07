---
name: clean-android-tv
description: Réduire la consommation mémoire d'un téléviseur Android TV ou Google TV par adb, et le rendre plus réactif — relevé du stockage, de la mémoire et des paquets, désactivation réversible des applications préinstallées inutilisées, réglages de fluidité. À utiliser quand l'utilisateur demande d'optimiser, d'accélérer ou de nettoyer sa TV Android, se plaint qu'elle rame ou qu'elle est devenue lente, veut désactiver des applications préinstallées, veut connecter sa TV en adb, ou demande de vérifier qu'un nettoyage précédent est toujours en place.
allowed-tools:
  - Bash(adb:*)
  - Bash(arp:*)
  - Bash(where.exe:*)
  - Bash(python:*)
  - Read
  - Write
  - Edit
---

# Accélérer un téléviseur Android TV par adb

Rendre un téléviseur Android TV ou Google TV plus réactif, depuis un poste du
même réseau local, par le pont de débogage adb.

L'objectif est de **libérer de la mémoire vive** en ne laissant tourner que les
applications réellement utilisées : les applications préinstallées inutilisées
sont désactivées, l'activité en background des applications conservées est
réduite, et quelques réglages raccourcissent les temps de réponse de
l'interface. Toutes les
opérations prescrites ici s'exécutent **sans accès root** et sont
**réversibles**.

**Lire au moment voulu**, dans le dossier de la skill : chaque phase cite la
section de [reference-adb.md](reference-adb.md) qui porte ses commandes, et
[paquets.md](paquets.md) — classement des applications préinstallées et
recensement des paquets critiques, auxquels il ne faut jamais toucher — s'ouvre
avant la phase 5. La vérification d'une intervention antérieure n'emploie que
les § 2, § 4 et § 13 de reference-adb.md.

## Suivi de progression — impératif

Cette skill couvre trois cas d'usage. Deux demandent le suivi :
l'**intervention**, en huit phases, et la **vérification d'une intervention
antérieure**, en cinq phases. La **connexion seule** — phases 1 et 2, quand
l'utilisateur demande seulement de connecter son téléviseur en adb — s'en
passe. Créer la liste du cas traité **avant sa première phase**, et la
ré-afficher en
entier à chaque changement d'état, avec les marqueurs `[ ]` non commencée, `[~]`
en cours, `[x]` terminée, `[-]` abandonnée ; une étape abandonnée porte une
raison courte sur la même ligne. Plusieurs `[~]` simultanées
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

La phase 7 est une vérification : elle ne passe à `[x]` qu'après un
redémarrage réel suivi d'une reconnexion adb et d'un essai du lanceur, le
résultat étant alors nommé
(`[x] Phase 7 : redémarrer — lanceur et télécommande opérationnels`).

Pour le second cas d'usage, la vérification d'une intervention antérieure :

**Tâches**
- [ ] Vérification 1 : lire le journal de l'intervention
- [ ] Vérification 2 : reconnecter le téléviseur et confirmer l'autorisation
- [ ] Vérification 3 : comparer paquets, accueil et réglages au journal
- [ ] Vérification 4 : mesurer la mémoire sur une journée d'usage
- [ ] Vérification 5 : consigner la vérification dans le journal

Dans ce cas d'usage, la phase de vérification est la troisième : elle ne passe
à `[x]` qu'une fois chaque élément du journal confronté à l'appareil, chaque
écart constaté — ou l'absence d'écart — étant alors nommé
(`[x] Vérification 3 : comparer au journal — aucun écart`).

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
  de débogage réseau, sont dans [reference-adb.md, § 1](reference-adb.md#1-activer-le-débogage-sur-le-téléviseur).
- **Python 3.10 ou une version ultérieure** pour [adb_tv.py](adb_tv.py) : `python --version`.
  Absent, et sans accord pour l'installer : lancer à la main les commandes de
  reference-adb.md que cite chaque phase.

## Utilisation

Les relevés passent par [adb_tv.py](adb_tv.py), script à **lancer**, jamais à
lire. Il exécute lui-même les commandes adb, n'affiche qu'une synthèse et ne
modifie jamais l'appareil.

```text
python "<dossier-skill>/adb_tv.py" probe <IP_TV>
python "<dossier-skill>/adb_tv.py" snapshot <IP_TV> --dir <dossier>
python "<dossier-skill>/adb_tv.py" residents <IP_TV> <paquet> [<paquet> …]
python "<dossier-skill>/adb_tv.py" check-plan <journal> [--ip <IP_TV>]
python "<dossier-skill>/adb_tv.py" compare <journal> [--ip <IP_TV>]
```

`<dossier-skill>` est le chemin absolu du dossier de cette skill,
`{AGENT_DIR}/skills/clean-android-tv`, `~` développé : entre guillemets, un `~`
n'est développé ni par le shell ni par Python.

Codes de sortie : `0` au vert ; `1` écart constaté, détaillé dans la sortie ;
`2` anomalie d'environnement — adb absent, appareil non connecté ou non
autorisé, fichier illisible —, à corriger avant de relancer.

## Instructions

1. **Vérifier les prérequis.** Contrôler `adb version` et l'unicité du binaire.
   Guider l'utilisateur pour activer les options pour les développeurs puis le
   débogage, et lui demander l'adresse IP du téléviseur. Ne jamais supposer que
   le débogage est déjà actif.
2. **Connecter.** `adb connect <IP_TV>:5555`, puis `adb devices -l`. Le
   téléviseur affiche une demande d'autorisation de clé RSA : la faire accepter.
   Ne pas enchaîner tant que l'état n'est pas `device`. En cas d'échec, sonder
   les ports par `adb_tv.py probe <IP_TV>` avant toute hypothèse
   ([reference-adb.md, § 2](reference-adb.md#2-diagnostiquer-un-échec-de-connexion)) : la
   sonde distingue un démon inactif d'un problème de réseau et, sur un refus
   explicite, met hors de cause un VPN installé sur le téléviseur. Ne pas
   demander de redémarrage à ce stade : le réglage de débogage n'y survit pas
   toujours. Si le démon n'écoute pas et qu'aucune option de débogage réseau
   n'existe dans les menus, mettre adbd en écoute réseau depuis un shell local
   sur le téléviseur — procédure au [§ 3](reference-adb.md#3-mettre-adbd-en-écoute-réseau-depuis-un-shell-local).
3. **Relever l'état initial.** Demander à l'utilisateur le dossier du
   journal — à défaut le répertoire de travail courant, jamais le dossier de la
   skill —, puis lancer `adb_tv.py snapshot <IP_TV> --dir <dossier>`. Le
   script relève modèle, version d'Android, occupation de `/data`, pression
   mémoire, paquets et processus en background, écrit le journal de la phase 4
   et n'affiche qu'une synthèse. Annoncer le résultat avant toute
   modification : quand `/data` est occupé à plus de 85 % — la synthèse le
   signale par `ALERTE` —, c'est le stockage qui explique le ralentissement, et la désactivation d'applications
   n'y changera presque rien. Dans ce cas, le dire, proposer en priorité les
   leviers de stockage — vidage des caches
   ([reference-adb.md, § 10](reference-adb.md#10-caches-et-réglages-de-fluidité)),
   suppression par l'utilisateur des applications tierces ou des données dont
   il n'a plus l'usage —, et demander à l'utilisateur s'il faut néanmoins
   procéder à la désactivation ; le journal de la phase 4 reste exigé avant toute
   modification. Ne pas lire le classement de `dumpsys meminfo` comme la liste
   des processus à désactiver : vérifier l'état de chaque processus volumineux
   par `adb_tv.py residents <IP_TV> <paquet>…` avant de l'incriminer, car un processus en cache ne coûte rien de durable
   ([reference-adb.md, § 5](reference-adb.md#5-relevé-de-létat-initial) et
   [§ 6](reference-adb.md#6-distinguer-un-processus-résident-dun-processus-en-cache)).
4. **Consigner l'inventaire restaurable.** Le journal
   `<appareil>-<AAAA-MM-JJ>.md`, écrit par `snapshot`, porte dans son nom le
   constructeur et le modèle en kebab-case (`tcl-percee-tv`), pour que les journaux de deux
   appareils traités le même jour ne se confondent pas ; les relevés bruts sont
   rangés dans le dossier `<appareil>-<AAAA-MM-JJ>-releves/` voisin. Il suit le
   [template du journal](#template-du-journal--impératif) : sortie brute de
   `pm list packages -e` **avant** toute modification, état initial de la
   phase 3, tableau « paquet ou réglage / action / restauration ». Y compléter
   la ligne des processus résidents. Sans le script, l'écrire à la main selon
   le même template. Ce journal est la garantie de réversibilité : ne pas
   passer à la phase suivante sans qu'il existe.
5. **Classer et proposer.** Classer chaque paquet selon
   [paquets.md](paquets.md), et identifier un paquet inconnu par les commandes
   du [§ 7](reference-adb.md#7-identifier-un-paquet-inconnu). Écrire le lot
   dans la section `## Lot` du journal selon le
   [template du lot](#template-du-lot--impératif), une ligne par paquet, avec
   son rôle réel et ce que sa désactivation retire, puis lancer
   `adb_tv.py check-plan <journal>`. Un écart — paquet critique, méthode de
   saisie active, lanceur encore déclaré comme accueil, paquet absent ou déjà désactivé — →
   corriger le lot et relancer ; ne soumettre le lot à l'utilisateur qu'une
   fois le contrôle au vert. Interroger
   l'utilisateur sur ses usages — diffusion Chromecast, assistant vocal, lecture
   de fichiers locaux, services de vidéo à la demande — plutôt que de les
   déduire. Ne jamais désactiver un paquet dont le rôle n'a pas été identifié :
   le signaler comme inconnu et le laisser activé ([paquets.md, § 4](paquets.md#4-classer-un-paquet-inconnu)).
6. **Appliquer.** Après accord explicite sur un lot dont `check-plan` est au
   vert, par groupes de risque homogène.
   Employer `pm disable-user --user 0`, jamais `pm uninstall` sauf demande
   expresse. Contrôler l'interface après chaque groupe par
   `adb shell "dumpsys window | grep mCurrentFocus"`. Un focus inattendu, ou une
   interface qui ne répond plus → réactiver le groupe depuis le journal,
   consigner l'anomalie et reprendre à la phase 5 avec un lot plus étroit.
   Consigner chaque commande
   et sa commande inverse dans le journal, à mesure
   ([reference-adb.md, § 9](reference-adb.md#9-désactiver-et-restaurer)).

   **Remplacer le lanceur d'origine**, quand un lanceur tiers est installé :
   déclarer le nouvel accueil par `set-home-activity`, le contrôler par un
   appui réel sur la touche HOME, puis désactiver le lanceur d'origine dans un
   groupe isolé. Sur le NVIDIA Shield, les deux dernières étapes s'inversent :
   déclarer l'accueil, désactiver le lanceur d'origine, puis contrôler
   l'accueil par la touche HOME
   ([reference-adb.md, § 8](reference-adb.md#8-remplacer-le-lanceur)).
7. **Redémarrer et vérifier.** Avertir d'abord que l'accès adb sera perdu s'il
   repose sur `service.adb.tcp.port`, propriété qui ne survit pas au
   redémarrage. Lancer ensuite `adb reboot`, attendre, reconnecter, et contrôler
   que le lanceur répond et que la télécommande pilote l'interface. Toute
   anomalie → réactiver le dernier groupe depuis le journal et reprendre à la
   phase 5 avec un lot plus étroit. Ne pas enchaîner sur la phase 8 tant que ce
   contrôle n'est pas concluant ([reference-adb.md, § 12](reference-adb.md#12-redémarrage-et-contrôle)).
8. **Finir.** Réglages de fluidité, vidage des caches, puis les leviers qui ne
   passent pas par la désactivation — activité en background des applications
   conservées, démarrage automatique du lanceur tiers, mise à jour
   automatique du magasin, services de localisation
   ([reference-adb.md, § 10](reference-adb.md#10-caches-et-réglages-de-fluidité) et [§ 11](reference-adb.md#11-leviers-au-delà-de-la-désactivation)).
   Un réglage d'activité en background n'est acquis qu'une fois son effet
   mesuré après redémarrage : à défaut, le consigner comme non vérifié. Écrire dans le journal la marche à suivre pour
   tout réactiver, y compris depuis les menus du téléviseur seul. Conseiller
   une réservation DHCP de l'adresse du téléviseur sur la box, pour que les
   commandes du journal restent valables. Refermer l'accès adb et rappeler de
   couper le débogage.

## Templates

### Template du journal — impératif

Reproduire ce template tel quel ; une rubrique sans objet porte « Néant ».
`snapshot` écrit le journal selon ce template ; `check-plan` et `compare` le
relisent d'après ses rubriques ; une ligne qui contient encore `<` est ignorée.

````markdown
# Intervention <appareil> — <AAAA-MM-JJ>

## Appareil
- Modèle : <ro.product.model> — Android <version> (SDK <sdk>)
- Adresse : <IP_TV>

## État initial
- `/data` : <occupation>
- Mémoire : Total RAM <…> (<statut>), Free RAM <…>, swap <…>, uptime <…>
- Processus résidents : <paquet — état oom>, …
- Relevés bruts : `<appareil>-<AAAA-MM-JJ>-releves/`

## Inventaire initial — `pm list packages -e`
```
<sortie brute, avant toute modification>
```

## Lot
| Groupe | Paquet | Rôle réel | Ce que la désactivation retire |
|---|---|---|---|
| <groupe> | `<paquet>` | <rôle> | <effet> |

## Actions
| Paquet ou réglage | Action | Restauration |
|---|---|---|
| `<paquet>` | `pm disable-user --user 0 <paquet>` | `pm enable <paquet>` |
| `<clé settings>` | `settings put global <clé> <valeur>` | `settings put global <clé> <valeur initiale>`, ou `settings delete global <clé>` si sa valeur initiale était `null` |

## État final
- Accueil déclaré : <activité, ou lanceur d'origine>
- Réglages d'activité en background : <paquet — vérifié ou non vérifié>

## Réactivation complète
<commandes inverses, puis marche à suivre depuis les menus du téléviseur>
````

Chaque vérification ultérieure ajoute à la fin une section
`## Vérification <AAAA-MM-JJ>`.

### Template du lot — impératif

Les deux premières colonnes sont lues par `check-plan` : garder les quatre
colonnes dans cet ordre, le paquet entre accents graves. Exemple d'une ligne :

| Groupe | Paquet | Rôle réel | Ce que la désactivation retire |
|---|---|---|---|
| Assistant vocal | `com.google.android.katniss` | Recherche et assistant vocal Google | Recherche vocale et bouton micro de la télécommande |

## Vérification d'une intervention antérieure

Vérifier, sans rien modifier, qu'une intervention consignée tient toujours.
Les commandes et les repères de lecture sont dans
[reference-adb.md, § 13](reference-adb.md#13-vérification-dune-intervention-antérieure).

1. **Lire le journal.** En demander l'emplacement à l'utilisateur, et en lire
   les rubriques « Actions » et « État final » : `compare` relit lui-même
   l'inventaire initial, qu'il est inutile de charger.
2. **Reconnecter.** Comme à la phase 2. Un appareil `unauthorized` a perdu son
   autorisation, ou ne l'a jamais reçue ; une expiration du délai de connexion
   peut signaler un changement d'adresse ([reference-adb.md, § 2](reference-adb.md#2-diagnostiquer-un-échec-de-connexion) et
   [§ 4](reference-adb.md#4-connexion)).
3. **Comparer au journal.** Lancer `adb_tv.py compare <journal>`, qui confronte
   au journal les paquets désactivés, disparus ou nouveaux, l'accueil, les
   réglages `settings` et `appops` consignés, et liste les services
   d'accessibilité et les applications mises à jour depuis l'intervention.
   Tout écart dont l'origine
   n'est pas établie est soumis à l'utilisateur, sans hypothèse sur sa cause.
4. **Mesurer.** `dumpsys procstats --hours 24` après une journée d'usage :
   les processus résidents retirés doivent rester absents, et chaque réglage
   d'activité en background doit montrer son effet. Relever en complément
   `dumpsys meminfo` et `uptime`, et ne comparer que des relevés pris à durée
   de fonctionnement voisine.
5. **Consigner.** Ajouter au journal une section datée : écarts, mesures et
   décisions de l'utilisateur. Ne pas réécrire les sections antérieures, sauf
   pour corriger une commande devenue fausse ou une affirmation démentie ; la
   correction est alors signalée comme telle.

Toute modification de l'appareil que la vérification fait apparaître nécessaire
relève de l'intervention : accord explicite, puis consignation de la commande
et de sa commande inverse.

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
  [paquets.md, § 1](paquets.md#1-paquets-critiques--ne-jamais-désactiver) — interface système, services Google Play,
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
  les paquets non désactivables restent hors d'atteinte, de même qu'un
  composant isolé : seul un paquet entier se désactive à coup sûr
  ([reference-adb.md, § 11](reference-adb.md#11-leviers-au-delà-de-la-désactivation)).
- **Le gain est borné.** Un téléviseur limité par sa mémoire vive ou par un
  stockage saturé ne redevient pas fluide par la désactivation d'applications.
  Le dire, plutôt que de laisser croire à un gain.
- **Les identifiants de paquets varient** selon le constructeur et la version
  d'Android. [paquets.md](paquets.md) couvre l'ossature commune à Android TV et
  à Google TV, et donne l'exemple d'un téléviseur TCL et celui du NVIDIA Shield
  comme modèles de transposition ; un paquet propre à un autre constructeur se
  classe au cas par cas et reste activé tant qu'il n'est pas identifié.
- **Beaucoup de téléviseurs n'exposent pas d'option de débogage réseau.** La
  connexion reste souvent possible ; le câble USB, en revanche, n'est pas un
  repli
  ([reference-adb.md, § 1](reference-adb.md#1-activer-le-débogage-sur-le-téléviseur)).
  Le contournement par un shell local
  ([§ 3](reference-adb.md#3-mettre-adbd-en-écoute-réseau-depuis-un-shell-local))
  échoue si ce shell ne tourne pas en UID 2000 ; il reste alors les menus
  du téléviseur.
- **Hors périmètre** : le root, l'installation d'applications tierces, et toute
  modification de la partition système.

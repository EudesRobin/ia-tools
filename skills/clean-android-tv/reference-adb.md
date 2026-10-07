# Référence adb — Android TV et Google TV

Commandes employées par la skill `clean-android-tv`. Aucune ne requiert d'accès
root. Remplacer `<IP_TV>` par l'adresse du téléviseur sur le réseau local.

Tout filtre — `grep`, `head`, `wc` — s'écrit **à l'intérieur des guillemets**
d'`adb shell` : il s'exécute alors sur le téléviseur, qui le fournit, et la
commande fonctionne quel que soit le shell du poste. Hors des guillemets, il est
confié au shell du poste, et PowerShell ne le connaît pas.

**Sommaire**

1. [Activer le débogage sur le téléviseur](#1-activer-le-débogage-sur-le-téléviseur)
2. [Diagnostiquer un échec de connexion](#2-diagnostiquer-un-échec-de-connexion)
3. [Mettre adbd en écoute réseau depuis un shell local](#3-mettre-adbd-en-écoute-réseau-depuis-un-shell-local)
4. [Connexion](#4-connexion)
5. [Relevé de l'état initial](#5-relevé-de-létat-initial)
6. [Distinguer un processus résident d'un processus en cache](#6-distinguer-un-processus-résident-dun-processus-en-cache)
7. [Identifier un paquet inconnu](#7-identifier-un-paquet-inconnu)
8. [Remplacer le lanceur](#8-remplacer-le-lanceur)
   - [Touche qu'aucun réglage système ne réaffecte](#touche-quaucun-réglage-système-ne-réaffecte)
9. [Désactiver et restaurer](#9-désactiver-et-restaurer)
10. [Caches et réglages de fluidité](#10-caches-et-réglages-de-fluidité)
11. [Leviers au-delà de la désactivation](#11-leviers-au-delà-de-la-désactivation)
12. [Redémarrage et contrôle](#12-redémarrage-et-contrôle)
13. [Vérification d'une intervention antérieure](#13-vérification-dune-intervention-antérieure)

## 1. Activer le débogage sur le téléviseur

Le démon adb est déjà présent dans le système : il suffit de l'activer, sans
rien installer sur le téléviseur.

1. Paramètres → Préférences de l'appareil → À propos → sélectionner sept fois
   **Version de build**.
2. Retour → **Options pour les développeurs** → activer **Débogage ADB**.
3. Activer **Débogage réseau** (**Débogage sans fil** sur Google TV) lorsque
   l'option existe. L'adresse et le port s'affichent.
4. L'adresse IP se lit dans Paramètres → Réseau et Internet → réseau actif.

**Absence d'option de débogage réseau.** Beaucoup de téléviseurs, en particulier
sous Android 8 et les versions antérieures, n'exposent que « Débogage ADB » ou
« Débogage USB ». Sur une partie d'entre eux, le démon écoute malgré tout sur le
port 5555 une fois le débogage activé : tenter `adb connect` avant de conclure.
Si le port reste fermé, la méthode du
[§3](#3-mettre-adbd-en-écoute-réseau-depuis-un-shell-local) s'applique.

**Le câble USB n'est pas un repli sur un téléviseur.** Ses ports USB sont des
ports hôtes, prévus pour une clé ou un disque ; ils ne permettent pas au
téléviseur d'apparaître comme appareil adb sur le poste. `adb tcpip 5555` depuis
une connexion USB ne vaut que pour les boîtiers et clés Android TV dotés d'un
port en mode périphérique.

**Le réglage de débogage ne survit pas toujours au redémarrage.** Activer le
débogage, puis tester aussitôt la connexion, et revérifier l'état du réglage
avant de conclure à un échec. Sur le NVIDIA Shield, le débogage réseau est au
contraire une option de menu persistante : l'accès adb survit au redémarrage,
mais l'autorisation du poste expire au bout de sept jours sans connexion
([§4](#4-connexion)).

## 2. Diagnostiquer un échec de connexion

Le message d'`adb connect` ne distingue pas un démon inactif d'un problème de
réseau. Une sonde TCP des ports 5555, 6466 et 6467 tranche ; `adb_tv.py`
la mène et rapporte, pour chaque port, `ouvert`, `refus` ou `expiration` :

```bash
python "<dossier-skill>/adb_tv.py" probe <IP_TV>
```

- **Refus explicite sur 5555** — l'hôte répond, mais le démon n'écoute pas en
  TCP. Le réseau est hors de cause, un VPN installé sur le téléviseur aussi : un
  refus suppose un aller-retour complet.
- **Expiration du délai sur 5555** — le paquet réseau n'atteint pas l'hôte :
  adresse erronée, segment réseau distinct ou filtrage. Une adresse attribuée
  dynamiquement par la box a pu changer depuis la dernière connexion : relever
  la table ARP du poste (`arp -a`), repérer l'adresse matérielle dont le
  préfixe désigne le constructeur, et sonder l'adresse IP qui lui est associée.
- **6466 et 6467 ouverts** — un appareil Android TV répond bien à cette
  adresse ; ce sont les ports du service de télécommande.

## 3. Mettre adbd en écoute réseau depuis un shell local

Cette méthode s'applique au téléviseur privé d'option de débogage réseau et dont
le démon n'écoute pas en TCP.

Mettre adbd en écoute TCP revient à définir la propriété `service.adb.tcp.port`
puis à relancer le démon — ce que fait `adb tcpip`. L'UID `shell` en a le
droit : il faut donc disposer d'un shell sur l'appareil. Aucune application ne
détient les permissions nécessaires pour le faire elle-même, mais certaines
applications de la catégorie « ADB » du magasin exposent une console adossée au
démon adb local : c'est ce shell-là qui convient.

**Test décisif, avant de retenir une application.** Dans la console de
l'application :

```
id
```

- `uid=2000(shell)` — la console passe par adbd : la suite s'applique.
- `uid=10xxx(u0_aXXX)` — shell applicatif ordinaire, dépourvu des droits de
  l'UID `shell` : il ne peut ni définir la propriété ni relancer adbd. Un
  serveur SSH installé sur le téléviseur est dans le même cas.

**Ouverture**, dans la même console :

```
getprop service.adb.tcp.port     # 5555 : deja defini, passer a la suite
setprop service.adb.tcp.port 5555
stop adbd
start adbd
```

Si `stop adbd` est refusé, désactiver puis réactiver le débogage ADB dans les
options pour les développeurs : le basculement relance le démon, qui relit la
propriété au démarrage. La session de l'application se coupe à cet instant.

Sonder le port depuis le poste par `adb_tv.py probe`, puis lancer
`adb connect`. Le téléviseur affiche
la demande d'autorisation de clé RSA : la faire accepter en cochant « Toujours
autoriser depuis cet ordinateur ».

**Refermer en fin d'intervention :** `setprop service.adb.tcp.port -1`.

La propriété n'a pas le préfixe `persist.` : le réglage est perdu à chaque
extinction complète, et la séquence est à refaire. Une application tierce qui
ouvre une console sur le réseau local élargit par ailleurs la surface
d'attaque ; proposer de désinstaller cette application une fois l'intervention
terminée.

Les applications qui amorcent elles-mêmes un shell par le débogage sans fil
supposent Android 11 ou une version postérieure.

## 4. Connexion

```bash
adb connect <IP_TV>:5555     # le televiseur demande d'autoriser la cle RSA
adb devices -l               # etat attendu : device
adb disconnect               # en fin d'intervention
adb kill-server              # reinitialise le serveur local en cas d'anomalie
```

Un appareil signalé `unauthorized` n'a pas reçu l'autorisation de la clé RSA sur
le téléviseur. Depuis Android 11, le système révoque en outre l'autorisation
d'un poste qui ne s'est pas connecté depuis sept jours : lors d'une
vérification ultérieure, un appareil autorisé pendant l'intervention répond
`unauthorized` et la clé RSA est à réaccepter. Un réglage des options pour les développeurs
désactive ce délai d'expiration des autorisations adb ; ne le proposer que si
des connexions espacées sont prévues, car il prolonge la confiance accordée au
poste. Un appareil `offline` se rétablit rarement par une simple
reconnexion : arrêter puis relancer le serveur local.

## 5. Relevé de l'état initial

`adb_tv.py snapshot` lance les commandes ci-dessous, range leurs sorties à côté du journal
et n'en affiche qu'une synthèse. Elles restent la référence quand le script ne
peut pas être employé.

```bash
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk

adb shell df -h /data                  # occupation du stockage utilisateur
adb shell dumpsys meminfo              # Total RAM, Free RAM, statut, swap
adb shell dumpsys diskstats            # repartition applications / donnees / cache

adb shell pm list packages -s          # paquets systeme
adb shell pm list packages -3          # paquets installes par l'utilisateur
adb shell pm list packages -e          # paquets actives — inventaire a conserver
adb shell pm list packages -d          # paquets deja desactives

adb shell dumpsys procstats --hours 24 # ce qui tourne reellement en background
```

Préférer `dumpsys meminfo` à `/proc/meminfo` : les noyaux anciens n'exposent pas
`MemAvailable`, et `MemFree` seul ne dit rien de la mémoire réellement
disponible.

Repères de lecture :

- `/data` occupé au-delà de 85 % : le stockage est la cause dominante du
  ralentissement, et la désactivation d'applications n'y changera presque rien.
- Le **statut** de la ligne `Total RAM` — `critical`, `low`, `moderate` ou
  `normal` — résume la pression mémoire vue par le système. Selon la version,
  Android le calcule d'après le nombre de processus en cache restants ou
  d'après la pression mesurée par le noyau. Un statut `moderate` accompagné de beaucoup de
  mémoire libre et de peu de swap signale que le système élague son cache, pas
  que la mémoire manque : le lire avec la mémoire libre et le swap, jamais seul.
- L'**occupation du swap** mesure la contrainte réelle : un système qui en
  arrive à compresser des pages pour libérer de la mémoire est un système dont
  la mémoire est saturée. Le swap croît toutefois avec la durée de
  fonctionnement, car le système y range peu à peu les pages inutilisées : deux
  relevés de swap ne se comparent qu'à durée de fonctionnement voisine
  (`adb shell uptime`).
- `procstats` désigne les paquets à examiner en priorité : ceux qui cumulent du
  temps d'exécution sans avoir été ouverts.

## 6. Distinguer un processus résident d'un processus en cache

`dumpsys meminfo` classe les processus par mémoire occupée, non par coût réel.
Un processus volumineux peut n'être qu'un reliquat en cache, que le système
libère à la première demande. Le confondre avec un processus résident conduit à
désactiver une application sans aucun gain. `adb_tv.py residents` lance les
commandes ci-dessous et affiche une ligne par paquet.

```bash
adb shell "dumpsys activity oom | grep -B1 -A1 <PAQUET>"
adb shell "dumpsys activity services <PAQUET>"
adb shell "dumpsys jobscheduler | grep <PAQUET>"
adb shell "dumpsys package <PAQUET> | grep BOOT_COMPLETED"
```

- `cch-empty`, `cch-act`, `prev` — processus conservé pour une réouverture
  rapide. **Aucun coût réel**, rien à corriger.
- `Persistent`, `Imp Fg`, `svc`, ou un `ServiceRecord` actif — résident
  véritable, candidat légitime.
- Une entrée dans `jobscheduler` ou un récepteur `BOOT_COMPLETED` — le coût
  n'est pas la mémoire mais les réveils périodiques du processeur. Traiter ce
  cas par le [§11](#11-leviers-au-delà-de-la-désactivation).

## 7. Identifier un paquet inconnu

```bash
adb shell "dumpsys package <PAQUET> | head -40" # version, chemin, flags
adb shell pm path <PAQUET>                      # emplacement de l'apk
adb shell cmd package list packages --show-versioncode -s
```

Un paquet dont le rôle n'est pas établi reste activé.

## 8. Remplacer le lanceur

Un lanceur tiers installé ne devient pas l'accueil du système pour autant : le
lanceur d'origine reste déclaré, la touche HOME continue de l'ouvrir, et il ne
peut donc pas être désactivé.

```bash
adb shell "cmd package query-activities -a android.intent.action.MAIN -c android.intent.category.HOME"
adb shell "cmd package set-home-activity <PAQUET>/<ACTIVITE>"
adb shell "dumpsys package preferred-activities | grep -B8 category.HOME"
```

**Vérifier par `dumpsys package preferred-activities`, non par
`resolve-activity`.** Ce dernier continue d'annoncer le lanceur d'origine après
un changement réussi : il renvoie la résolution brute, non la préférence
enregistrée. La preuve d'un réglage effectif est la ligne `mAlways=true` sous
l'activité voulue.

Contrôler ensuite par un appui réel sur la touche HOME depuis une application au
premier plan, et constater le résultat par
`adb shell "dumpsys window | grep mCurrentFocus"`. Le lanceur d'origine ne se désactive
qu'une fois ce contrôle concluant.

**Exception : le NVIDIA Shield.** Le système y ignore la préférence d'accueil :
même avec `mAlways=true` vérifié, la touche HOME et l'intention `MAIN/HOME`
ouvrent le lanceur d'origine, y compris après un `am force-stop` de celui-ci.
Seule la désactivation du lanceur d'origine rend la préférence effective.
Inverser donc l'ordre : déclarer le nouvel accueil par `set-home-activity`,
désactiver le lanceur d'origine dans un groupe isolé, puis contrôler la touche
HOME ; en cas d'échec, `pm enable` rétablit le lanceur d'origine. Un service
d'accessibilité installé pour capter la touche HOME devient alors superflu et se
retire comme l'indique [Touche qu'aucun réglage système ne réaffecte](#touche-quaucun-réglage-système-ne-réaffecte).

`com.android.tv.settings/.system.FallbackHome` sert de solution de repli :
l'appareil ne reste pas sans accueil si le lanceur tiers échoue.

**Couper le démarrage automatique propre au lanceur tiers.** Un lanceur tiers
installé avant d'être déclaré accueil propose souvent de se lancer lui-même au
démarrage. Une fois l'accueil déclaré par `set-home-activity`, ce réglage
devient nuisible : le système lance déjà l'accueil par `CATEGORY_HOME`, et le lanceur qui se relance
par `LEANBACK_LAUNCHER` place son activité d'accueil hors de la pile d'accueil.
Chaque retour par la touche HOME reconstruit alors cette activité, ce qui fige
l'écran plus d'une seconde sur un appareil d'entrée de gamme. Le réglage
est interne au lanceur : le faire passer sur « aucun » dans son interface, puis
contrôler après redémarrage :

```bash
adb shell "logcat -d | grep -E 'START.*LEANBACK_LAUNCHER'"   # aucune relance par le lanceur
adb shell "dumpsys activity activities | grep -E 'Stack #|Run #'"
```

Sous Android 8, l'activité d'accueil doit figurer seule dans `Stack #0`, la
pile d'accueil.

**Lanceur d'origine redéclaré à chaque démarrage.** Certains constructeurs
redéclarent le lanceur d'origine comme accueil préféré à chaque démarrage — sur
TCL sous Android 8, `logcat` montre `addPreferredActivity....tvlauncher`. Tant
que le lanceur d'origine est désactivé, le gestionnaire de paquets retire cette
déclaration quelques secondes plus tard (`Removing dangling preferred activity`).
Dans l'intervalle, le système ou le lanceur tiers peut afficher une demande de
confirmation de l'accueil par défaut : la faire accepter au profit du lanceur
tiers. Le lanceur d'origine reste désactivé ; ne jamais le réactiver sans
relancer ensuite `set-home-activity`.

### Touche qu'aucun réglage système ne réaffecte

Quand aucun réglage système ne réaffecte une touche, une application de
remappage fondée sur le service d'accessibilité rétablit le comportement voulu. Ce contournement a un coût : le service s'intercale en permanence dans la
chaîne d'événements de toute l'interface. Le réserver aux touches qu'aucun
réglage système ne couvre, et vérifier d'abord `set-home-activity`, qui suffit
dans le cas courant de la touche HOME. Retirer un tel service de la liste des
services actifs :

```bash
adb shell "settings get secure enabled_accessibility_services"   # relever la valeur
adb shell 'settings put secure enabled_accessibility_services "<VALEUR_SANS_LE_SERVICE>"'
```

Conserver la valeur relevée : c'est la seule façon de restaurer la liste à
l'identique.

## 9. Désactiver et restaurer

```bash
adb shell pm disable-user --user 0 <PAQUET>     # reversible, methode par defaut
adb shell pm enable <PAQUET>                    # restauration

adb shell pm uninstall -k --user 0 <PAQUET>     # sur demande expresse seulement
adb shell cmd package install-existing <PAQUET> # restauration
```

`disable-user --user 0` n'altère pas la partition système : le paquet reste
présent, simplement inactif pour l'utilisateur courant. `uninstall --user 0` le
retire pour l'utilisateur courant sans toucher à l'image système ; `-k` conserve
les données. Une mise à jour du système peut le réinstaller.

`pm clear <PAQUET>` efface les données d'une application : compte, réglages et
sessions ouvertes sont perdus. Ne l'employer que sur demande explicite portant
sur l'application nommée.

Désactiver un paquet n'arrête pas son processus en cours : `disable-user`
empêche seulement les démarrages ultérieurs. Le processus disparaît au
redémarrage, ou immédiatement par `am force-stop`.

**La restauration ne demande pas adb.** Les paquets désactivés restent visibles
dans Paramètres → Applications → Voir toutes les applications, où ils se
réactivent un par un. L'indiquer à l'utilisateur : c'est sa solution de secours
quand l'accès adb est refermé.

## 10. Caches et réglages de fluidité

```bash
adb shell pm trim-caches 999G                   # libere les caches applicatifs

adb shell settings put global window_animation_scale 0.5
adb shell settings put global transition_animation_scale 0.5
adb shell settings put global animator_duration_scale 0.5
```

Les échelles d'animation n'accélèrent rien : elles raccourcissent les
transitions, ce qui rend l'interface plus réactive à l'usage. La valeur `0`
supprime les animations, `1` est la valeur d'origine. Relever la valeur de
départ par `settings get global <CLE>` ; quand elle vaut `null`, la restauration
se fait par `settings delete global <CLE>`.

## 11. Leviers au-delà de la désactivation

À examiner une fois le lot de désactivations appliqué. Ces leviers portent sur
des paquets critiques, ou sur des applications que l'utilisateur emploie et qui
ne peuvent donc pas être désactivées.

**Couper l'activité en background d'une application conservée.** L'état `svc`
dans `dumpsys activity oom` signale un service permanent. Le réglage
`RUN_IN_BACKGROUND` ne prend effet sur le processus en cours qu'après un arrêt
forcé :

```bash
adb shell "cmd appops set <PAQUET> RUN_IN_BACKGROUND ignore"
adb shell "am force-stop <PAQUET>"
adb shell "cmd appops get <PAQUET> RUN_IN_BACKGROUND"   # verification
```

L'application recharge son contenu à l'ouverture au lieu de le préparer à
l'avance. Restauration par `allow`. Demander ensuite à l'utilisateur d'ouvrir
l'application et de confirmer qu'elle fonctionne : c'est le seul contrôle qui
vaille pour un usage conservé.

**L'effet de `RUN_IN_BACKGROUND` n'est acquis qu'une fois mesuré.** Le réglage
persiste, mais il n'arrête pas tout :

- un récepteur `BOOT_COMPLETED` de l'application relance son service à chaque
  démarrage ;
- un service que l'application lie elle-même échappe à l'arrêt des services en
  background.

Contrôler l'effet après un redémarrage, puis après une journée d'usage :

```bash
adb shell "dumpsys activity services <PAQUET> | grep -E 'ServiceRecord|createTime|ConnectionRecord'"
adb shell "dumpsys procstats --hours 24 | grep -A4 '<PAQUET> '"
```

Un `ServiceRecord` créé au démarrage, ou une ligne `Service` qui occupe la
majeure partie des 24 heures, signale un réglage sans effet. Le consigner comme
tel, sans annoncer de gain. Aucun autre levier ne s'offre alors à l'UID
`shell` que la désactivation du paquet entier.

**Désactiver un composant plutôt qu'un paquet : généralement refusé.**

```bash
adb shell "pm disable --user 0 <PAQUET>/<CLASSE_DU_COMPOSANT>"
adb shell "pm enable <PAQUET>/<CLASSE_DU_COMPOSANT>"
```

Android n'autorise l'UID `shell` à basculer que des paquets entiers. La
commande échoue sur un composant et renvoie
`SecurityException: Shell cannot change component state`, y compris sur une
application portant le flag `SYSTEM` — refus vérifié sous Android 8. Le flag
`SYSTEM` ne lève donc pas la restriction. La commande se tente sans risque :
consigner le refus, et ne présenter la désactivation d'un composant comme une
solution qu'après sa réussite.

**Les récepteurs de recommandations ne demandent aucune action.** Les
applications de diffusion déclarent des récepteurs visant
`com.google.android.tvrecommendations` et
`com.google.android.leanbacklauncher.recommendations`, ainsi qu'un récepteur
`android.media.tv.action.INITIALIZE_PROGRAMS`. Désactiver les deux paquets que
visent ces récepteurs — ce que fait le groupe du lanceur — suffit à rendre ces
récepteurs inertes. Le `TvProvider` reste alimenté, et c'est souhaitable : un
lanceur tiers y puise ses propres rangées. Couper ce mécanisme retirerait une
fonctionnalité, non une charge.

**Services de localisation.** Sans objet sur un téléviseur fixe, et source de
réveils périodiques :

```bash
adb shell "settings get secure location_providers_allowed"
adb shell "settings put secure location_providers_allowed -gps"
adb shell "settings put secure location_providers_allowed -network"
```

Les préfixes `-` et `+` retirent et ajoutent un fournisseur sans réécrire la
liste entière. Restauration par `+gps` et `+network`.

**Mise à jour automatique du magasin d'applications.** Le magasin est un paquet
critique, mais son activité en background pèse souvent lourd. Le réglage de
mise à jour automatique est propre au magasin et **n'est pas accessible par adb** : il
se modifie dans son interface, rubrique des préférences réseau. L'indiquer à
l'utilisateur plutôt que de chercher une commande.

**VPN installé sur le téléviseur.** Sur un processeur d'entrée de gamme, le
chiffrement du tunnel est une charge permanente.
Ne pas désinstaller le VPN d'autorité : mesurer la charge du VPN, énoncer le
chiffre, laisser l'utilisateur arbitrer.

**Applications relancées au démarrage.** Inventorier celles qui déclarent
`BOOT_COMPLETED` parmi les applications tierces conservées, et confronter la
liste à l'usage réel.

## 12. Redémarrage et contrôle

```bash
adb reboot
adb connect <IP_TV>:5555                          # apres le redemarrage
adb shell "dumpsys window | grep -i mCurrentFocus" # lanceur au premier plan
adb shell "pm list packages -d | wc -l"            # desactivations conservees
adb shell df -h /data
```

Le contrôle porte sur trois points : le téléviseur démarre, le lanceur s'affiche
et la télécommande pilote l'interface. Un seul de ces points en défaut impose la
réactivation du dernier groupe de paquets désactivés.

**Mesurer sur un état comparable.** Un relevé pris juste après l'usage d'une
application est gonflé par l'application elle-même, que le système conserve en
cache sous l'état `prev`. Comparer deux relevés pris dans des conditions
différentes produit un chiffre faux. Signaler que les relevés ne sont pas
comparables plutôt que d'annoncer l'écart, et s'en tenir alors aux indicateurs
insensibles à l'activité en cours : le statut mémoire, l'occupation du swap, le
nombre de paquets désactivés et l'occupation de `/data`. Le statut et le swap
dépendent eux-mêmes de la durée de fonctionnement : relever `uptime` avec
chaque mesure et ne comparer que des relevés pris à durée de fonctionnement
voisine. Après
plusieurs jours de fonctionnement, la mesure qui fait foi est
`dumpsys procstats --hours 24`, qui moyenne une journée d'usage.

## 13. Vérification d'une intervention antérieure

La vérification est une lecture : elle ne modifie rien sur l'appareil. Chaque
relevé se confronte au journal de l'intervention. `adb_tv.py compare` mène
cette confrontation, à l'exception de `logcat` et de `procstats`, à lire
directement.

```bash
adb shell uptime                                    # duree depuis le dernier demarrage
adb shell "pm list packages -d"                     # a comparer a la liste du journal
adb shell "pm list packages"                        # paquets disparus ou nouveaux
adb shell "cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
adb shell "dumpsys package preferred-activities | grep -B8 category.HOME"
adb shell "settings get secure enabled_accessibility_services"
adb shell "cmd appops get <PAQUET> RUN_IN_BACKGROUND"
adb shell "dumpsys package packages | grep -E '^  Package \[|lastUpdateTime'"
adb shell "logcat -d -b all | grep -i -E 'preferred|HOME'"   # historique depuis le demarrage
adb shell "dumpsys procstats --hours 24"
```

Repères de lecture :

- **Paquet de l'inventaire du journal absent de l'appareil** — désinstallation postérieure à
  l'intervention. En demander l'origine à l'utilisateur plutôt que de la
  supposer.
- **Application mise à jour depuis l'intervention** — vérifier qu'elle ne
  déclare pas de nouvel accueil (`query-activities` ci-dessus) ni de nouveau
  service résident.
- **Réglage `settings` ou `appops` revenu à sa valeur initiale** — réglage
  annulé, par une mise à jour du système ou depuis les menus.
- **Résident retiré qui réapparaît dans `procstats`** — paquet réactivé, ou
  réglage d'activité en background sans effet ([§11](#11-leviers-au-delà-de-la-désactivation)).

L'historique de `logcat` ne remonte qu'au dernier démarrage, souvent moins : un
événement antérieur, comme une demande de confirmation d'accueil, ne s'y lit
plus. Signaler cette limite plutôt que d'affirmer la cause de l'écart constaté.

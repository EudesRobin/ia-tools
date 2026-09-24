# Classement des paquets Android TV

Grille de décision employée par la skill `clean-android-tv`. Les identifiants
varient selon le constructeur et la version d'Android : confirmer chaque paquet
sur l'appareil par `pm list packages -e` avant d'agir, sans jamais présumer sa
présence.

## 1. Paquets critiques — ne jamais désactiver

Désactiver l'un de ces paquets rend le téléviseur inutilisable ou le prive de
son interface, parfois sans possibilité de retour en arrière depuis la
télécommande.

| Paquet | Rôle |
|---|---|
| `android`, `com.android.shell` | Socle du système et canal adb lui-même |
| `com.android.systemui` | Interface système, barres et dialogues |
| `com.google.android.tvlauncher` | Lanceur Android TV — écran d'accueil |
| `com.google.android.apps.tv.launcherx` | Lanceur Google TV — écran d'accueil |
| `com.google.android.leanbacklauncher` | Lanceur des versions antérieures |
| `com.android.tv.settings`, `com.android.settings` | Menu des paramètres |
| `com.google.android.gms` | Services Google Play — authentification, comptes |
| `com.google.android.gsf` | Services de base Google |
| `com.android.vending` | Play Store et mécanisme de mise à jour |
| `com.android.providers.*` | Fournisseurs de contenu — réglages, médias, téléchargements |
| `com.google.android.webview`, `com.android.webview` | Moteur de rendu web partagé |
| `com.google.android.tv.remote.service` | Appairage et service de télécommande |
| Chaîne vidéo du constructeur | Tuner, entrées HDMI, passerelle vidéo — voir [§2](#2-couche-constructeur) |
| Méthode de saisie active | Clavier à l'écran ; sans elle, aucune saisie |

La méthode de saisie active se lit par
`adb shell settings get secure default_input_method`. Le paquet que cette valeur
désigne devient critique, quel que soit son nom.

**Le lanceur cesse d'être critique quand un autre accueil est déclaré.** Sans
lanceur tiers installé, le lanceur d'origine reste critique : la skill n'en
installe pas et ne le désactive pas. Un lanceur tiers installé ne suffit pas
pour autant : tant que `dumpsys package preferred-activities` désigne le lanceur
d'origine, celui-ci reste indispensable. Une fois le nouvel écran d'accueil
défini par `cmd package set-home-activity` et contrôlé par un appui réel sur la
touche HOME, le lanceur d'origine et son service de recommandations deviennent
désactivables. Désactiver le lanceur d'origine libère une part notable de la
mémoire sur un appareil à mémoire limitée. Procédure dans
[reference-adb.md](reference-adb.md), qui traite aussi l'exception du NVIDIA
Shield, où la désactivation du lanceur d'origine précède le contrôle par la
touche HOME.

## 2. Couche constructeur

Les paquets préfixés par le constructeur — `com.sony.`, `com.philips.`,
`com.nvidia.`, `com.tcl.`, `com.hisense.`, `com.xiaomi.`, `com.mediatek.` — ne
se classent pas d'avance. Certains portent le pilotage du tuner, du
rétroéclairage ou des entrées HDMI et sont donc critiques ; d'autres ne sont que
des applications d'accompagnement.

La répartition est toujours la même : **couche matérielle critique — chaîne
vidéo et entrées sur un téléviseur, télécommande et audio sur un boîtier —,
applications d'accompagnement désactivables, reste non identifié laissé
activé.** Deux exemples servent de modèles de transposition : le tableau TCL
ci-dessous, pour un téléviseur sous Android 8, et celui du NVIDIA Shield plus
bas, pour un boîtier sous Android 11. Les identifiants d'un autre constructeur
diffèrent.

| Paquet TCL | Classement |
|---|---|
| `com.tcl.tv`, `com.tcl.tvinput`, `com.tcl.tvpassthrough`, `com.tcl.sourcemananger` | Critique — tuner, entrées, passerelle vidéo |
| `com.mediatek.tunerservice`, `com.mediatek.wifi`, `mtktvapi.agent` | Critique — couche matérielle |
| `com.tcl.settings`, `com.tcl.initsetup`, `com.tcl.inputmethod.international` | Critique — paramètres et méthode de saisie |
| `com.tcl.autopair`, `com.tcl.rc.ota` | Critique — appairage et micrologiciel de la télécommande |
| `com.tcl.audioplayer`, `com.tcl.imageplayer`, `com.tcl.videoplayer`, `com.tcl.ui_mediaCenter`, `com.tcl.pvr.pvrplayer` | Désactivable quand un lecteur tiers assure la lecture locale |
| `com.tcl.MultiScreenInteraction_TV` | Partage d'écran TCL, distinct de la diffusion Chromecast |
| `com.tcl.appmarket2`, `com.tcl.esticker`, `com.tcl.partnercustomizer`, `android.autoinstalls.config.tcl.device` | Magasin et personnalisation d'usine |
| `com.tcl.smartalexa` | Assistant vocal Alexa |
| `com.tcl.versionUpdateApp` | Arbitrage — voir ci-dessous |
| `com.tcl.tvweishi`, `com.tcl.m`, `com.tcl.xian.StartandroidService`, `com.tcl.eletronicpolicy`, `com.tcl.factory.view`, `com.tcl.virtualkey` | Rôle non établi — laissé activé |

**Le vérificateur de mises à jour du constructeur demande un arbitrage
explicite.** Sur TCL, `com.tcl.versionUpdateApp` est marqué persistant et occupe
de la mémoire en permanence, mais c'est lui qui va chercher les mises à jour du
système. Sur un appareil dont le constructeur a cessé d'en publier, le
désactiver ne retire rien et libère de la mémoire ; rien ne permet de vérifier
cet arrêt depuis l'appareil. Poser la question à l'utilisateur, consigner sa
réponse, et rappeler que `pm enable` le réactive le jour où une mise à jour est
attendue.

**Paquets restés sous un nom de développement.** Un appareil peut embarquer des
paquets nommés `com.example.*`, signés avec la clé de plateforme et portant le
flag `PERSISTENT`. Ce nommage résulte d'une négligence du constructeur : ces
paquets appartiennent au système d'origine. Leur rôle n'étant pas établi et le
système les maintenant délibérément actifs, les laisser activés : le gain de
mémoire attendu ne justifie pas le risque. `dumpsys package <PAQUET>` confirme
le `sharedUser=android.uid.system` et les flags de `pkgFlags`.

### Exemple : NVIDIA Shield sous Android 11

Le Shield est un boîtier, sans tuner ni entrée HDMI : la couche constructeur
porte ici la télécommande Bluetooth, l'audio, les mises à jour du système et un
ensemble d'applications d'accompagnement.

| Paquet NVIDIA | Classement |
|---|---|
| `com.nvidia.ota` | Arbitrage — mises à jour du système ; même règle que le vérificateur TCL ci-dessus |
| `com.nvidia.blakepairing`, `com.nvidia.bluetooth.ShieldBluetoothManager`, `com.android.bluetooth` | Critique — appairage et pilotage de la télécommande Bluetooth d'origine |
| `com.nvidia.nvaudiosvc`, `com.nvidia.NvCPLSvc`, `com.nvidia.shieldtech.*`, `com.dolby.android.audio.service` | Critique — audio, réglages matériels et services système du constructeur |
| `com.nvidia.shield.nas`, `com.nvidia.shield.smbauth` | À conserver quand le boîtier accède à des partages réseau distants |
| `com.nvidia.stats`, `com.nvidia.factorysyschecker`, `com.nvidia.feedback`, `com.nvidia.diagtools` | Désactivable — télémétrie et diagnostic |
| `com.nvidia.factory`, `com.nvidia.factorybundling`, `com.nvidia.shield.welcome`, `com.nvidia.shield.registration` | Désactivable — outils d'usine et configuration initiale |
| `com.nvidia.shieldbeta`, `com.nvidia.shield.beta` | Désactivable hors inscription au programme bêta |
| `com.nvidia.developerwidget`, `com.nvidia.tegraprofiler.security` | Désactivable — outils de développement |
| `com.nvidia.nvgamecast`, `com.nvidia.tegrazone3`, `com.nvidia.ControllerMapper`, `com.nvidia.bluetooth.ps3usbpairer` | Désactivable quand le boîtier ne sert pas au jeu — NVIDIA a arrêté GameStream en 2023 |
| `com.nvidia.shield.ask`, `com.nvidia.hotwordsetup` | Assistant vocal NVIDIA — désactivable dans le même groupe que `com.google.android.katniss` (§3) |
| `com.nvidia.shield.smbserver` | Serveur SMB qui partage le stockage du boîtier sur le réseau — désactivable s'il n'est pas utilisé |
| `com.nvidia.irtuner` | Récepteur infrarouge — désactivable quand seule la télécommande Bluetooth est employée ; HDMI-CEC n'en dépend pas |
| `com.amazon.amazonvideo.livingroom.nvidia` | Prime Video préinstallé — candidat courant (§3) |
| `com.nvidia.benchmarkblocker` | Désactivé d'origine |
| `com.nvidia.packagemanagerservice`, `com.nvidia.KeyComboOta`, `com.nvidia.NvCPLUpdater`, `com.nvidia.app.messaging`, `com.nvidia.avsync`, `com.nvidia.inputviewer`, `com.nvidia.osc`, `com.nvidia.overscancomp`, `com.nvidia.remotelocator`, `com.nvidia.shield.appselector`, `com.nvidia.shield.nvcustomize`, `com.nvidia.shield.remote.server`, `com.nvidia.shieldservice`, `com.nvidia.wifi.countrycode` | Rôle non établi ou lié au matériel — laissé activé |

Deux particularités du Shield modifient le déroulé :

- **L'accueil déclaré est ignoré tant que le lanceur d'origine est actif.** Le
  contrôle par la touche HOME ne peut donc pas précéder la désactivation du
  lanceur d'origine : procédure dans [reference-adb.md](reference-adb.md).
- **Le débogage réseau survit au redémarrage.** C'est une option de menu
  persistante : l'accès adb n'est pas perdu à la phase 7.

## 3. Candidats courants — effet à annoncer

Ces paquets se désactivent sans compromettre le démarrage. La seconde colonne
énonce ce qui doit être annoncé à l'utilisateur avant son accord.

| Paquet | Ce que cela retire |
|---|---|
| `com.google.android.katniss` | Recherche et assistant vocal, bouton micro de la télécommande |
| `com.google.android.tvrecommendations` | Rangées de recommandations de l'écran d'accueil |
| `com.google.android.backdrop` | Économiseur d'écran d'ambiance |
| `com.google.android.apps.mediashell` | Diffusion Chromecast intégrée |
| `com.google.android.play.games` | Services de jeu Play |
| `com.google.android.videos` | Application de films et séries Google |
| `com.google.android.youtube.tvmusic`, `com.google.android.youtube.tvkids` | YouTube Music, YouTube Kids |
| `com.android.printspooler` | Impression — sans usage sur un téléviseur |
| `com.google.android.syncadapters.*` | Synchronisation des contacts et de l'agenda |
| `com.google.android.partnersetup`, `com.google.android.tungsten.setupwraith` | Configuration initiale, achevée depuis longtemps |
| `com.android.cts.ctsshim`, `com.android.cts.priv.ctsshim` | Composants de test de conformité Android, sans fonction en usage courant |
| `com.android.dreams.basic` | Économiseur d'écran de base, redondant avec celui d'un lanceur tiers |
| `com.google.android.backuptransport`, `com.android.backupconfirm`, `com.android.wallpaperbackup`, `com.android.sharedstoragebackup` | Sauvegarde Google — à ne couper que si la restauration de l'appareil n'est pas attendue |
| Méthode de saisie installée mais non activée | Rien. `ime list -s` donne les méthodes actives, `ime list -a -s` toutes celles présentes |
| Applications de diffusion préinstallées non utilisées | Le service correspondant, réinstallable depuis le Play Store |

**Chercher une application préinstallée par son nom commercial échoue quand le
paquet porte l'ancien nom du service.** Rakuten TV s'installe sous
`tv.wuaki.apptv`, du nom du service racheté. Balayer la liste complète des
paquets système actifs plutôt que de filtrer sur les marques attendues.

## 4. Classer un paquet inconnu

Dans l'ordre, en s'arrêtant à la première réponse qui tranche :

1. **Le nom désigne-t-il une fonction visible ?** Une application de diffusion,
   un jeu, un assistant. Si oui, l'effet de la désactivation est prévisible.
2. **L'identifiant du paquet contient-il `provider`, `service`, `framework`,
   `setup`, `ime`, `launcher`, `systemui` ?** Traiter le paquet comme critique
   par défaut.
3. **`dumpsys package <PAQUET>` l'identifie-t-il comme paquet système ?** Un
   paquet système sans fonction identifiée reste activé.
4. **Consomme-t-il des ressources en fond ?** `dumpsys procstats --hours 24`.
   Désactiver un paquet qui ne consomme rien n'apporte aucun gain et ajoute du
   risque.

Un paquet que ces quatre points ne permettent pas de classer est **signalé comme
inconnu et laissé activé**. La skill ne propose pas de désactiver ce qu'elle n'a
pas su identifier.

## 5. Ce que la désactivation ne fait pas

- Elle ne libère **pas** d'espace de stockage : le paquet reste sur la partition
  système. Seul l'espace occupé par le cache et les données de l'application se
  récupère, par `pm trim-caches` ou `pm clear`.
- Elle ne réduit la mémoire occupée que pour les paquets qui s'exécutaient
  réellement en fond, ce que seule la mesure établit.
- Elle ne survit pas nécessairement à une mise à jour majeure du système :
  conserver le journal permet de réappliquer le lot.

# Vocabulaire

Les termes retenus pour ce dépôt, et ceux à ne pas employer. Ce document fait
autorité : quand un terme figure ici, c'est celui-là qu'on emploie, dans la
documentation comme dans les messages produits par les outils.

La colonne « À ne pas employer » n'est pas décorative. Elle recense des
formulations qui ont été essayées puis écartées ; sans elle, ces formulations
reviennent.

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

## 1. Principe sur les termes anglais

Un terme anglais s'écrit tel quel lorsqu'il est **couramment employé en français
technique** — *hook*, *skill*, *front-matter*, *pull request*, *merge*, *shell*,
*flag*, *root*, *cache*, *swap*, *payload*. Ne pas lui imposer une traduction
française rare, qui obscurcit au lieu de clarifier.

La règle vaut aussi contre les traductions qui **existent** mais ne s'emploient
pas : *flag* ne devient ni « drapeau », calque raide, ni « indicateur », exact
mais jamais employé spontanément. Dans le doute sur un terme technique, garder
l'anglais et poser la question plutôt que de trancher pour une traduction.

Inversement, ne pas employer d'anglicisme quand le mot français est courant :
on écrit « contrôle », pas « gate » ; « dérive », pas « drift ».

Les termes anglais retenus s'écrivent **en minuscules** et prennent la marque
française du pluriel : « des hooks », « trois skills », pas « des Hooks ».

L'abréviation *vs* est **admise** : elle est entrée dans l'usage français et
reste plus lisible que « face à » ou « par rapport à » dans une comparaison
dense. Ne pas la remplacer dans les documents qui l'emploient.

## 2. Harnais et vérification

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **harnais** | L'ensemble des règles, outils et boucles qui maintiennent l'agent ancré et lui permettent de savoir s'il a réussi. | — |
| **le DoD** (masculin) | *Definition of Done* : ce que « terminé » signifie, énoncé comme une condition contrôlable. Introduire la forme longue au premier emploi dans un document, puis abréger. | « définition du fait », « la DoD » |
| **contrôle** | Le mécanisme qui rend un verdict objectif : tests, compilation, validateur. | « barrière », « juge de paix », « gate » |
| **critère** | Un des points qu'examine un agent d'audit et qu'il juge sur pièces — accessibilité des règles, duplication, solidité du harnais. Le critère relève du jugement ; le contrôle rend un verdict objectif. | « contrôle » pour désigner un critère d'audit |
| **application des règles** | Ce qui fait qu'une règle est réellement respectée — instruction écrite, DoD, script, hook, intégration continue. Ces mécanismes ne se valent pas ; les nommer directement plutôt que les classer. | « échelle de contrainte », « échelle de garantie », « barreau », « enforcement » |
| **ancrage** | Constater l'état réel avant d'agir, au lieu de le supposer. | « grounding » |
| **phase de vérification** | Dans un déroulé, la phase qui ne passe à `[x]` que sur une preuve nommée — par exemple un contrôle au vert, une ligne réellement lue, l'accord de l'utilisateur. Elle s'adosse éventuellement à un contrôle, mais n'en est pas un. | « phase de contrôle », « la phase N est un contrôle » |
| **boucle de vérification** | Lancer → observer → corriger → relancer, jusqu'à ce que le contrôle soit au vert. | « feedback loop » |
| **dérive** | L'écart qui se creuse entre ce qui est documenté et ce qui existe. | « drift » |
| **liste de tâches** | La liste d'étapes tenue à jour pendant l'exécution d'un outil, quel que soit son affichage. Ses marqueurs sont exactement `[ ]`, `[~]`, `[x]` et `[-]`, et l'en-tête sous lequel elle s'affiche est `**Tâches**`. Nommer la fonction, jamais l'outil qui la porte : son nom varie d'une session à l'autre. | « todo list », « task list », « TodoWrite » |
| **suivi de progression** | Le fait de tenir cette liste à jour au fil des étapes. Le protocole qui le régit est au [§5 de qualite-outils.md](qualite-outils.md#5-déroulés-et-suivi-de-progression). « Suivre l'avancement » convient aussi bien. | « progress tracking » |
| **suivi par l'outil de la session** | La liste tenue à jour dans l'outil de liste de tâches de la session, quand celle-ci en expose un, et affichée par lui. | « voie native », « mode natif », « panneau intégré » |
| **suivi dans la réponse** | La liste tenue à jour dans un bloc `**Tâches**` écrit dans la réponse, quand la session n'expose aucun outil de ce type. **À égalité avec le suivi par l'outil de la session** : les deux satisfont le protocole, aucun n'est un échec. | « voie imprimée », « repli », « voie dégradée », « mode secours » |
| **checklist Markdown** | La forme concrète que prend le suivi dans la réponse : le bloc `**Tâches**`, écrit puis ré-affiché en entier à chaque changement d'état. Markdown est le nom du format : ne pas chercher à le traduire. | « checklist imprimée », « checklist en prose » ; toute formulation la qualifiant de repli — les deux suivis se valent ([qualite-outils.md §5](qualite-outils.md#5-déroulés-et-suivi-de-progression)) ; le marqueur en une seule ligne `✓ n terminé → suivant`, incompatible avec le ré-affichage intégral |
| **[mécanique]** (marqueur de checklist) | Signale qu'un item est vérifié par `scripts/validate.py`, par opposition aux items non marqués, qui relèvent du jugement ([qualite-outils.md §11](qualite-outils.md#11-checklist)). Repris de l'expression « vérifié mécaniquement » ([CONTRIBUTING.md §3](CONTRIBUTING.md#3-ce-qui-est-vérifié-mécaniquement), [CONVENTIONS.md §6](CONVENTIONS.md#6-checklist--ajouter-un-document-de-fond)). | « [validé] » — contredit la case à cocher `[ ]` voisine, puisqu'il annonce un état accompli alors que `[ ]` marque ce qui reste à faire, et ne dit pas par quel moyen |

## 3. Documentation

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **table de routage** | [DOC_MAP.md](DOC_MAP.md), l'autorité qui rattache chaque tâche au document qui la régit. | « carte de documentation », « doc map », « index » |
| **découpage** | Le fait de limiter la longueur du document canonique d'un outil en sortant le détail dans des fichiers embarqués ([qualite-outils.md §3](qualite-outils.md#3-découpage--limiter-la-longueur-du-document-canonique)). | « divulgation progressive », « progressive disclosure » |
| **latitude** | Ce qu'une instruction laisse décider à l'agent, à ajuster à la fragilité de la tâche ([qualite-outils.md §4](qualite-outils.md#4-latitude-laissée-à-lagent)). | « degré de liberté », « degrees of freedom » |
| **document de fond** | Un document de `docs/` qui explique le *pourquoi* des règles, enregistré dans la table. Ce n'est pas un outil. | « document compagnon » — calque de *companion document* ; « doc annexe » |
| **lien de retour** | La ligne qui, depuis un document de fond, renvoie vers la table. | « lien retour » — composé sans préposition ; « backlink » |
| **registre** | Le niveau de langue imposé par [CONVENTIONS.md §1.9](CONVENTIONS.md#19-registre-de-rédaction) : français formel, factuel, impersonnel. | « ton », « style » |
| **template** (masculin) | Un texte ou un format à reproduire, tel quel ou en l'adaptant, selon qu'il est impératif ou indicatif ([qualite-outils.md §6](qualite-outils.md#6-règles-de-contenu)). Terme anglais courant en français technique (§1). | « gabarit » — correct, mais moins employé en français technique ; « modèle », ambigu avec le modèle de langage |
| **lot de modifications** | Un ensemble de changements proposés fichier par fichier, que l'appelant applique. | « changeset », « patch » |

## 4. Outils

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **outil** | Une skill, un agent, un hook ou une status line. S'installe **isolément** : l'utilisateur peut le copier seul, sans le reste du dépôt, d'où l'exigence d'auto-suffisance ([CONVENTIONS.md §1.7](CONVENTIONS.md#17-auto-suffisance-des-outils)). Terme générique par défaut ; ne préciser skill, agent, hook ou status line que lorsque la distinction importe. | « unité installable isolément » — exact mais lourd, et jamais employé spontanément |
| **skill** | Un dossier `skills/<nom>/` avec son `SKILL.md`. Suite d'étapes fixes, sortie unique. | « compétence », « capacité » |
| **agent** | Un fichier `agents/<nom>.md`. Persona spécialisée dont le raisonnement se réutilise. | « sous-agent » au sens d'agent de ce dépôt (voir ci-dessous) |
| **sous-agent** | Une instance déléguée dans une session, quel que soit l'agent qu'elle exécute. À distinguer de l'artefact `agents/<nom>.md`. | — |
| **hook** | Un dossier `hooks/<nom>/` avec son `HOOK.md` et son script, déclenché par un événement de session. | « crochet », « déclencheur » |
| **hook git** | Un script de `.githooks/` déclenché par git (`pre-commit`, `commit-msg`), activé une fois par clone. Ce n'est pas un outil : il vit hors de `hooks/` et ne relève pas des conventions des hooks d'agent hôte. Toujours écrire « hook git », jamais « hook » seul, pour le distinguer d'un hook d'agent hôte. | « crochet git » |
| **status line** (féminin) | Un dossier `statuslines/claude/<nom>/` avec son `STATUSLINE.md` et son script, que Claude Code exécute à chaque rafraîchissement de sa barre d'état. Propre à Claude Code, ce que signale le dossier `claude/`. Terme anglais courant en français technique (§1). | « ligne d'état », « barre de statut » |
| **payload** (masculin) | L'objet JSON que l'agent hôte transmet sur l'entrée standard d'un hook ou d'une status line (`cwd`, `stop_hook_active`, `context_window`…). | « charge utile » — traduction littérale, opaque hors du vocabulaire des réseaux |
| **front-matter** | Le bloc YAML en tête de `SKILL.md` ou d'un fichier d'agent. | « en-tête », « métadonnées » |
| **fichier embarqué** | Un script, une feuille de style ou un document de référence livré dans le dossier d'un outil. | « asset », « ressource » |
| **donnée sensible** | Une valeur dont la divulgation ouvre un accès ou expose une personne : jeton d'accès, mot de passe, clé privée, cookie de session, contenu d'un fichier d'identifiants. Elle ne transite jamais par le contexte de l'agent ([CONVENTIONS.md §1.3](CONVENTIONS.md#13-aucun-secret-dans-le-dépôt)). « Secret » reste admis pour la même notion. | « credential » ; « token » pour un jeton d'accès — *token* désigne l'unité du modèle (§5) |

## 5. Installation et contexte

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **committer** | Enregistrer des modifications par un commit git. | « valider un commit », ambigu avec le contrôle du validateur |
| **tag** (masculin) | Une référence git nommée qui désigne un commit ; dans ce dépôt, elle marque une version ([CONTRIBUTING.md §4](CONTRIBUTING.md#4-publier-une-version)). | « étiquette » — jamais employé spontanément ; « balise », qui désigne une balise XML |
| **journal des modifications** | Le fichier `CHANGELOG.md`, une section par version, rédigé pour qui installe les outils ([CONTRIBUTING.md §4.2](CONTRIBUTING.md#42-journal-des-modifications)). « changelog » reste admis pour nommer le fichier ou le format *Keep a Changelog*. | « historique des versions », ambigu avec l'historique git |
| **Release** (féminin) | La publication GitHub associée à un tag ; ses notes reprennent la section du journal des modifications. Nom de l'objet GitHub, d'où la majuscule. | « version » pour désigner la Release seule — une version est le tag et sa Release ; « livraison » |
| **merge intelligent** | La procédure de [SETUP.md](SETUP.md) : rendre, comparer, adopter ou arbitrer, pour chaque agent hôte. | « fusion », « synchronisation » |
| **placeholder** | `{NOM_VARIABLE}`, présent dans le dépôt et remplacé lors de l'installation par sa valeur locale — par exemple `{AGENT_DIR}`. À distinguer de la forme `<...>`, valeur renseignée à l'exécution et jamais substituée ([CONVENTIONS.md §1.2](CONVENTIONS.md#12-aucun-chemin-local-en-dur)). | « marqueur », « jeton » |
| **agent hôte** | Le produit qui charge et exécute les outils : Claude Code ou Copilot CLI. Sa racine locale s'écrit `{AGENT_DIR}`. À distinguer de l'**agent**, artefact `agents/<nom>.md` de ce dépôt : ne pas l'abréger en « agent » dans un passage qui parle aussi des agents du dépôt. | « harnais », qui désigne autre chose (§2) ; « plateforme » ; « IDE » |
| **rendu** | La source du dépôt après substitution des placeholders. C'est le rendu, jamais la source brute, que l'on compare au fichier local. | — |
| **affichage** | La ligne qu'une status line écrit sur sa sortie standard et que Claude Code affiche. | « rendu », réservé à la source après substitution des placeholders |
| **conflit** | Un écart qui ne s'explique ni par les placeholders ni par une révision antérieure du dépôt : une édition locale manuelle. Seul cas qui justifie un arbitrage. | « divergence » |
| **token** (masculin) | L'unité de texte que compte le modèle de langage : remplissage du contexte, quotas, facturation. Terme anglais courant en français technique (§1). | « jeton » — traduction peu usitée ; déjà écarté comme équivalent de *placeholder*, il serait ambigu |
| **prompt** | La requête que l'utilisateur adresse à l'agent hôte dans une session. Terme anglais courant en français technique (§1). | « invite », « consigne » — la première évoque d'abord l'invite de commandes, la seconde désigne une règle et non une requête |
| **mode plan** | Le mode d'exploration en lecture seule précédant toute proposition. | « planning mode » |

## 6. Domaines couverts par les skills

Une skill introduit le vocabulaire de son domaine. Les termes qui y ont fait
l'objet d'une correction rejoignent ce document, au même titre que les autres :
l'outil s'installe isolément et ne peut pas renvoyer ici
([CONVENTIONS.md §1.7](CONVENTIONS.md#17-auto-suffisance-des-outils)), mais
c'est la relecture du dépôt qui doit empêcher la formulation écartée de
revenir.

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **paquet critique** | Un paquet dont la désactivation rend l'appareil inutilisable ou le prive de son interface ([skills/clean-android-tv](../skills/clean-android-tv/paquets.md)). | « liste rouge » — en français, être sur liste rouge signifie être **absent** de l'annuaire : le sens est inverse de celui visé |
| **accélérer**, **réduire la consommation mémoire** | Ce que fait `clean-android-tv` : libérer de la mémoire vive et raccourcir les temps de réponse. Nommer le résultat attendu, pas la métaphore. | « allègement », « alléger », « désencombrer » — évoquent un régime, et ne disent ni ce qui est fait ni pourquoi |
| **en background**, **activité en background** | L'exécution d'un processus ou d'une application hors du premier plan : service permanent, tâche planifiée, réveil périodique ([skills/clean-android-tv](../skills/clean-android-tv/SKILL.md)). Terme anglais courant en français technique pour un processus ou une application (§1). | « en fond », « travail de fond », « activité de fond » — « travail de fond » désigne en français un travail approfondi ; « en arrière-plan », correct, mais écarté au profit du terme d'usage pour un processus ou une application |
| **liste blanche d'économie d'énergie**, abrégée **liste blanche** après le premier emploi | La liste des applications exemptées des restrictions d'économie d'énergie (`cmd deviceidle whitelist`, balise `sysconfig` `<allow-in-power-save>`) : une application inscrite échappe aux réglages d'activité en background ([skills/clean-android-tv](../skills/clean-android-tv/reference-adb.md)). | « whitelist », « allowlist » hors des commandes ; « liste d'exemption » ; « optimisation de la batterie », libellé d'interface propre aux appareils sur batterie |
| ***pull request***, abrégée **PR** (féminin) | La demande d'intégration d'une branche dans une autre sur GitHub ([skills/pull-request](../skills/pull-request/SKILL.md)). Forme longue en italique au premier emploi, puis « PR ». | « demande de tirage », « demande de fusion » — traductions peu usitées (§1) ; « merge request », terme propre à GitLab |
| **branche de travail** | La branche créée pour porter un changement jusqu'à sa PR, par opposition à la **branche par défaut** du dépôt distant (`main`, `master`…). | « feature branch », « branche de fonctionnalité » — une branche de travail porte aussi une correction ou de la documentation |
| **pousser**, **un push** (masculin) | Transférer les commits locaux vers le dépôt distant par `git push`. | « pusher », « envoyer », « publier » — ce dernier est réservé à la PR et à la version |

## 7. Tics de rédaction

Des tournures qui ne sont pas des termes, mais qui reviennent et qu'il faut
couper à la relecture.

| À éviter | Pourquoi | À employer |
|---|---|---|
| **« la voie »** hors de l'idiome « ouvrir la voie » | Employé comme traduction passe-partout de *way*, il produit des tours qui n'existent pas : « voie de réouverture », « cette voie », « voie de secours ». Deux entrées du [§2](#2-harnais-et-vérification) l'écartent déjà sous « voie native » et « voie imprimée ». | Nommer la chose : « méthode », « moyen », « accès », « mécanisme », « solution de secours » |
| **Pronom sans antécédent net** — « le », « la », « en », « l' » renvoyant à une idée non nommée | Le lecteur remonte la phrase pour deviner la cible, et l'accord en genre part souvent sur le mauvais nom. | Répéter le groupe nominal, même au prix d'une redite |
| **Virgule entre deux propositions indépendantes** | Le second membre justifie ou précise le premier : la virgule ne porte pas ce lien. | Deux-points, point-virgule, ou « car » |
| **Adjectif sans support nominal** — « Android 8 et antérieur » | L'adjectif se rattache à un nom absent. | « Android 8 et les versions antérieures » |
| **« rendre » au sens de *to return*** — « rendre l'URL », « rendre le hash du commit » | Calque de l'anglais : en français, on rend ce qu'on a reçu, pas un résultat qu'on communique. Le mot entre en outre en concurrence avec **rendu**, terme fixé au [§5](#5-installation-et-contexte). Le rapport « rendu » par un sous-agent reste correct : il s'agit d'un travail remis. | « indiquer », « communiquer », « donner » |

## 8. Ajouter un terme

Un terme rejoint ce document dès qu'il a fait l'objet d'une hésitation ou d'une
correction — c'est précisément ce qui le rend utile. Renseigner les trois
colonnes, y compris les formulations écartées, puis, dans le même changement,
reprendre les documents qui emploient encore l'ancienne forme.

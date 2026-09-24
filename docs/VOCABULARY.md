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
*flag*, *root*, *cache*, *swap*. Ne pas lui imposer une traduction française
rare, qui obscurcit au lieu de clarifier.

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
| **application des règles** | Ce qui fait qu'une règle est réellement respectée — instruction écrite, DoD, script, hook, intégration continue. Ces mécanismes ne se valent pas ; les nommer directement plutôt que les classer. | « échelle de contrainte », « échelle de garantie », « barreau », « enforcement » |
| **ancrage** | Constater l'état réel avant d'agir, au lieu de le supposer. | « grounding » |
| **boucle de vérification** | Lancer → observer → corriger → relancer, jusqu'à ce que le contrôle soit au vert. | « feedback loop » |
| **dérive** | L'écart qui se creuse entre ce qui est documenté et ce qui existe. | « drift » |
| **liste de tâches** | La liste d'étapes tenue à jour pendant l'exécution d'un outil, quel que soit son affichage. Ses marqueurs sont exactement `[ ]`, `[~]`, `[x]` et `[-]`, et l'en-tête sous lequel elle s'affiche est `**Tâches**`. Nommer la fonction, jamais l'outil qui la porte : son nom varie d'une session à l'autre. | « todo list », « task list », « TodoWrite » |
| **suivi de progression** | Le fait de tenir cette liste à jour au fil des étapes. Le protocole qui le régit est au [§5 de qualite-outils.md](qualite-outils.md#5-déroulés-et-suivi-de-progression). « Suivre l'avancement » convient aussi bien. | « progress tracking » |
| **suivi par l'outil de la session** | La liste tenue à jour dans l'outil de liste de tâches de la session, quand celle-ci en expose un, et affichée par lui. | « voie native », « mode natif », « panneau intégré » |
| **suivi dans la réponse** | La liste tenue à jour dans un bloc `**Tâches**` écrit dans la réponse, quand la session n'expose aucun outil de ce type. **À égalité avec le suivi par l'outil de la session** : les deux satisfont le protocole, aucun n'est un échec. | « voie imprimée », « repli », « voie dégradée », « mode secours » |
| **checklist Markdown** | La forme concrète que prend le suivi dans la réponse : le bloc `**Tâches**`, écrit puis ré-affiché en entier à chaque changement d'état. Markdown est le nom du format : ne pas chercher à le traduire. | « checklist imprimée », « checklist en prose » ; toute formulation la qualifiant de repli — les deux suivis se valent ([qualite-outils.md §5](qualite-outils.md#5-déroulés-et-suivi-de-progression)) ; le marqueur en une seule ligne `✓ n terminé → suivant`, incompatible avec le ré-affichage intégral |
| **[mécanique]** (marqueur de checklist) | Signale qu'un item est vérifié par `scripts/validate.py`, par opposition aux items non marqués, qui relèvent du jugement ([qualite-outils.md §11](qualite-outils.md#11-checklist)). Repris de l'expression « vérifié mécaniquement » ([CLAUDE.md](../CLAUDE.md), [CONVENTIONS.md §6](CONVENTIONS.md#6-checklist--ajouter-un-document-de-fond)). | « [validé] » — contredit la case à cocher `[ ]` voisine, puisqu'il annonce un état accompli alors que `[ ]` marque ce qui reste à faire, et ne dit pas par quel moyen |

## 3. Documentation

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **table de routage** | [DOC_MAP.md](DOC_MAP.md), l'autorité qui rattache chaque tâche au document qui la régit. | « carte de documentation », « doc map », « index » |
| **découpage** | Le fait de limiter la longueur du document canonique d'un outil en sortant le détail dans des fichiers embarqués ([qualite-outils.md §3](qualite-outils.md#3-découpage--limiter-la-longueur-du-document-canonique)). | « divulgation progressive », « progressive disclosure » |
| **latitude** | Ce qu'une instruction laisse décider à l'agent, à ajuster à la fragilité de la tâche ([qualite-outils.md §4](qualite-outils.md#4-latitude-laissée-à-lagent)). | « degré de liberté », « degrees of freedom » |
| **document de fond** | Un document de `docs/` qui explique le *pourquoi* des règles, enregistré dans la table. Ce n'est pas un outil. | « document compagnon » — calque de *companion document* ; « doc annexe » |
| **lien de retour** | La ligne qui, depuis un document de fond, renvoie vers la table. | « lien retour » — composé sans préposition ; « backlink » |
| **registre** | Le niveau de langue imposé par [CONVENTIONS.md §1.9](CONVENTIONS.md#19-registre-de-rédaction) : français formel, factuel, impersonnel. | « ton », « style » |
| **lot de modifications** | Un ensemble de changements proposés fichier par fichier, que l'appelant applique. | « changeset », « patch » |

## 4. Outils

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **outil** | Une skill, un agent ou un hook. S'installe **isolément** : l'utilisateur peut le copier seul, sans le reste du dépôt, d'où l'exigence d'auto-suffisance ([CONVENTIONS.md §1.7](CONVENTIONS.md#17-auto-suffisance-des-outils)). Terme générique par défaut ; ne préciser skill, agent ou hook que lorsque la distinction importe. | « unité installable isolément » — exact mais lourd, et jamais employé spontanément |
| **skill** | Un dossier `skills/<nom>/` avec son `SKILL.md`. Suite d'étapes fixes, sortie unique. | « compétence », « capacité » |
| **agent** | Un fichier `agents/<nom>.md`. Persona spécialisée dont le raisonnement se réutilise. | « sous-agent » au sens d'agent de ce dépôt (voir ci-dessous) |
| **sous-agent** | Une instance déléguée dans une session, quel que soit l'agent qu'elle exécute. À distinguer de l'artefact `agents/<nom>.md`. | — |
| **hook** | Un dossier `hooks/<nom>/` avec son `HOOK.md` et son script, déclenché par un événement de session. | « crochet », « déclencheur » |
| **front-matter** | Le bloc YAML en tête de `SKILL.md` ou d'un fichier d'agent. | « en-tête », « métadonnées » |
| **fichier embarqué** | Un script, une feuille de style ou un document de référence livré dans le dossier d'un outil. | « asset », « ressource » |

## 5. Installation et contexte

| Terme retenu | Sens | À ne pas employer |
|---|---|---|
| **merge intelligent** | La procédure de [SETUP.md](SETUP.md) : rendre, comparer, adopter ou arbitrer. | « fusion », « synchronisation » |
| **placeholder** | `<NOM_VARIABLE>`, présent dans le dépôt et remplacé lors de l'installation par sa valeur locale. | « marqueur », « jeton » |
| **rendu** | La source du dépôt après substitution des placeholders. C'est le rendu, jamais la source brute, que l'on compare au fichier local. | — |
| **conflit** | Un écart qui ne s'explique ni par les placeholders ni par une révision antérieure du dépôt : une édition locale manuelle. Seul cas qui justifie un arbitrage. | « divergence » |
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

## 7. Tics de rédaction

Des tournures qui ne sont pas des termes, mais qui reviennent et qu'il faut
couper à la relecture.

| À éviter | Pourquoi | À employer |
|---|---|---|
| **« la voie »** hors de l'idiome « ouvrir la voie » | Employé comme traduction passe-partout de *way*, il produit des tours qui n'existent pas : « voie de réouverture », « cette voie », « voie de secours ». Deux entrées du [§2](#2-harnais-et-vérification) l'écartent déjà sous « voie native » et « voie imprimée ». | Nommer la chose : « méthode », « moyen », « accès », « mécanisme », « solution de secours » |
| **Pronom sans antécédent net** — « le », « la », « en », « l' » renvoyant à une idée non nommée | Le lecteur remonte la phrase pour deviner la cible, et l'accord en genre part souvent sur le mauvais nom. | Répéter le groupe nominal, même au prix d'une redite |
| **Virgule entre deux propositions indépendantes** | Le second membre justifie ou précise le premier : la virgule ne porte pas ce lien. | Deux-points, point-virgule, ou « car » |
| **Adjectif sans support nominal** — « Android 8 et antérieur » | L'adjectif se rattache à un nom absent. | « Android 8 et les versions antérieures » |

## 8. Ajouter un terme

Un terme rejoint ce document dès qu'il a fait l'objet d'une hésitation ou d'une
correction — c'est précisément ce qui le rend utile. Renseigner les trois
colonnes, y compris les formulations écartées, puis, dans le même changement,
reprendre les documents qui emploient encore l'ancienne forme.

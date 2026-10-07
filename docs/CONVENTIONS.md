# Conventions d'écriture des outils — skills, agents, hooks, status lines

Les règles à suivre pour **ajouter ou modifier un outil** de ce dépôt : une
**skill**, un **agent**, un **hook**, une **status line**, ou tout fichier
embarqué (script, document de référence, feuille de style). Elles reprennent les
conventions déjà en place dans `skills/` et `agents/` pour que les nouveaux
outils restent cohérents et installables.

> **Pour l'agent.** Quand l'utilisateur demande de créer ou modifier une skill,
> un agent, un hook ou une status line dans ce dépôt, appliquer les règles
> ci-dessous. En cas de contradiction avec un template par défaut, **ce document
> prévaut**. La procédure d'installation est décrite dans [SETUP.md](SETUP.md) ;
> l'inventaire de ce que fait chaque outil figure dans [README.md](../README.md).

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

---

## 1. Règles d'or

### 1.1 Arborescence et nommage

- **Une skill = un dossier** en kebab-case sous `skills/<nom>/`, contenant
  `SKILL.md` et ses fichiers embarqués. Le nom du dossier est l'identité de la
  skill : il doit être identique au champ `name` du front-matter.
- **Un agent = un fichier** `agents/<nom>.md`. Ses documents de référence
  versionnés sont placés dans `agents/docs/<nom>/`.
- **Un hook = un dossier** `hooks/<nom>/`, contenant `HOOK.md` et son script.
- **Une status line = un dossier** `statuslines/claude/<nom>/`, contenant
  `STATUSLINE.md` et `statusline.ps1`. Le dossier intermédiaire nomme l'agent
  hôte qui exécute la status line : Claude Code est aujourd'hui le seul agent
  hôte concerné ([§3.3](#33-status-lines-statuslinesclaudenom)).

L'agent est un fichier à plat, pas un dossier : c'est la structure attendue sous
`{AGENT_DIR}/agents/`, celle que [SETUP.md](SETUP.md) copie et celle que
`scripts/validate.py` contrôle. Pour Copilot CLI, l'installation le renomme
`<nom>.agent.md` ; le dépôt ne porte que `<nom>.md`.

### 1.2 Aucun chemin local en dur

Aucun fichier versionné ne doit contenir de chemin utilisateur réel
(`C:\Users\<nom>\…`, `/home/<nom>/…`). Employer un placeholder `{NOM_VARIABLE}`,
déclaré dans la table des variables de [SETUP.md](SETUP.md), que l'installation
remplace par la valeur locale. Cette règle est contrôlée mécaniquement par
`scripts/validate.py`.

La racine de l'agent hôte s'écrit `{AGENT_DIR}` : `~/.claude` pour Claude Code,
`~/.copilot` pour Copilot CLI. Un chemin propre à un seul agent hôte
(`~/.claude/…`) ne s'écrit tel quel que lorsque le propos ne concerne que cet
agent hôte.

La forme `<...>` désigne une valeur renseignée à l'exécution, par l'utilisateur
ou par l'agent (`<IP_TV>`, `<nom>`) : elle n'est jamais substituée à
l'installation.

### 1.3 Aucun secret dans le dépôt

Jetons, identifiants et paramètres personnels restent hors du dépôt. Un outil
qui a besoin d'une valeur sensible la lit au moment de son exécution, ne
l'affiche jamais, ne la consigne jamais dans un journal et ne la recopie jamais
dans un message de commit ou une description de *pull request*.

Une **donnée sensible** — jeton d'accès, mot de passe, clé privée, cookie de
session, contenu d'un fichier d'identifiants — ne transite pas non plus par le
contexte de l'agent. Un script la lit à sa source (variable d'environnement,
gestionnaire d'identifiants, fichier hors du dépôt), l'emploie, et ne transmet à
l'agent qu'un résultat non sensible : un statut, un code de sortie, une valeur
masquée. L'outil ne prescrit jamais à l'agent de lire, d'afficher ou de recopier
la valeur, ni de l'écrire dans une commande composée par l'agent : la commande
comme sa sortie entrent dans le contexte, et de là dans l'historique de la
session.

### 1.4 Aucun état produit à l'exécution n'est versionné

Ce qu'un outil génère pendant son utilisation reste dans le dossier installé,
pas dans le dépôt. Le cas type est un fichier de notes qu'un agent crée et tient
à jour sous `{AGENT_DIR}/agents/docs/<nom>/` : il est absent d'un environnement
neuf, et l'installation ne doit ni le créer, ni l'écraser, ni le supprimer.
`.gitignore` doit couvrir toute production de ce type.

### 1.5 Aucune attribution d'outil d'IA

Aucun `Co-Authored-By: Claude`, aucun « Generated with Claude Code », aucun
équivalent — ni dans un message de commit, ni dans le titre ou la description
d'une *pull request*, ni dans une sortie produite par un outil. Cette règle
prévaut sur le comportement par défaut de tout template.

### 1.6 Enregistrer tout outil ajouté

Un outil n'est pas terminé tant qu'il n'est pas repérable et installable — voir
la checklist du [§5](#5-checklist--ajouter-un-outil).

### 1.7 Auto-suffisance des outils

Un outil s'installe **isolément** : l'utilisateur peut copier
`skills/clean-android-tv/` sans le reste du dépôt. Il en découle deux règles.

- **Ne jamais référencer un chemin relatif au dépôt.** Une fois installée dans
  `{AGENT_DIR}/skills/<nom>/`, une skill n'a plus ni `docs/`, ni `README.md` à
  côté d'elle. Ne référencer que son propre dossier ou un chemin
  `{AGENT_DIR}/…`.
  Un renvoi vers `../../docs/…` ne mène plus nulle part une fois l'outil
  installé. `scripts/validate.py` refuse, dans une skill, un agent ou une
  status line, tout lien relatif qui sort du dossier de l'outil ; pour un
  agent, le périmètre admis est son fichier et `agents/docs/<nom>/`.
- **Répéter plutôt que renvoyer.** Si un outil a besoin d'une règle ou d'un
  template qui figure ailleurs dans le dépôt, le recopier dans l'outil. Cette
  duplication est délibérée : elle garantit que l'outil fonctionne seul. Elle
  doit alors être déclarée au [§1.8](#18-règles-dupliquées-à-tenir-synchrones).

### 1.8 Règles dupliquées à tenir synchrones

Certaines formulations sont volontairement présentes en plusieurs endroits, pour
des lecteurs ou des couches différentes. Ce n'est pas de la dérive. Quand l'une
est modifiée, **mettre à jour toutes ses copies dans le même changement** :

| Contenu dupliqué | Copies |
|---|---|
| Ne jamais écraser `settings.json` en bloc | [SETUP.md](SETUP.md), [hooks/README.md](../hooks/README.md) et chaque `statuslines/claude/<nom>/STATUSLINE.md` |
| Consigne de lire `AGENTS.md` avant toute action | [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md) et [.github/copilot-instructions.md](../.github/copilot-instructions.md) |
| Règle de suivi des tâches — déclencheur, marqueurs `[ ]` `[~]` `[x]` `[-]`, ré-affichage intégral, équivalence des deux suivis | [docs/qualite-outils.md](qualite-outils.md) §5 et chaque outil multi-étapes de `skills/` et `agents/` |
| Conventions de commit — préfixes admis, 50 mots au plus, sujet sans point final, absence d'attribution d'IA | `scripts/check_commit_msg.py` et [skills/pull-request/conventions-defaut.md](../skills/pull-request/conventions-defaut.md), qui ajoute la langue, la forme du sujet et le rôle du corps, que le script ne contrôle pas |
| Activation des hooks git (`git config core.hooksPath .githooks`) | [CONTRIBUTING.md](CONTRIBUTING.md), [README.md](../README.md) et `.githooks/pre-commit`, `.githooks/commit-msg` |
| Registre de rédaction et principe sur les termes anglais — garder l'anglais courant, ne pas imposer une traduction rare | ce document [§1.9](#19-registre-de-rédaction), [docs/VOCABULARY.md](VOCABULARY.md) §1 et [agents/relecture-fr.md](../agents/relecture-fr.md) |
| Commande d'enregistrement d'une status line — interpréteur, `-ExecutionPolicy Bypass`, chemin en barres obliques | `statusline_command()` de `scripts/install.py`, [SETUP.md](SETUP.md) §6 et chaque `statuslines/claude/<nom>/STATUSLINE.md` |
| Grille de qualité d'un outil — règles de [qualite-outils.md](qualite-outils.md) §§1 à 9, dont la délégation à un script, et checklist du §11 | [docs/qualite-outils.md](qualite-outils.md) et [agents/audit-outil.md](../agents/audit-outil.md) |
| Donnée sensible tenue hors du contexte de l'agent | ce document [§1.3](#13-aucun-secret-dans-le-dépôt) et [agents/audit-outil.md](../agents/audit-outil.md) |

La ligne relative à la lecture d'`AGENTS.md` tient au chargement : chaque
agent hôte lit son propre fichier d'entrée, et `AGENTS.md` doit être atteint
depuis chacun d'eux. Les lignes du suivi des tâches, des conventions de commit,
du registre, de la commande d'enregistrement, de la grille de qualité et de la
donnée sensible relèvent du
[§1.7](#17-auto-suffisance-des-outils) :
`skills/`, `agents/` et `statuslines/` sont distribués séparément et `docs/` ne
l'est pas du tout — aucun de ces ensembles ne peut renvoyer vers un autre.

### 1.9 Registre de rédaction

Cette règle s'applique à **tout** ce qui est écrit dans ce dépôt : documentation
d'outil, documents de fond, `README.md`, `AGENTS.md` et ses renvois, ce fichier
compris.

- **Français formel et neutre.** Pas de langage familier, pas de réflexion à
  voix haute, pas de commentaire sur la démarche suivie. Concis et impersonnel.
- **Énoncer des exigences, pas des anecdotes.** Écrire « cette étape est
  obligatoire », pas « ça a déjà posé problème ». Documenter ce qui est
  nécessaire, pas l'historique qui l'a motivé.
- **N'exposer que le résultat.** Ne pas raconter le raisonnement qui a mené à la
  solution.
- **Termes précis.** Le vocabulaire du projet est fixé par
  [VOCABULARY.md](VOCABULARY.md), qui fait autorité : s'y reporter avant
  d'introduire un terme, et y ajouter tout terme ayant fait l'objet d'une
  hésitation. Les termes anglais largement employés en français (*front-matter*,
  *hook*, *pull request*, *headless*, *payload*) s'écrivent tels quels ; ne pas
  imposer une traduction française peu usitée. Inversement, ne pas employer
  d'anglicisme quand le terme français est courant.
- **Tout en français.** Un document rédigé en français le reste, même si la
  demande est formulée dans une autre langue ; un nouveau document s'écrit en
  français.

Les outils de ce dépôt servent plusieurs agents hôtes — Claude Code et Copilot
CLI. Écrire « l'agent » pour désigner celui qui exécute un outil ; ne nommer
Claude ou Copilot que pour un comportement propre à l'un d'eux.

---

## 2. Skills (`skills/<nom>/SKILL.md`)

### 2.1 Front-matter

```yaml
---
name: ma-skill          # OBLIGATOIRE — kebab-case, identique au nom du dossier
description: >-         # OBLIGATOIRE — voir ci-dessous
  Ce que fait la skill, en une phrase. À utiliser quand l'utilisateur
  demande « … », fournit « … », ou pour « … ».
allowed-tools:          # FACULTATIF — moindre privilège, voir §2.2
  - Read
  - Bash(git status:*)
---
```

- **`name`** — kebab-case, strictement identique au nom du dossier. Contrôlé par
  `scripts/validate.py`.
- **`description`** — c'est la chaîne d'après laquelle l'agent décide de
  déclencher la skill. Deux parties : *ce que fait la skill*, puis les
  **conditions de déclenchement explicites**, introduites par « À utiliser
  quand… » ou « À utiliser pour… ». Les formuler avec les mots que l'utilisateur
  emploierait réellement, pas avec le vocabulaire interne de la skill. La
  première partie s'écrit **à l'infinitif** — « Convertir un document
  Markdown… », jamais « Convertit… » ni « Cette skill convertit… » : c'est la
  forme qui désigne une capacité en français, et elle est uniforme sur tout le
  dépôt.
- **`allowed-tools`** — facultatif. Il est préférable de le renseigner dans
  toute nouvelle skill dont le périmètre d'outils est identifiable. Ce champ n'est
  appliqué que par Claude Code ; Copilot CLI l'ignore, si bien qu'il ne remplace
  pas les garde-fous énoncés dans le corps de la skill.

### 2.2 `allowed-tools` — moindre privilège

Quand le champ est renseigné, y lister le **minimum** nécessaire et
**restreindre les commandes `Bash`** à un préfixe : `Bash(git status:*)`,
`Bash(adb:*)`. Ne jamais accorder un `Bash` nu, qui revient à ouvrir un
interpréteur complet, ni un interpréteur par son seul nom : `Bash(python:*)`
autorise `python -c` et donc l'exécution de tout code. Un script embarqué
s'autorise par son chemin complet ([§2.4](#24-fichiers-embarqués)). N'ajouter `Write` que si la skill écrit réellement des
fichiers.

### 2.3 Structure du corps

Après le front-matter : un titre `#` lisible, une phrase d'introduction, puis
les sections utiles dans l'ordre d'exécution.

- **`## Suivi de progression`** — pour une skill de trois étapes ou plus, en
  tête du corps et avant le déroulé, dans une section dédiée dont la forme et
  l'ordre interne sont fixés par [qualite-outils.md](qualite-outils.md) §5.
- **`## Prérequis`** — ce que la skill suppose installé, avec un renvoi vers
  [PREREQUIS.md](PREREQUIS.md) plutôt qu'une procédure recopiée.
- **`## Utilisation`** — la commande ou l'appel, dans un bloc de code.
- **`## Instructions`** — le cœur, en **étapes numérotées**, dans l'ordre
  d'exécution. Chaque étape est impérative et se suffit à elle-même. Une skill
  de **trois étapes ou plus** prescrit en outre de suivre ces étapes dans la
  liste de tâches de la session, selon le protocole de suivi de progression
  ([qualite-outils.md](qualite-outils.md) §5) : elle fournit sa propre liste de
  phases sous l'en-tête `**Tâches**` plutôt que de réénoncer la règle. Ce
  qu'elle reprend se **recopie** dans la skill, adapté à son déroulé : le
  [§1.7](#17-auto-suffisance-des-outils) interdit d'y renvoyer par un lien. Une
  skill de deux étapes en est dispensée ; une skill qui couvre plusieurs cas
  d'usage d'ampleur inégale énumère ceux qui demandent le suivi et ceux qui s'en
  passent, plutôt que de laisser l'agent rejuger la question à chaque exécution.
- **`## Règles`** — les règles impératives, sous forme de liste.
- **`## Limites`** — cas non couverts et comportements connus.

Rédiger les instructions comme des ordres adressés à l'agent (« Lire… »,
« Vérifier… », « Ne pas… »), pas comme des conseils. Mettre dans un bloc de code
toute commande ou tout template à reproduire tel quel.

### 2.4 Fichiers embarqués

Les scripts, feuilles de style et documents de référence sont placés à côté de
`SKILL.md`, dans le dossier de la skill, et sont référencés par un chemin
relatif à ce dossier. La skill appelle le script plutôt que d'en réimplanter la
logique dans ses instructions. L'installation copie le dossier entier, fichier
par fichier ([SETUP.md](SETUP.md) §3) : aucune déclaration n'est nécessaire pour
qu'un fichier embarqué soit installé.

**Script embarqué.** Un script de skill s'écrit en Python, avec la seule
bibliothèque standard : Python est déjà requis par l'installation
([PREREQUIS.md](PREREQUIS.md)). Il suit les règles du
[§7](#7-scripts-doutillage-du-dépôt-scripts) sur les identifiants, les messages
sans accents, la sortie compacte et les codes de sortie `0` / `1` / `2`. La
skill l'autorise dans `allowed-tools` par son chemin complet, seuls ses
arguments variant : `Bash(python {AGENT_DIR}/skills/<nom>/<script>.py *)`,
auquel s'ajoute `Bash(python --version)` pour la vérification du prérequis.
Claude Code compare le texte littéral de la commande à cette règle, sans
développer de chemin : la skill prescrit donc d'écrire l'appel exactement sous
la forme `python {AGENT_DIR}/skills/<nom>/<script>.py …`, sans guillemets, le
shell développant lui-même un `~` placé hors guillemets. Un `*` placé avant le
chemin complet laisserait passer tout code, comme `Bash(python:*)`. Il est
testé par `scripts/test_<script>.py` sans le matériel ni le service qu'il
pilote : un faux exécutable y rejoue des sorties enregistrées. `scripts/validate.py` en contrôle la syntaxe. Dans ce script, une
majuscule entre accolades serait prise pour un placeholder
([§1.2](#12-aucun-chemin-local-en-dur)), y compris dans une f-string : l'éviter.

---

## 3. Hooks (`hooks/<nom>/HOOK.md` + script) et status lines

### 3.1 Structure de `HOOK.md`

Pas de front-matter. Sections attendues :

- Titre `# Hook — <nom>` et un paragraphe indiquant ce qui le déclenche.
- **`## Ce qu'il fait`** — comportement, et surtout ce qu'il ne fait
  délibérément pas.
- **`## Installation`** — un renvoi vers [SETUP.md](SETUP.md) plutôt qu'une
  procédure recopiée. Signaler qu'un hook s'installe en deux temps : copie du
  script, puis enregistrement.
- **`## Configuration`** — les paramètres modifiables en tête de script.
- **`## Limites`** — modes de défaillance connus.

### 3.2 Conventions de script

- **Ne rien faire quand les conditions ne sont pas réunies.** Vérifier le
  contexte (extension de fichier, présence d'un marqueur de projet, contenu du
  payload reçu) et sortir silencieusement sinon. Un hook doit être sans
  effet là où il ne s'applique pas.
- **Un hook distribué ne bloque jamais.** Sortie 0 en toutes circonstances, les
  erreurs étant écrites sur la sortie d'erreur standard. Un hook installé
  globalement s'exécute dans tous les projets : une défaillance ne doit jamais
  interrompre le travail en cours.
- **Cas particulier : les hooks de vérification.** Un hook dont l'objet *est* de
  bloquer, comme `hooks/validate-tool/`, bloque volontairement la fin du tour
  quand son contrôle échoue. C'est la seule catégorie autorisée à le faire, et
  elle est réservée aux hooks enregistrés **localement à un dépôt**, jamais
  globalement. Un tel hook doit se prémunir contre les boucles : il plafonne le
  nombre de blocages consécutifs dans un même tour, puis se termine sans
  bloquer. Il ne bloque pas non plus en cas d'anomalie d'environnement
  (interpréteur ou dépendance absents), qui n'est pas un défaut du travail
  produit.
- **Contrat commun aux deux agents hôtes.** Un hook destiné à Claude Code et à
  Copilot CLI bloque en écrivant sur la sortie standard l'objet JSON
  `{"decision": "block", "reason": "…"}` et en se terminant avec le code 0 :
  c'est la seule forme que les deux agents reconnaissent. Le code 2, bloquant
  pour Claude Code, n'est qu'un avertissement pour Copilot CLI. La racine du
  projet se lit dans le champ `cwd` du payload, présent chez les deux
  agents, plutôt que dans une variable d'environnement propre à l'un d'eux.
- **Paramètres en tête de script**, pas dispersés dans le corps.

### 3.3 Status lines (`statuslines/claude/<nom>/`)

Une status line est un dossier dont Claude Code exécute le script à chaque
rafraîchissement de sa barre d'état. Elle est **propre à Claude Code**, ce que
signale le dossier `claude/` de son chemin : `scripts/install.py` ne l'examine
pour aucun autre agent hôte, et `scripts/validate.py` refuse sous
`statuslines/` tout dossier qui ne nomme pas un agent hôte doté de status lines
par `install.py`. L'installation ne reprend pas ce dossier intermédiaire : la cible
est `~/.claude/statuslines/<nom>/`.

- **`STATUSLINE.md`**, sans front-matter, reprend les sections de `HOOK.md`
  ([§3.1](#31-structure-de-hookmd)) : « Ce qu'elle affiche », avec ce qu'elle
  ne fait délibérément pas, « Installation », « Configuration » et « Limites ».
  Il recopie le fragment `statusLine` à enregistrer
  ([§1.7](#17-auto-suffisance-des-outils)).
- **`statusline.ps1`** lit le payload JSON sur son entrée standard et écrit une
  ligne sur sa sortie standard. Il ne fait aucun appel au modèle.
- **Elle n'échoue jamais.** Sur un payload absent, illisible ou incomplet, le
  script produit un affichage réduit et se termine avec le code 0, sans rien
  écrire sur la sortie d'erreur.
  Tout champ facultatif du payload est lu de façon tolérante.
- **Elle est sans état.** Elle n'écrit aucun fichier : elle s'exécute plusieurs
  fois par minute.
- **Compatible avec PowerShell 5.1 et 7.** Pas d'opérateur propre à
  PowerShell 7 ; fichier en ASCII, car PowerShell 5.1 lit un script sans BOM
  dans l'encodage ANSI — un caractère non ASCII se construit par son code
  (`[char]0x2502`).
- **Paramètres en tête de script** ; la variable d'environnement `NO_COLOR`
  désactive les couleurs.
- **Tests.** Chaque affichage est vérifié par `scripts/test_statusline.py`, sur
  des payloads couvrant les champs absents ou nuls.

---

## 4. Agents (`agents/<nom>.md`)

Un agent est une **manière de réfléchir** réutilisable : une persona
spécialisée, avec son propre contexte et un jeu d'outils restreint, pour une
tâche dont le raisonnement se répète alors que les données changent à chaque
fois.

Préférer une **skill** quand la tâche est une suite d'étapes fixes avec une
sortie unique — c'est le cas de la plupart des outils. Réserver l'**agent** au
cas où c'est l'analyse elle-même qui est réutilisable : `audit-docs` examine des
dépôts différents à chaque appel, mais applique toujours les mêmes critères.

### 4.1 Front-matter

```yaml
---
name: mon-agent         # OBLIGATOIRE — kebab-case, identique au nom du fichier
description: >-         # OBLIGATOIRE — ce qu'il analyse + déclencheurs explicites
  Ce que l'agent analyse et produit. À utiliser quand l'utilisateur
  demande « … », ou délègue directement à l'agent mon-agent.
tools: Read, Grep, Glob # OBLIGATOIRE — moindre privilège
---
```

- **`description`** — c'est elle qui décide de la délégation automatique. Y
  énoncer les conditions de déclenchement aussi explicitement que dans une skill,
  et, comme pour une skill, l'écrire **à l'infinitif** — « Auditer la structure
  documentaire… », jamais « Audite… » ([§2.1](#21-front-matter)).
- **`tools`** — noms d'outils simples (`Read`, `Grep`, `Glob`, `Edit`, `Write`,
  `Bash`), et non les motifs restreints à un préfixe `Bash(cmd:*)` des skills.
  Appliquer le moindre privilège : **omettre `Write`, `Edit` et `Bash` sauf
  besoin réel**. Un agent d'analyse privé d'outil d'écriture ne peut pas
  rapporter une modification qu'il n'a pas faite — c'est une garantie, pas une
  restriction subie. Ces noms sont ceux de Claude Code ; Copilot CLI les fait
  correspondre aux siens (`Read` → `read`, `Grep` et `Glob` → `search`, `Edit`
  et `Write` → `edit`, `Bash` → `execute`, `TodoWrite` → `todo`) et ignore un
  nom qu'il ne connaît pas. Les écrire sous la forme de Claude Code, qui vaut
  pour les deux agents hôtes.
- **Outil de liste de tâches** — l'accorder quand l'agent applique le protocole
  de suivi de progression ([§4.2](#42-corps)), pour que le suivi par l'outil de
  la session reste disponible là où la session l'expose. Cet outil gère une
  liste d'étapes, pas des fichiers : l'accorder ne contredit pas le moindre
  privilège d'un agent en lecture seule. Son absence n'est pas un défaut —
  l'agent écrit alors le bloc `**Tâches**` dans sa réponse, suivi équivalent et
  non repli ([qualite-outils.md](qualite-outils.md) §5) — mais l'agent doit
  nommer le suivi qui s'applique d'après les outils qu'il a réellement reçus. Le
  nom exact de l'outil dépend de la session : ne pas supposer qu'il est exposé.
- **`model`** — **ne pas renseigner** sauf raison précise et énoncée. Sans ce
  champ, l'agent hérite du modèle de la session, ce qui convient dans presque
  tous les cas.

### 4.2 Corps

Un titre `#`, une introduction courte qui pose la persona, puis les sections qui
décrivent **comment l'agent raisonne** : ses conventions, ses contrôles, ses
garde-fous, et un déroulé numéroté. La `description` du front-matter dit *quand*
l'agent intervient ; le corps dit *comment* il procède.

Un agent dont le déroulé compte **trois étapes ou plus** prescrit de suivre ce
déroulé dans la liste de tâches de la session, aux mêmes conditions qu'une skill
([§2.3](#23-structure-du-corps)) : protocole recopié et non lié, liste de phases
fournie sous l'en-tête `**Tâches**`, cas d'usage énumérés pour un agent qui en
couvre plusieurs, outil de liste accordé dans `tools`
([§4.1](#41-front-matter)), section dédiée en tête du corps et avant le déroulé.
Deux exigences s'ajoutent, propres aux sous-agents : **nommer le suivi** qui
s'applique d'après les outils accordés, et **répéter la liste terminée en tête
du rapport rendu** — l'appelant lit ce rapport, pas le déroulement du travail.
Le protocole complet est décrit dans [qualite-outils.md](qualite-outils.md) §5.

Un agent est un outil installable isolément : le
[§1.7](#17-auto-suffisance-des-outils) s'applique.

---

## 5. Checklist — ajouter un outil

Un outil n'est pas terminé tant que tout ceci n'est pas fait :

- [ ] **[README.md](../README.md)** — l'outil figure dans l'inventaire et dans
      l'arborescence, avec ses fichiers embarqués.
- [ ] **Status line** — `STATUSLINE.md` et `statusline.ps1` présents, cas
      d'affichage ajoutés à `scripts/test_statusline.py`.
- [ ] **[AGENTS.md](../AGENTS.md)** — une règle d'usage est ajoutée **uniquement**
      si l'outil doit être déclenché dans des situations précises.
- [ ] **Front-matter conforme** au [§2](#2-skills-skillsnomskillmd) ou au
      [§4](#4-agents-agentsnommd) — sans objet pour un hook ou une status
      line —, aucun chemin local en dur, moindre privilège respecté.
- [ ] **Aucun secret ni fichier produit à l'exécution** n'est versionné.
- [ ] **Aucune donnée sensible ne transite par le contexte de l'agent** : un
      script la lit et l'emploie ([§1.3](#13-aucun-secret-dans-le-dépôt)).
- [ ] **Protocole de suivi de progression** appliqué si le déroulé compte trois
      étapes ou plus — en-tête `**Tâches**` et marqueurs `[ ]` `[~]` `[x]`
      `[-]`, contrôlés par `scripts/validate.py` — ou son omission délibérément
      assumée ([qualite-outils.md](qualite-outils.md) §5).
- [ ] **`python scripts/validate.py` sort au vert.**

## 6. Checklist — ajouter un document de fond

Un document de fond explique le *pourquoi* des règles (harnais, injection de
contexte, stratégie de modèles…). Ce n'est pas un outil : rien des §§1.1 à 4 ne
s'y applique, hormis le registre de rédaction. Il n'est pas terminé tant que
tout ceci n'est pas fait :

- [ ] Il est **enregistré dans [DOC_MAP.md](DOC_MAP.md)**, dans la table
      « Où chercher », avec une entrée formulée par intention (« Avant de… »).
- [ ] Il est **atteint par la table**. `DOC_MAP.md` est le point de routage
      par intention, et tout nouveau document de fond y entre. `AGENTS.md` ne
      lie directement un document de fond que lorsqu'une de ses propres règles
      en dépend — c'est le cas de `CONVENTIONS.md`, cité par le DoD et par la
      règle de registre, de `VOCABULARY.md`, cité par le DoD, de `SETUP.md`,
      cité par la règle d'installation, et de `CONTRIBUTING.md`, cité par la
      règle git. **Ne pas ajouter à `AGENTS.md` de
      liste parallèle à celle de la table** : c'est ce que cette exigence
      prévient, pas le lien ponctuel et justifié.
- [ ] Il porte son **lien de retour**, sous son introduction :
      `Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).`
- [ ] Le **registre de rédaction** ([§1.9](#19-registre-de-rédaction)) est
      respecté.

**Ce qui est réellement contrôlé.** `scripts/validate.py` vérifie
l'enregistrement dans la table et la présence du lien de retour. Le registre de
rédaction et le placement des liens **ne sont pas** vérifiés mécaniquement : ce
sont des règles en prose, à appliquer délibérément.

---

## 7. Scripts d'outillage du dépôt (`scripts/`)

Un script de `scripts/` n'est **pas un outil** : il n'est jamais distribué vers
`{AGENT_DIR}` et rien des §§1.1 à 4 ne s'y applique, hormis les règles d'or 1.2,
1.3, 1.5 et le registre de rédaction. Il sert à l'entretien du dépôt lui-même —
`validate.py` contrôle les sources, `install.py` porte le merge intelligent de
[SETUP.md](SETUP.md), `check_commit_msg.py` contrôle les messages de commit
pour le hook git `commit-msg` et l'intégration continue, ainsi que le titre et
la description d'une *pull request* pour cette dernière
([CONTRIBUTING.md](CONTRIBUTING.md) §3), et `changelog.py` contrôle le journal
des modifications et en extrait la section d'une version
([CONTRIBUTING.md](CONTRIBUTING.md) §4.2).
Les fichiers `test_*.py`, écrits avec la seule bibliothèque standard, testent
ces contrôles, le merge intelligent d'`install.py`, l'affichage des status
lines et les scripts embarqués des skills ; toute vérification ajoutée à `validate.py` ou à `check_commit_msg.py` y
reçoit son cas volontairement cassé.

- **Python.** C'est le langage d'outillage du dépôt. PowerShell est réservé aux
  scripts de hook, où le contrat d'appel l'impose, et aux scripts de status
  line, qui ne doivent rien exiger d'autre que PowerShell 5.1, intégré à
  Windows.
- **Racine dérivée du fichier** :
  `ROOT = Path(__file__).resolve().parent.parent`. Aucun chemin local en dur
  ([§1.2](#12-aucun-chemin-local-en-dur)) ; une valeur propre à la machine est
  dérivée ou fournie par une option de ligne de commande.
- **Identifiants en anglais, textes en français.** Fonctions, variables,
  constantes, paramètres, options de ligne de commande et noms de test sont en
  anglais ; messages affichés, docstrings et commentaires restent en français.
  Les clés de la sortie `--json` d'`install.py` et ses valeurs énumérées (noms
  de classe, états de la status line) font exception : interface publique,
  elles ne changent qu'avec une version `MAJEUR`
  ([CONTRIBUTING.md](CONTRIBUTING.md) §4.1).
- **Messages sans accents.** La sortie s'affiche dans une console PowerShell,
  dont l'encodage par défaut corrompt les caractères accentués
  ([PREREQUIS.md](PREREQUIS.md)). Le vocabulaire reste celui de
  [VOCABULARY.md](VOCABULARY.md).
- **Sortie compacte.** Un récapitulatif par classe, le détail seulement pour ce
  qui appelle une suite. Un contrôle verbeux encombre le contexte et cesse
  d'être relancé.
- **Codes de sortie `0` / `1` / `2`** : `0` vert, `1` contrôle en échec ou erreur d'usage, `2`
  anomalie d'environnement — dépendance absente —, distincte d'un défaut du
  travail produit. Le code de retour porte le verdict : la session n'a pas à
  relire la sortie pour savoir s'il reste quelque chose à faire.
- **Aucune dépendance nouvelle** sans l'inscrire dans
  [PREREQUIS.md](PREREQUIS.md).
- **DoD** : le script doit avoir été **lancé sur une invocation réelle**, et
  toute vérification ajoutée doit avoir été **vue en rouge** au moins une fois
  sur un cas volontairement cassé ([AGENTS.md](../AGENTS.md), section
  « Definition of Done »).

Un script qui écrit hors du dépôt n'écrase jamais un contenu qu'il ne saurait
reconstituer : il le signale et laisse l'utilisateur trancher.

---

## 8. Référence rapide

| Aspect | Skill | Agent | Hook | Status line |
|---|---|---|---|---|
| Emplacement | `skills/<nom>/` | `agents/<nom>.md` | `hooks/<nom>/` | `statuslines/claude/<nom>/` |
| Fichier canonique | `SKILL.md` (front-matter) | le fichier lui-même (front-matter) | `HOOK.md` (sans front-matter) | `STATUSLINE.md` (sans front-matter) |
| Identité | `name` = nom du dossier | `name` = nom du fichier | nom du dossier | nom du dossier |
| Déclenchement | `description` / `/nom` | `description` ou délégation explicite | événement de session | rafraîchissement de la barre d'état |
| Restriction d'outils | `allowed-tools` (motifs restreints à un préfixe ; Claude Code seul) | `tools` (noms simples, forme Claude) | garde-fous dans le script | sans objet : aucun appel au modèle |
| Fichiers embarqués | scripts, styles, références | `agents/docs/<nom>/` | le script | `statusline.ps1` |
| Installation | copie du dossier sous `{AGENT_DIR}/skills/` | copie du fichier sous `{AGENT_DIR}/agents/`, renommé `<nom>.agent.md` pour Copilot CLI | copie **et** enregistrement, propre à chaque agent hôte | copie sous `~/.claude/statuslines/` **et** clé `statusLine` fusionnée à la main ; Claude Code seul |

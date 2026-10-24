# SETUP — installer ou mettre à jour les outils

Procédure d'installation et de mise à jour des outils de ce dépôt pour chaque
agent hôte : Claude Code et Copilot CLI. **Le dépôt est la source de vérité** :
par défaut, sa version est adoptée. Un arbitrage n'est demandé que sur un
**conflit non résoluble automatiquement** (§2).

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

> **Prérequis système** (Python ≥ 3.10, Git, `adb`, PowerShell, bibliothèque
> `pyyaml`) — dépendances logicielles que supposent installées certaines skills,
> la status line `usage-session` et l'outillage du dépôt : voir
> [PREREQUIS.md](PREREQUIS.md). Python et Git sont nécessaires au merge
> intelligent décrit ci-dessous ; les autres ne concernent qu'une skill, une
> status line ou la contribution au dépôt.

## 1. Agents hôtes, cibles et placeholders

### Agents hôtes

Seuls Claude Code et Copilot CLI sont pris en charge. Les intégrations aux IDE
ne le sont pas : certaines lisent aussi `~/.claude` ou `~/.copilot`, mais la
procédure ne repose pas sur ce comportement.

| Agent hôte | Option | `{AGENT_DIR}` | Nom d'un agent installé |
|------------|--------|---------------|-------------------------|
| Claude Code | `claude` | `~/.claude` | `<nom>.md` |
| Copilot CLI | `copilot` | `~/.copilot` | `<nom>.agent.md` — extension exigée par Copilot CLI |

Sous Windows, `~` désigne `C:\Users\<utilisateur>`.

### Cibles

| Type        | Source du dépôt         | Cible locale                                              |
|-------------|-------------------------|-----------------------------------------------------------|
| Skill       | `skills/<nom>/`         | `{AGENT_DIR}/skills/<nom>/`                               |
| Agent       | `agents/<nom>.md`       | `{AGENT_DIR}/agents/<nom>.md`, ou `<nom>.agent.md` pour Copilot CLI |
| Documents d'agent | `agents/docs/<nom>/` | `{AGENT_DIR}/agents/docs/<nom>/`                          |
| Hook        | `hooks/<nom>/`          | `{AGENT_DIR}/hooks/<nom>/` + enregistrement propre à l'agent hôte (§5) |
| Status line | `statuslines/claude/<nom>/` | `~/.claude/statuslines/<nom>/` + clé `statusLine` de `~/.claude/settings.json` (§6) ; Claude Code seul |

Le front-matter des skills et des agents est commun aux deux agents hôtes :
Copilot CLI fait correspondre les noms d'outils de Claude Code aux siens et
ignore `allowed-tools`. Seul le nom du fichier d'agent diffère.

**Non distribué.** `docs/`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `scripts/`,
`.claude/`, `.github/` et `hooks/validate-tool/` régissent le dépôt lui-même et
ne sont jamais copiés vers `{AGENT_DIR}`. Le hook `validate-tool` est délibérément
**local au dépôt** — voir
[hooks/validate-tool/HOOK.md](../hooks/validate-tool/HOOK.md).

### Placeholders substitués à l'installation

La substitution des placeholders est la **seule** différence légitime entre le
contenu d'un fichier du dépôt et celui de sa cible locale. Le dépôt contient des
placeholders `{NOM_VARIABLE}` que l'installation remplace par la valeur propre à
l'agent hôte visé.

| Placeholder | Valeur |
|-------------|--------|
| `{AGENT_DIR}` | `~/.claude` pour Claude Code, `~/.copilot` pour Copilot CLI ; le chemin absolu de la cible quand `--target` est fourni |

Tout placeholder ajouté se déclare dans la fonction `variables()` de
`scripts/install.py`, sans quoi il n'est pas substitué. La forme `<...>`
désigne une valeur renseignée à l'exécution et n'est jamais substituée.

## 2. Procédure — merge intelligent

Le merge intelligent est porté par **`scripts/install.py`**. Ne pas le
reproduire à la main, ne pas écrire de comparaison ad hoc et ne pas lire le
contenu des fichiers comparés : le script substitue les placeholders, compare
chaque fichier du dépôt à sa cible, classe les écarts, écrit ce que
l'utilisateur a confirmé et vérifie ses écritures, pour chaque agent hôte. La
session lance l'audit, transmet son résumé, recueille les choix de
l'utilisateur et lance l'écriture
([ci-dessous](#ce-qui-reste-à-la-session)).

```powershell
python scripts/install.py                          # audit : résumé court, n'écrit rien
python scripts/install.py apply --all              # écrit tous les cas sûrs
python scripts/install.py apply --confirm <id>     # écrit la mise à jour d'un seul outil
python scripts/install.py apply --confirm <id>=depot,<id>=local   # arbitre des conflits
python scripts/install.py view <id>                # fichiers à comparer, pour l'utilisateur
python scripts/install.py hunks <id>               # extrait borné de l'écart
python scripts/install.py --diff <chemin>          # résumé et identifiant d'un fichier
python scripts/install.py --scope skills,agents --agent copilot
python scripts/install.py apply --all --tool clean-android-tv
```

Le périmètre par défaut est `skills,agents,hooks,statusline`, tous outils
compris, pour les agents hôtes `claude,copilot`. Le périmètre `statusline` n'est
examiné que pour Claude Code, seul agent hôte doté de status lines. `--agent`
restreint l'installation aux agents hôtes nommés. `--tool` restreint l'examen et
l'écriture aux outils nommés, séparés par des virgules, et à celles de leurs
dépendances qui relèvent du périmètre examiné. Ces dépendances sont déclarées
dans la carte de [README.md](../README.md#dépendances-entre-outils)
([CONVENTIONS.md](CONVENTIONS.md) §1.7) ; le script signale chaque dépendance
ainsi ajoutée. `--target` permet de viser une autre racine que `{AGENT_DIR}` et
n'est admis qu'avec un seul agent hôte. Une cible dont le chemin contient une
espace oblige à appeler les scripts embarqués par un chemin entre guillemets,
forme que ne couvre plus la règle `allowed-tools` de leur skill
([CONVENTIONS.md](CONVENTIONS.md) §2.4). `--json` produit la même sortie au
format JSON. Les options `--apply`, équivalente à `apply --all`, et `--outil`,
ancien nom de `--tool`, sont obsolètes et seront retirées dans une prochaine
version `MAJEUR`.

**Chaque agent hôte est traité séparément.** Le classement, les écritures et les
conflits sont propres à chacun ; un conflit chez l'un n'empêche pas l'écriture
chez l'autre.

**Un outil s'installe d'un bloc.** Tant que l'un des conflits d'un outil n'est
pas arbitré chez un agent hôte, `apply` n'écrit aucun de ses fichiers chez cet
agent hôte, y compris ceux classés `absent`. Une skill ou un agent homonyme créé
par l'utilisateur n'est ainsi jamais complété ni modifié sans son accord.

### Ce que le script classe

| Classe | Ce que c'est | Ce que fait `apply` |
|---|---|---|
| `identique` | le fichier du dépôt, placeholders substitués, et la cible ne diffèrent pas | rien |
| `absent` | la cible n'existe pas | l'écrit, avec `--all` ou l'identifiant de l'outil |
| `obsolete` | la cible est une révision antérieure du dépôt, ou une copie manuelle dont les placeholders n'ont pas été substitués : installation intacte devenue obsolète | la remplace, avec `--all` ou l'identifiant de l'outil |
| `conflit` | l'écart ne s'explique ni par les placeholders ni par une révision : **édition locale manuelle**, ou outil de l'utilisateur portant le nom d'un outil du dépôt | rien sans `--confirm <id>=<choix>` ; `depot` sauvegarde la version locale puis la remplace, `local` la garde ; une fois chaque conflit de l'outil arbitré, ses autres fichiers sont écrits |
| `local seul` | fichier présent seulement en local, dans le dossier d'un outil du dépôt ; les outils étrangers au dépôt ne sont pas examinés | **rien**, jamais de suppression |

La version locale remplacée par le choix `depot` est sauvegardée sous
`{AGENT_DIR}/.ia-tools-backup/<horodatage>/`, en conservant son chemin relatif ;
ce dossier n'est jamais examiné.

### Ce que le script rapporte

- **Validation préalable.** Le script lance `scripts/validate.py` avant tout
  examen. Si la validation échoue, `apply` n'écrit rien. Une anomalie
  d'environnement (`pyyaml` absent) est signalée sans bloquer l'installation.
- **Résumé court**, sans contenu de fichier : une ligne par agent hôte, qui
  compte ses outils par état — `a_jour`, `a_installer`, `a_mettre_a_jour`,
  `conflit`, `illisible`, puis `installe`, `mis_a_jour` ou `echec` après
  `apply` —, puis une ligne par action à confirmer, sous un identifiant court.
  Une mise à jour donne l'outil et le nombre de fichiers concernés ; un conflit
  donne le fichier et un résumé de l'écart : nombre de blocs, lignes propres à
  chaque version, plages de lignes. Suivent, pour information, les fichiers
  illisibles, les fichiers en `local seul`, les échecs d'écriture et l'état de
  la clé `statusLine`, puis la commande `apply` à lancer.
- **Identifiants sans état stocké.** Un identifiant est tiré de l'état examiné :
  il change dès que la cible ou la source change. `apply` refait l'audit et
  refuse tout identifiant inconnu ou périmé, sans rien écrire.
- **Écritures vérifiées.** Chaque fichier écrit par `apply` est relu et comparé
  à la version du dépôt, placeholders substitués. Une écriture impossible, ou un
  fichier relu qui diffère, classe l'outil en `echec`, sans interrompre le
  traitement des autres outils. `apply` refait ensuite l'audit et affiche ce qui
  reste.
- **Contenu d'un conflit.** `view <id>` dépose la version du dépôt,
  placeholders substitués, dans un dossier temporaire hors de `{AGENT_DIR}`, et
  n'affiche que les deux chemins et la commande qui les compare dans l'éditeur.
  `hunks <id>` affiche les blocs de l'écart sans contexte, dans la limite de
  `--max-lines` lignes (40 par défaut), chacune tronquée à 160 caractères ;
  c'est la seule sortie qui cite le contenu d'un fichier.

Code de sortie : `0` si la validation n'est pas en échec — une validation
impossible en raison d'une anomalie d'environnement ne compte pas comme un
échec — et qu'aucun conflit ni échec d'écriture ne reste chez aucun agent hôte,
`1` sinon.

### Ce qui reste à la session

1. **Lancer l'audit et montrer son résumé tel quel.** Une demande qui ne précise
   ni le périmètre ni les agents hôtes (« mets à jour mes outils ») prend les
   valeurs par défaut du script.
2. **Recueillir l'accord de l'utilisateur** : `--all` pour les cas sûrs, ou les
   identifiants qu'il retient ; pour chaque conflit, son choix explicite entre
   `depot` et `local`. Pour décider, l'utilisateur compare lui-même les deux
   versions grâce à `view <id>`. `hunks <id>` ne se lance que si l'utilisateur
   demande à la session d'examiner l'écart.
3. **Lancer `apply`** avec ces choix, sans relancer l'audit : `apply` le refait
   lui-même. Pour merger écart par écart, la session reporte dans le fichier
   local, à la demande de l'utilisateur, les blocs retenus parmi ceux
   qu'affiche `hunks <id>`, par des modifications ciblées et jamais par une
   réécriture du fichier ; l'utilisateur choisit ensuite `local`. Un conflit
   arbitré par le choix `local` est de nouveau signalé à chaque audit, et le
   code de sortie vaut alors `1`.
4. **Traiter les fichiers en `local seul`** : les lister et demander l'accord de
   l'utilisateur avant toute suppression. Il peut s'agir d'une édition locale
   volontaire.
5. **Récapituler**, par agent hôte, en reprenant le résumé affiché par `apply`.

Un audit dont le code de sortie vaut `0` et qui n'affiche aucune action clôt la
procédure : il n'y a rien à confirmer ni à écrire.

## 3. Skills

`--scope skills` parcourt chaque dossier **fichier par fichier**, pas seulement
`SKILL.md` : un fichier embarqué présent uniquement dans le dépôt est classé
`absent` et ajouté par `apply` ; un fichier présent uniquement dans le dossier
local d'une skill du dépôt est classé `local seul` et jamais supprimé. Les
skills étrangères au dépôt — celles de l'utilisateur, ou celles que l'agent hôte
synchronise lui-même — ne sont pas examinées.

La conformité du front-matter — `name` identique au nom du dossier — relève de
`scripts/validate.py`, que `scripts/install.py` lance avant tout examen (§2).

## 4. Agents

`--scope agents` couvre ensemble `agents/<nom>.md` et `agents/docs/<nom>/`.
Pour Copilot CLI, le fichier d'agent est installé sous le nom `<nom>.agent.md` ;
ses documents de référence gardent leur nom. En cas de conflit portant sur un
fichier d'agent, examiner en priorité les champs `tools` et `model` : un écart
sur `tools` change les droits de l'agent, un écart sur `model` change le modèle
qui l'exécute, donc son coût et la qualité de ses réponses.

## 5. Hooks

Un hook s'installe en deux temps : la copie du script, puis l'enregistrement du
hook.

- Scripts → `{AGENT_DIR}/hooks/<nom>/`, par le merge intelligent comme
  ci-dessus.
- Enregistrement, propre à chaque agent hôte :
  - Claude Code : clé `hooks` du fichier de paramètres
    `~/.claude/settings.json`. **Ne jamais écraser `~/.claude/settings.json` en
    bloc** : n'y merger que les entrées de hook concernées.
  - Copilot CLI : fichier d'enregistrement dédié `~/.copilot/hooks/<nom>.json`.
    Copilot CLI admet aussi une clé `hooks` dans `~/.copilot/settings.json`, son
    fichier de paramètres ; le dépôt retient le fichier d'enregistrement, qui
    laisse `~/.copilot/settings.json` intact. Un fichier d'enregistrement déjà
    présent n'est pas écrasé non plus : n'y merger que les entrées de hook
    concernées.

  `scripts/install.py` **n'écrit jamais** ni le fichier de paramètres ni le
  fichier d'enregistrement : il affiche ce qui reste à faire ; l'enregistrement
  se fait à la main.

Aucun hook de ce dépôt n'est distribué aujourd'hui : `validate-tool` est local
(§1). `--scope hooks` constate cette absence et ne touche à rien.

## 6. Status lines

Chaque status line est propre à un agent hôte, nommé dans son chemin source :
`statuslines/claude/<nom>/` pour Claude Code, seul agent hôte concerné
aujourd'hui. Elle s'installe en deux temps : la copie du script, puis
l'enregistrement de la clé `statusLine`.

- Script → `~/.claude/statuslines/<nom>/`, par le merge intelligent comme
  ci-dessus. Le dossier `claude/` de la source n'est pas repris dans la cible :
  celle-ci, sous `~/.claude/`, est déjà propre à Claude Code.
- Enregistrement → clé `statusLine` de `~/.claude/settings.json`.
  `scripts/install.py` **n'écrit jamais** ce fichier : il lit la clé et lui
  attribue l'un des états `enregistree` (elle désigne une status line du
  dépôt), `absente`, `autre` (elle désigne un autre script) ou `illisible`
  (JSON invalide), puis affiche le fragment à merger. **Ne jamais écraser
  `~/.claude/settings.json` en bloc** : n'y merger que la clé `statusLine`,
  après accord de l'utilisateur quand la clé existante désigne un autre
  script. L'état de cette clé n'influe pas sur le code de sortie.

La commande du fragment a la forme suivante :

```text
pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "<chemin absolu de la cible, en barres obliques>"
```

L'interpréteur est `pwsh` s'il est présent, sinon `powershell`.
`-ExecutionPolicy Bypass` est nécessaire : sans cette option, PowerShell 5.1
refuse le script. Une mise à jour du script ne demande aucune modification de la
clé.

## 7. Après installation

- Skills et agents : le `name` apparaît dans la liste des outils à la
  **prochaine session** de l'agent hôte, pas immédiatement. Vérifier sa présence
  dans chaque agent hôte : liste des skills et des agents d'une session Claude
  Code ; commandes `/skills` et `/agent` de Copilot CLI.
- Hooks : tester le déclenchement réel. La présence du script et de son
  enregistrement ne prouve pas que le hook fonctionne.
- Status line : elle s'affiche au rafraîchissement suivant de la barre d'état,
  sans redémarrage. Vérifier qu'elle apparaît et que ses valeurs sont
  renseignées.

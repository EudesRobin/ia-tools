# SETUP — installer ou mettre à jour les outils

Procédure d'installation et de mise à jour des outils de ce dépôt pour chaque
agent hôte : Claude Code et Copilot CLI. **Le dépôt est la source de vérité** :
un outil n'admet aucune personnalisation hors des placeholders, et une édition
locale est sauvegardée, puis remplacée par la version du dépôt (§2).

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

> **Prérequis système** (Python ≥ 3.10, Git, `adb`, PowerShell, bibliothèque
> `pyyaml`) — dépendances logicielles que supposent installées certaines skills,
> la status line `usage-session` et l'outillage du dépôt : voir
> [PREREQUIS.md](PREREQUIS.md). Python et Git sont nécessaires à
> l'installation décrite ci-dessous ; les autres ne concernent qu'une skill, une
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

## 2. Procédure d'installation

L'installation est menée par **`scripts/install.py`**. Ne pas la
reproduire à la main, ne pas écrire de comparaison ad hoc et ne pas lire le
contenu des fichiers comparés : le script substitue les placeholders, compare
chaque fichier du dépôt à sa cible, classe les écarts, écrit ce que
l'utilisateur a confirmé et vérifie ses écritures, pour chaque agent hôte. La
session lance l'audit, transmet son résumé, recueille l'accord de
l'utilisateur et lance l'écriture
([ci-dessous](#ce-qui-reste-à-la-session)).

```powershell
python scripts/install.py                          # audit : résumé court, n'écrit rien
python scripts/install.py apply --all              # écrit tous les outils, éditions locales comprises
python scripts/install.py apply --confirm <id>,... # n'écrit que ces outils
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
format JSON. Les options `--apply`, `--outil` et `--diff` sont retirées depuis
la version 2.0.0 : le script les refuse et indique ce qui en tient lieu.

**Chaque agent hôte est traité séparément.** Le classement et les écritures
sont propres à chacun.

**Le dépôt l'emporte.** Un outil n'admet aucune personnalisation hors des
placeholders. `apply` traite un outil d'un bloc : il écrit ses fichiers
`absent` et `obsolete`, ainsi que ses fichiers en `conflit`, et supprime ses
fichiers en `local seul` ; la version locale d'un fichier remplacé ou supprimé
est d'abord sauvegardée. Un outil `retire` est supprimé de la même façon. Une
skill ou un agent créé par l'utilisateur sous le nom
d'un outil du dépôt est traité comme un fichier en `conflit` : sauvegardé,
puis remplacé. Pour épargner un outil,
lancer `apply --confirm` avec les seuls identifiants des autres outils ; l'outil
épargné reste signalé à chaque audit.

### Ce que le script classe

| Classe | Ce que c'est | Ce que fait `apply` |
|---|---|---|
| `identique` | le fichier du dépôt, placeholders substitués, et la cible ne diffèrent pas | rien |
| `absent` | la cible n'existe pas | l'écrit, avec `--all` ou l'identifiant de l'outil |
| `obsolete` | la cible est une révision antérieure du dépôt, ou une copie manuelle dont les placeholders n'ont pas été substitués : installation intacte devenue obsolète | la remplace, avec `--all` ou l'identifiant de l'outil |
| `conflit` | l'écart ne s'explique ni par les placeholders ni par une révision : **édition locale manuelle**, ou outil de l'utilisateur portant le nom d'un outil du dépôt | sauvegarde la version locale, puis la remplace, avec `--all` ou l'identifiant de l'outil |
| `local seul` | fichier présent seulement en local, dans le dossier d'un outil du dépôt ; les outils étrangers au dépôt ne sont pas examinés | sauvegarde le fichier, puis le supprime, avec `--all` ou l'identifiant de l'outil |
| `retire` | outil supprimé ou renommé dans le dépôt, encore présent en local, dont chaque fichier est une révision antérieure du dépôt, placeholders substitués | sauvegarde ses fichiers, puis les supprime, avec `--all` ou l'identifiant de l'outil |

La version locale d'un fichier en `conflit`, en `local seul` ou d'un outil
`retire` est sauvegardée, sous le même chemin relatif, dans
`{AGENT_DIR}/.ia-tools-backup/<horodatage>/`, avant d'être remplacée ou
supprimée ; ce dossier n'est jamais examiné. Une sauvegarde impossible laisse la
cible intacte et figure parmi les échecs d'écriture. Les dossiers devenus vides
sont supprimés.

Un outil retiré dont un fichier local ne correspond à aucune révision du dépôt
— édition locale, ou outil désormais porté par un autre dépôt — est laissé en
place et signalé pour information. La reconnaissance d'un outil retiré exige
l'historique git du dépôt ([PREREQUIS.md](PREREQUIS.md#git)) ; `--tool`
n'examine aucun outil retiré.

### Ce que le script rapporte

- **Validation préalable.** Le script lance `scripts/validate.py` avant tout
  examen. Si la validation échoue, `apply` n'écrit rien. Une anomalie
  d'environnement (`pyyaml` absent) est signalée sans bloquer l'installation.
- **Résumé court**, sans contenu de fichier : une ligne par agent hôte, qui
  compte ses outils par état — `a_jour`, `a_installer`, `a_mettre_a_jour`,
  `retire`, `conflit`, `illisible`, puis `installe`, `mis_a_jour`, `supprime`
  ou `echec` après `apply` —, puis une ligne par outil à traiter, sous un
  identifiant court, avec le nombre de fichiers concernés. Chaque fichier en
  `conflit` y est nommé, sur une ligne qui annonce sa sauvegarde et son
  remplacement ; chaque fichier à supprimer, ou le dossier d'un outil
  `retire`, sur une ligne qui annonce sa sauvegarde et sa suppression. Une
  section distincte propose l'enregistrement de la clé `statusLine`, sous un
  identifiant par status line (§6). Suivent, pour information, les fichiers
  illisibles, les outils retirés laissés en place, les échecs d'écriture,
  l'indisponibilité de l'historique git et les prérequis système absents du
  PATH pour les outils examinés, puis la commande `apply` à lancer.
- **Identifiants sans état stocké.** Un identifiant est tiré de l'état examiné :
  il change dès que l'un des fichiers locaux de l'outil change. `apply` refait
  l'audit et refuse tout identifiant inconnu ou périmé, sans rien écrire.
- **Écritures vérifiées.** Chaque fichier écrit par `apply` est relu et comparé
  à la version du dépôt, placeholders substitués. Une écriture impossible, ou un
  fichier relu qui diffère, classe l'outil en `echec`, sans interrompre le
  traitement des autres outils. `apply` refait ensuite l'audit et affiche ce qui
  reste.

Code de sortie : `0` si la validation n'est pas en échec — une validation
impossible en raison d'une anomalie d'environnement ne compte pas comme un
échec — et qu'aucun conflit ni échec d'écriture ne reste chez aucun agent hôte,
`1` sinon. Un prérequis absent ou un historique git indisponible n'influe pas
sur ce code.

### Ce qui reste à la session

1. **Lancer l'audit et montrer son résumé tel quel.** Une demande qui ne précise
   ni le périmètre ni les agents hôtes (« mets à jour mes outils ») prend les
   valeurs par défaut du script.
2. **Recueillir l'accord de l'utilisateur** sur `apply --all`, ou sur les seuls
   identifiants qu'il retient. Une demande qui prescrit déjà `apply --all` vaut
   accord. Le résumé nomme chaque fichier en conflit, dont la version locale
   sera sauvegardée, puis remplacée, et chaque fichier qui sera sauvegardé,
   puis supprimé.
3. **Lancer `apply`** — `--all`, ou `--confirm` avec les identifiants retenus —,
   sans relancer l'audit : `apply` le refait lui-même.
4. **Récapituler**, par agent hôte, en reprenant le résumé affiché par `apply`.

Un audit dont le code de sortie vaut `0` et qui n'affiche aucune action clôt la
procédure : il n'y a rien à confirmer ni à écrire.

## 3. Skills

`--scope skills` parcourt chaque dossier **fichier par fichier**, pas seulement
`SKILL.md` : un fichier embarqué présent uniquement dans le dépôt est classé
`absent` et ajouté par `apply` ; un fichier présent uniquement dans le dossier
local d'une skill du dépôt est classé `local seul`, sauvegardé, puis supprimé
par `apply` (§2). Les
skills étrangères au dépôt — celles de l'utilisateur, ou celles que l'agent hôte
synchronise lui-même — ne sont pas examinées.

La conformité du front-matter — `name` identique au nom du dossier — relève de
`scripts/validate.py`, que `scripts/install.py` lance avant tout examen (§2).

## 4. Agents

`--scope agents` couvre ensemble `agents/<nom>.md` et `agents/docs/<nom>/`.
Pour Copilot CLI, le fichier d'agent est installé sous le nom `<nom>.agent.md` ;
ses documents de référence gardent leur nom. Une édition locale d'un fichier
d'agent, de ses champs `tools` ou `model` par exemple, est remplacée comme toute
autre par la version du dépôt (§2) ; elle reste lisible dans la sauvegarde.

## 5. Hooks

Un hook s'installe en deux temps : la copie du script, puis l'enregistrement du
hook.

- Scripts → `{AGENT_DIR}/hooks/<nom>/`, par `scripts/install.py` (§2).
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

  `scripts/install.py` **n'écrit jamais** ni la clé `hooks` du fichier de
  paramètres ni le fichier d'enregistrement : il affiche ce qui reste à faire ;
  l'enregistrement se fait à la main.

Aucun hook de ce dépôt n'est distribué aujourd'hui : `validate-tool` est local
(§1). `--scope hooks` constate cette absence et ne touche à rien.

## 6. Status lines

Chaque status line est propre à un agent hôte, nommé dans son chemin source :
`statuslines/claude/<nom>/` pour Claude Code, seul agent hôte concerné
aujourd'hui. Elle s'installe en deux temps : la copie du script, puis
l'enregistrement de la clé `statusLine`.

- Script → `~/.claude/statuslines/<nom>/`, par `scripts/install.py` (§2).
  Le dossier `claude/` de la source n'est pas repris dans la cible : celle-ci,
  sous `~/.claude/`, est déjà propre à Claude Code.
- Enregistrement → clé `statusLine` de `~/.claude/settings.json`.
  `scripts/install.py` lit la clé et lui attribue l'un des états `enregistree`
  (elle désigne une status line du dépôt), `absente`, `autre` (elle désigne un
  autre script) ou `illisible` (JSON invalide). Pour les états `absente` et
  `autre`, l'audit propose une action par status line du dépôt, chacune sous
  son propre identifiant. **`--all` n'inclut jamais ces actions** : seul
  `apply --confirm <id>`, sur accord explicite de l'utilisateur, en exécute
  une, et une demande qui prescrit `apply --all` ne vaut pas cet accord. Une
  fois l'identifiant confirmé, `apply` installe la status line, sauvegarde
  `settings.json` dans `{AGENT_DIR}/.ia-tools-backup/<horodatage>/`, puis
  n'écrit dans `settings.json` que la clé `statusLine`, en conservant les
  autres clés et leur ordre, et relit le fichier ; le reformatage du fichier,
  indenté de deux espaces, est la seule autre modification. Un fichier
  `illisible` n'est jamais écrit. L'état de cette clé n'influe pas sur le code
  de sortie.

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

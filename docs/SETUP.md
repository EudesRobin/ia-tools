# SETUP — installer / mettre à jour les outils

Procédure d'installation et de mise à jour des outils de ce dépôt pour chaque
agent hôte : Claude Code et Copilot CLI. **Le dépôt est la source de vérité** :
par défaut, sa version est adoptée. Un arbitrage n'est demandé que sur un
**conflit non résoluble automatiquement** (§2).

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

> **Prérequis système** (Python ≥ 3.10, Git, `adb`, PowerShell, bibliothèque
> `pyyaml`) — outils supposés présents par certaines skills, par la status line
> `usage-session` et par l'outillage du dépôt : voir
> [PREREQUIS.md](PREREQUIS.md). Python et Git sont nécessaires au merge
> intelligent décrit ci-dessous ; les autres ne concernent qu'une skill, une
> status line ou la contribution au dépôt.

## 1. Agents hôtes, cibles et variables

### Agents hôtes

Seuls Claude Code et Copilot CLI sont pris en charge. Les intégrations aux IDE
ne le sont pas : certaines lisent aussi `~/.claude` ou `~/.copilot`, mais la
procédure ne repose pas sur ce comportement.

| Agent hôte | Option | `{AGENT_DIR}` | Nom d'un agent installé |
|------------|--------|---------------|-------------------------|
| Claude Code | `claude` | `~/.claude` | `<nom>.md` |
| Copilot CLI | `copilot` | `~/.copilot` | `<nom>.agent.md` — extension exigée par Copilot CLI |

Sous Windows, `~` = `C:\Users\<user>`.

### Cibles

| Type        | Source du dépôt         | Cible locale                                              |
|-------------|-------------------------|-----------------------------------------------------------|
| Skill       | `skills/<nom>/`         | `{AGENT_DIR}/skills/<nom>/`                               |
| Agent       | `agents/<nom>.md`       | `{AGENT_DIR}/agents/<nom>.md`, ou `<nom>.agent.md` pour Copilot CLI |
| Docs agents | `agents/docs/<nom>/`    | `{AGENT_DIR}/agents/docs/<nom>/`                          |
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

### Variables substituées à l'installation

La substitution de ces variables est la **seule** différence légitime entre le
contenu d'un fichier du dépôt et celui de sa cible locale. Le dépôt contient
des placeholders `{NOM_VARIABLE}` que l'installation remplace par la valeur
propre à l'agent hôte visé.

| Placeholder | Valeur |
|-------------|--------|
| `{AGENT_DIR}` | `~/.claude` pour Claude Code, `~/.copilot` pour Copilot CLI ; le chemin absolu de la cible quand `--target` est fourni |

Toute variable ajoutée se déclare dans la fonction `variables()` de
`scripts/install.py`, sans quoi elle n'est pas substituée. La forme `<...>`
désigne une valeur renseignée à l'exécution et n'est jamais substituée.

## 2. Procédure — merge intelligent

Le merge intelligent est porté par **`scripts/install.py`**. Ne pas le refaire,
ne pas écrire de comparaison ad hoc : le script rend les sources, compare,
classe et applique les cas sûrs, pour chaque agent hôte. Ce qui reste à la
session, c'est l'arbitrage des conflits.

```powershell
python scripts/install.py                     # audit : n'écrit rien
python scripts/install.py --apply             # écrit les cas sûrs
python scripts/install.py --diff <chemin>     # écart d'un fichier en conflit
python scripts/install.py --scope skills,agents
python scripts/install.py --agent copilot
python scripts/install.py --tool clean-android-tv --apply
python scripts/install.py --scope statusline --agent claude
```

Le périmètre par défaut est `skills,agents,hooks,statusline`, tous outils
compris, pour les agents hôtes `claude,copilot`. Le périmètre `statusline` n'est
examiné que pour Claude Code, seul agent hôte doté de status lines. `--agent` restreint l'installation aux agents
hôtes nommés. `--tool` restreint l'examen et l'écriture aux outils nommés,
séparés par des virgules. `--target` permet de viser une autre racine que
`{AGENT_DIR}` et n'est admis qu'avec un seul agent hôte. `--json` produit la
même sortie au format JSON.

**Chaque agent hôte est traité séparément.** Classes, écritures et conflits
sont établis pour chacun ; un conflit chez l'un n'empêche pas l'écriture chez
l'autre.

**Un outil s'installe d'un bloc.** Si l'un des fichiers d'un outil est en
conflit chez un agent hôte, `--apply` n'écrit aucun de ses fichiers chez cet
agent hôte, y compris ceux classés `absent`. Une skill ou un agent homonyme créé par
l'utilisateur n'est ainsi jamais complété ni modifié : le script le signale et
le laisse intact.

### Ce que le script classe

| Classe | Ce que c'est | Ce que fait `--apply` |
|---|---|---|
| `identique` | le rendu et la cible ne diffèrent pas | rien |
| `absent` | la cible n'existe pas | écrit le rendu |
| `obsolete` | la cible est le rendu d'une révision antérieure du dépôt : installation propre devenue obsolète | écrit le rendu, sans confirmation |
| `conflit` | l'écart ne s'explique ni par les variables ni par une révision : **édition locale manuelle**, ou outil homonyme de l'utilisateur | **rien**, pour aucun fichier du même outil chez cet agent hôte |
| `local seul` | fichier présent seulement en local, dans le dossier d'un outil du dépôt ; les outils étrangers au dépôt ne sont pas examinés | **rien**, jamais de suppression |

### Ce que le script rapporte

- **Validation préalable.** Le script lance `scripts/validate.py` avant tout
  examen. Si la validation échoue, `--apply` n'écrit rien. Une anomalie
  d'environnement (`pyyaml` absent) est signalée sans bloquer l'installation.
- **État de chaque outil**, par agent hôte : l'état le plus défavorable parmi
  ceux de ses fichiers — `a_jour`, `a_installer`, `a_mettre_a_jour`,
  `conflit` ou `illisible`. Après `--apply`, un outil dont les fichiers ont
  été écrits passe à `installe` ou `mis_a_jour`. Le détail par fichier n'est
  affiché que pour ce qui demande une intervention : conflits, fichiers
  illisibles, fichiers en `local seul`, échecs d'écriture.
- **Écritures vérifiées.** Chaque fichier écrit par `--apply` est relu et
  comparé au rendu. Une écriture impossible, ou un fichier relu qui diffère
  du rendu, classe l'outil en `echec`, sans interrompre le traitement des
  autres outils.

Code de sortie : `0` si la validation passe et qu'aucun conflit ni échec
d'écriture ne reste chez aucun agent hôte, `1` sinon.

### Ce qui reste à la session

1. **Confirmer le périmètre et les agents hôtes** avant la première écriture,
   puis lancer `--apply`. Une demande qui ne les précise pas (« mets à jour mes
   outils ») prend les valeurs par défaut du script.
2. **Arbitrer chaque conflit** : afficher l'écart par `--diff <chemin>` (avec
   `--agent` pour ne viser qu'un seul agent hôte), puis demander à l'utilisateur
   de choisir — adopter la version du dépôt / garder la version locale /
   fusionner écart par écart — et
   appliquer le choix. Le script n'écrit jamais un fichier en conflit.
3. **Traiter les fichiers en `local seul`** : les lister et demander l'accord de
   l'utilisateur avant toute suppression. Il peut s'agir d'une édition locale
   volontaire.
4. **Ne relancer l'audit qu'après un arbitrage** : `--apply` vérifie
   lui-même ses écritures. Chaque fichier arbitré en faveur du dépôt doit être
   classé `identique`. Un fichier gardé en version locale ou fusionné écart par
   écart reste classé `conflit`, et le code de sortie vaut alors `1`.
5. **Récapituler**, par agent hôte, en reprenant les lignes d'état par outil
   que donne la sortie, complétées du résultat de chaque arbitrage.

Un audit dont le code de sortie vaut `0` et qui ne signale aucun outil
`a_installer` ni `a_mettre_a_jour` clôt la procédure : il n'y a rien à
confirmer ni à écrire.

## 3. Skills

`--scope skills` parcourt chaque dossier **fichier par fichier**, pas seulement
`SKILL.md` : un fichier embarqué présent uniquement dans le dépôt est classé
`absent` et ajouté par `--apply` ; un fichier présent uniquement dans le dossier
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
sur ces champs change les droits de l'agent.

## 5. Hooks

Un hook s'installe en deux temps : la copie du script, puis l'enregistrement du
hook.

- Scripts → `{AGENT_DIR}/hooks/<nom>/`, par le merge intelligent comme
  ci-dessus.
- Enregistrement, propre à chaque agent hôte : clé `hooks` de
  `~/.claude/settings.json` pour Claude Code, fichier
  `~/.copilot/hooks/<nom>.json` pour Copilot CLI. **Ne jamais écraser
  `{AGENT_DIR}/settings.json` en bloc** : n'y fusionner que les entrées de hook
  concernées. Pas d'adoption automatique du fichier entier. Copilot CLI admet
  aussi une clé `hooks` dans `~/.copilot/settings.json`, son fichier de
  configuration principal ; le dépôt retient le fichier dédié, qui laisse
  `~/.copilot/settings.json` intact.
  `scripts/install.py` **n'écrit jamais** ces fichiers d'enregistrement : il
  affiche ce qui reste à faire ; l'enregistrement se fait à la main.

Aucun hook de ce dépôt n'est distribué aujourd'hui : `validate-tool` est local
(§1). `--scope hooks` le constate et ne touche à rien.

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
  (JSON invalide), puis affiche le fragment à fusionner. **Ne jamais écraser
  `~/.claude/settings.json` en bloc** : n'y fusionner que la clé `statusLine`,
  après accord de l'utilisateur quand la clé existante désigne un autre
  script. L'état de cette clé n'influe pas sur le code de sortie.

La commande du fragment se compose du chemin absolu de la cible, en barres
obliques, de l'interpréteur — `pwsh` s'il est présent, sinon `powershell` — et
de `-ExecutionPolicy Bypass`, sans lequel PowerShell 5.1 refuse le script. Une
mise à jour du script ne demande aucune modification de la clé.

## 7. Après installation

- Skills et agents : le `name` apparaît dans la liste des outils à la
  **prochaine session** de l'agent hôte, pas immédiatement. Le vérifier dans
  chaque agent hôte : liste des skills et des agents d'une session Claude Code ; commandes
  `/skills` et `/agent` de Copilot CLI.
- Hooks : tester le déclenchement réel. La présence du script et de son
  enregistrement ne prouve pas qu'il fonctionne.
- Status line : elle s'affiche au rafraîchissement suivant de la session, sans
  redémarrage. Vérifier qu'elle apparaît et que ses valeurs sont renseignées.

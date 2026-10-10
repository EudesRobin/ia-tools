# ia-tools

[![CI](https://github.com/EudesRobin/ia-tools/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/EudesRobin/ia-tools/actions/workflows/validate.yml)
[![Dependabot](https://img.shields.io/badge/Dependabot-actif-025E8C?logo=dependabot)](./.github/dependabot.yml)

Outils pour agents de code — **skills**, **agents**, **hooks** et **status
lines** — rédigés en français et publiés sous licence MIT. Le dépôt les
versionne ; un script les installe ou les met à jour pour **Claude Code**
(`~/.claude/`) et pour **Copilot CLI** (`~/.copilot/`). Les changements de
chaque version sont décrits dans le [journal des modifications](./CHANGELOG.md).

## Outils

### Skills

| Skill | Ce qu'elle fait |
|---|---|
| [`clean-android-tv`](./skills/clean-android-tv/SKILL.md) | Rend un téléviseur ou un boîtier Android TV plus réactif par adb : libère la mémoire vive en désactivant les applications préinstallées inutilisées, de façon réversible, et vérifie qu'une intervention antérieure tient toujours. Embarque `reference-adb.md`, `paquets.md` et `adb_tv.py`, script de relevés en lecture seule. |
| [`pull-request`](./skills/pull-request/SKILL.md) | Committe des modifications, crée la branche de travail, la pousse et ouvre ou met à jour la *pull request* GitHub par `gh`, selon les conventions et le template de PR du projet. Embarque `conventions-defaut.md` et `template-pr.md`, appliqués quand le projet n'en déclare aucun, et `etat_depot.py`, script en lecture seule qui relève l'état du dépôt. |
| [`setup-harness`](./skills/setup-harness/SKILL.md) | Installe la section « Harnais » — lancer / tester / vérifier — dans le fichier d'instructions d'un projet tiers (`AGENTS.md`, à défaut celui de l'agent hôte). |

### Agents

| Agent | Ce qu'il fait |
|---|---|
| [`audit-docs`](./agents/audit-docs.md) | Audite la structure documentaire d'un projet : accessibilité des règles, duplication, solidité du harnais. Produit un constat étayé et un lot de modifications à appliquer ; n'écrit rien lui-même. |
| [`audit-outil`](./agents/audit-outil.md) | Audite une skill, un agent ou un hook : qualité d'écriture, étapes à confier à un script pour réduire le coût en tokens, données sensibles exposées au contexte de l'agent. Rend un constat sourcé `fichier:ligne` et un lot de modifications proposées ; n'écrit rien lui-même. |
| [`relecture-fr`](./agents/relecture-fr.md) | Relit un document français en contexte neuf : calques de l'anglais, pronoms sans antécédent, accords, registre. Rend un constat sourcé `fichier:ligne` ; n'écrit rien lui-même. |

### Hooks

| Hook | Ce qu'il fait |
|---|---|
| [`validate-tool`](./hooks/validate-tool/HOOK.md) | Lance `scripts/validate.py` en fin de tour et empêche l'agent de rendre la main tant que le validateur est au rouge, sous Claude Code comme sous Copilot CLI. **Local au dépôt**, non distribué. |

### Status lines

Chaque status line est propre à un agent hôte, nommé dans son chemin :
`statuslines/claude/` pour Claude Code, seul agent hôte concerné aujourd'hui.

| Status line | Ce qu'elle affiche |
|---|---|
| [`usage-session`](./statuslines/claude/usage-session/STATUSLINE.md) | Modèle, effort, remplissage du contexte en pourcentage et en tokens, puis quotas 5 h et 7 jours de l'abonnement ou, en facturation API, coût estimé de la session, sur une ligne alignée à droite. Script PowerShell sans appel au modèle : aucun token consommé. |

## Arborescence

```
ia-tools/
├── AGENTS.md            instructions de dépôt, seule autorité
├── CLAUDE.md            renvoi vers AGENTS.md (point d'entrée de Claude Code)
├── README.md            ce fichier
├── CHANGELOG.md         journal des modifications, une section par version
├── LICENSE              licence MIT
├── requirements-dev.txt  dépendances Python épinglées pour contribuer
├── docs/                règles d'écriture, installation (SETUP.md), prérequis
├── skills/              une skill par sous-dossier
├── agents/              un agent par fichier ; agents/docs/<nom>/ pour ses références
├── hooks/               un hook par sous-dossier ; hooks/README.md en donne l'état
├── statuslines/claude/  une status line par sous-dossier, propre à Claude Code
├── scripts/             outillage du dépôt (réservé au développement, non installé)
│   ├── validate.py      validateur des sources
│   ├── install.py       merge intelligent vers chaque agent hôte
│   ├── check_commit_msg.py  contrôle des messages de commit
│   └── changelog.py     contrôle du journal des modifications, notes d'une version
├── tests/               tests des scripts, des scripts embarqués et des status lines
├── .githooks/           hooks git pre-commit et commit-msg (à activer dans chaque clone)
├── .claude/             config Claude Code du dépôt (enregistrement du hook local)
└── .github/             renvoi pour Copilot (copilot-instructions.md),
                         enregistrement du hook local (hooks/), intégration
                         continue (workflows/) et Dependabot (dependabot.yml)
```

## Prérequis

| Prérequis | Nécessaire pour |
|---|---|
| Un agent hôte : Claude Code ou Copilot CLI | utiliser les outils installés |
| Python ≥ 3.10 | lancer `scripts/install.py`, le script `adb_tv.py` de la skill `clean-android-tv` et le script `etat_depot.py` de la skill `pull-request` |
| Git, et le dépôt obtenu par `git clone` | reconnaître une installation obsolète : sans l'historique git, elle est signalée comme conflit |
| `adb` (platform-tools) | la skill `clean-android-tv` |
| GitHub CLI (`gh`), authentifié | la skill `pull-request`, pour pousser et ouvrir une PR |
| PowerShell 5.1 (intégré à Windows) ou 7 (`pwsh`) | la status line `usage-session` |
| `pyyaml` et PowerShell 7 (`pwsh`) | contribuer au dépôt : `scripts/validate.py` et hook `validate-tool` |

Commandes de vérification et d'installation : [PREREQUIS.md](./docs/PREREQUIS.md).

## Installation

### Par le script

```powershell
python scripts/install.py                  # audit : n'écrit rien
python scripts/install.py --apply          # installe ou met à jour, pour les deux agents hôtes
python scripts/install.py --agent copilot --apply            # un seul agent hôte
python scripts/install.py --tool clean-android-tv --apply    # un seul outil
```

La sortie donne, pour chaque agent hôte, l'état de chaque outil : à jour, à
installer, à mettre à jour ou en conflit. Le script valide d'abord les sources
du dépôt et n'écrit rien si la validation échoue ; chaque fichier écrit est relu
et comparé à la version du dépôt.

Une installation locale obsolète est remplacée par la version du dépôt. Un
fichier modifié à la main est signalé comme conflit et laissé intact. Le script
ne supprime aucun fichier local et ne modifie jamais le `settings.json` d'un
agent hôte. Une status line est donc copiée mais reste inactive tant que sa clé
n'est pas enregistrée ([ci-dessous](#activer-une-status-line)). Procédure
détaillée : [SETUP.md](./docs/SETUP.md).

Sans le script, un outil s'installe par simple copie : le dossier
`skills/<nom>/` sous `{AGENT_DIR}/skills/`, le fichier `agents/<nom>.md` sous
`{AGENT_DIR}/agents/` — renommé `<nom>.agent.md` pour Copilot CLI —, le dossier
`statuslines/claude/<nom>/` sous `~/.claude/statuslines/`. `{AGENT_DIR}` vaut
`~/.claude` pour Claude Code et `~/.copilot` pour Copilot CLI. Une copie
manuelle ne remplace pas les placeholders `{…}` qu'un outil pourrait contenir :
le script reste la méthode de référence. Une skill ou un agent apparaît à la
session suivante ; une status line, au rafraîchissement suivant une fois sa clé
enregistrée.

### Activer une status line

Une status line est facultative. `install.py --apply` copie son script avec les
autres outils, mais Claude Code ne l'affiche qu'une fois la clé `statusLine`
enregistrée dans `~/.claude/settings.json`, fichier que le script n'écrit
jamais.

1. Copier le script et obtenir la clé à enregistrer :

   ```powershell
   python scripts/install.py --scope statusline --agent claude --apply
   ```

   La sortie indique l'état de la clé `statusLine`. Si elle est absente ou
   désigne un autre script, la sortie affiche le fragment JSON à enregistrer,
   avec le chemin absolu du script sur la machine.
2. Ajouter ce fragment au premier niveau de `~/.claude/settings.json`, sans
   écraser le reste du fichier. Une clé `statusLine` existante désigne une autre
   status line : la remplacer seulement si elle n'est plus voulue.
3. Relancer la commande sans `--apply` : la clé doit être signalée
   `enregistree`. La status line apparaît au rafraîchissement suivant, sans
   redémarrage.

Retirer la clé `statusLine` désactive la status line. Ce qu'elle affiche et ses
paramètres sont décrits dans son
[STATUSLINE.md](./statuslines/claude/usage-session/STATUSLINE.md).

### Par un prompt

Dans une session de l'agent hôte ouverte à la racine du dépôt, un chemin de
fichier précédé de `@` joint ce fichier au prompt. L'agent dispose ainsi
d'emblée de la procédure d'installation, sans avoir à la rechercher dans le
dépôt, et un
modèle moins coûteux, choisi par `/model`, suffit à la dérouler. Exemple :

```text
Lis @AGENTS.md et @docs/SETUP.md, puis installe ou mets à jour les skills,
agents et hooks de ce dépôt pour Claude Code et Copilot CLI. Lance d'abord
l'audit, présente-moi le périmètre et attends ma confirmation avant --apply.
En cas de conflit, affiche l'écart avec --diff et laisse-moi choisir.
```

Ajouter `@docs/PREREQUIS.md` au prompt pour faire d'abord vérifier les prérequis :
l'agent dresse la liste de ce qui manque et n'installe rien sans accord.

## Contribuer

Les instructions du dépôt sont dans [AGENTS.md](./AGENTS.md). Les règles
d'écriture des outils sont dans [CONVENTIONS.md](./docs/CONVENTIONS.md) ;
[DOC_MAP.md](./docs/DOC_MAP.md) rattache chaque tâche au document qui la régit.
Branche protégée, commits, *pull requests*, contrôles automatiques et
publication des versions : [CONTRIBUTING.md](./docs/CONTRIBUTING.md). Activer
une fois par clone les hooks git, qui refusent un commit tant que le validateur
est au rouge ou que le message de commit est non conforme :

```powershell
git config core.hooksPath .githooks
```

Le hook `validate-tool` lance aussi le validateur en fin de tour d'une session
ouverte dans le dépôt. Lancement manuel :

```powershell
python scripts/validate.py
python tests/test_validate.py
python tests/test_check_commit_msg.py
python tests/test_changelog.py
python tests/test_install.py
python tests/test_statusline.py
python tests/test_adb_tv.py
python tests/test_etat_depot.py
```

## Licence

MIT : voir [LICENSE](./LICENSE).

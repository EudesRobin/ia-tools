# ia-tools

[![validate](https://github.com/EudesRobin/ia-tools/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/EudesRobin/ia-tools/actions/workflows/validate.yml)
[![Dependabot](https://img.shields.io/badge/Dependabot-actif-025E8C?logo=dependabot)](./.github/dependabot.yml)

Outils pour agents de code — **skills**, **agents** et **hooks** — rédigés en
français et publiés sous licence MIT. Le dépôt les versionne ; un script les
installe ou les met à jour pour **Claude Code** (`~/.claude/`) et pour
**Copilot CLI** (`~/.copilot/`).

## Outils

### Skills

| Skill | Ce qu'elle fait |
|---|---|
| [`clean-android-tv`](./skills/clean-android-tv/SKILL.md) | Rend un téléviseur Android TV plus réactif par adb : libère la mémoire vive en désactivant les applications préinstallées inutilisées, de façon réversible. Embarque `reference-adb.md` et `paquets.md`. |
| [`setup-harness`](./skills/setup-harness/SKILL.md) | Installe la section « Harnais » — lancer / tester / vérifier — dans le fichier d'instructions d'un projet tiers (`AGENTS.md`, à défaut celui de l'agent hôte). |

### Agents

| Agent | Ce qu'il fait |
|---|---|
| [`audit-docs`](./agents/audit-docs.md) | Audite la structure documentaire d'un projet : accessibilité des règles, duplication, solidité du harnais. Produit un constat étayé et un lot de modifications à appliquer ; n'écrit rien lui-même. |
| [`relecture-fr`](./agents/relecture-fr.md) | Relit un document français en contexte neuf : calques de l'anglais, pronoms sans antécédent, accords, registre. Rend un constat sourcé `fichier:ligne` ; n'écrit rien lui-même. |

### Hooks

| Hook | Ce qu'il fait |
|---|---|
| [`validate-tool`](./hooks/validate-tool/HOOK.md) | Lance `scripts/validate.py` en fin de tour et empêche l'agent de rendre la main tant que le validateur est au rouge, sous Claude Code comme sous Copilot CLI. **Local au dépôt**, non distribué. |

## Arborescence

```
ia-tools/
├── AGENTS.md            instructions de dépôt, seule autorité
├── CLAUDE.md            renvoi vers AGENTS.md (point d'entrée de Claude Code)
├── README.md            ce fichier
├── LICENSE              licence MIT
├── requirements-dev.txt  dépendances Python épinglées pour contribuer
├── docs/                règles d'écriture, installation (SETUP.md), prérequis
├── skills/              une skill par sous-dossier
├── agents/              un agent par fichier ; agents/docs/<nom>/ pour ses références
├── hooks/               un hook par sous-dossier ; hooks/README.md en donne l'état
├── scripts/             outillage du dépôt (réservé au développement, non installé)
│   ├── validate.py      validateur des sources
│   ├── install.py       merge intelligent vers chaque agent hôte
│   ├── check_commit_msg.py  contrôle des messages de commit
│   └── test_*.py        tests du validateur et du contrôle des messages
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
| Python ≥ 3.10 | lancer `scripts/install.py` |
| Git, et le dépôt obtenu par `git clone` | reconnaître une installation obsolète : sans l'historique git, elle est signalée comme conflit |
| `adb` (platform-tools) | la skill `clean-android-tv` |
| `pyyaml` et PowerShell 7 (`pwsh`) | contribuer au dépôt : `scripts/validate.py` et hook `validate-tool` |

Commandes de vérification et d'installation : [PREREQUIS.md](./docs/PREREQUIS.md).

## Installation

### Par le script

```powershell
python scripts/install.py                  # audit : n'écrit rien
python scripts/install.py --apply          # installe ou met à jour, pour les deux agents hôtes
python scripts/install.py --agent copilot --apply            # un seul agent hôte
python scripts/install.py --outil clean-android-tv --apply   # un seul outil
```

Une installation locale obsolète est remplacée par la version du dépôt. Un
fichier modifié à la main est signalé comme conflit et laissé intact. Le script
ne supprime aucun fichier local et ne modifie jamais le `settings.json` d'un
agent hôte. Procédure détaillée : [SETUP.md](./docs/SETUP.md).

Sans le script, un outil s'installe par simple copie : le dossier
`skills/<nom>/` sous `{AGENT_DIR}/skills/`, le fichier `agents/<nom>.md` sous
`{AGENT_DIR}/agents/` — renommé `<nom>.agent.md` pour Copilot CLI. `{AGENT_DIR}`
vaut `~/.claude` pour Claude Code et `~/.copilot` pour Copilot CLI. Une copie
manuelle ne remplace pas les placeholders `{…}` qu'un outil pourrait contenir :
le script reste la méthode de référence. L'outil apparaît à la session
suivante.

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
La branche `main` est protégée : toute modification passe par une *pull
request*, dont l'intégration continue lance le validateur et les tests. Activer
une fois par clone les hooks git, qui refusent un commit tant que le validateur
est au rouge ou que le message de commit est non conforme :

```powershell
git config core.hooksPath .githooks
```

Le hook `validate-tool` lance aussi le validateur en fin de tour d'une session
ouverte dans le dépôt. Lancement manuel :

```powershell
python scripts/validate.py
python scripts/test_validate.py
python scripts/test_check_commit_msg.py
```

## Licence

MIT : voir [LICENSE](./LICENSE).

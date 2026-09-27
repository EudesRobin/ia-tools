# ia-tools

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
├── docs/                règles d'écriture, installation (SETUP.md), prérequis
├── skills/              une skill par sous-dossier
├── agents/              un agent par fichier ; agents/docs/<nom>/ pour ses références
├── hooks/               un hook par sous-dossier ; hooks/README.md en donne l'état
├── scripts/             outillage du dépôt (développement seul, non installé)
│   ├── validate.py      validateur des sources
│   └── install.py       merge intelligent vers chaque agent hôte
├── .claude/             config Claude Code du dépôt (enregistrement du hook local)
└── .github/             renvoi pour Copilot (copilot-instructions.md) et
                         enregistrement du hook local (hooks/)
```

## Installation

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

Prérequis système (`adb` pour `clean-android-tv`, Python pour les scripts) :
[PREREQUIS.md](./docs/PREREQUIS.md).

## Contribuer

Les instructions du dépôt sont dans [AGENTS.md](./AGENTS.md). Les règles
d'écriture des outils sont dans [CONVENTIONS.md](./docs/CONVENTIONS.md) ;
[DOC_MAP.md](./docs/DOC_MAP.md) rattache chaque tâche au document qui la régit.
Toute modification doit passer le validateur, que le hook `validate-tool` lance
automatiquement en fin de tour :

```powershell
python scripts/validate.py
```

## Licence

MIT : voir [LICENSE](./LICENSE).

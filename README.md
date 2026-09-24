# ia-tools

Outils pour Claude Code — **skills**, **agents** et **hooks** — rédigés en
français et publiés sous licence MIT. Le dépôt les versionne ; un script les
installe ou les met à jour dans `~/.claude/`.

## Outils

### Skills

| Skill | Ce qu'elle fait |
|---|---|
| [`clean-android-tv`](./skills/clean-android-tv/SKILL.md) | Rend un téléviseur Android TV plus réactif par adb : libère la mémoire vive en désactivant les applications préinstallées inutilisées, de façon réversible. Embarque `reference-adb.md` et `paquets.md`. |
| [`setup-harness`](./skills/setup-harness/SKILL.md) | Installe la section « Harnais » — lancer / tester / vérifier — dans le `CLAUDE.md` d'un projet tiers. |

### Agents

| Agent | Ce qu'il fait |
|---|---|
| [`audit-docs`](./agents/audit-docs.md) | Audite la structure documentaire d'un projet : accessibilité des règles, duplication, solidité du harnais. Produit un constat étayé et un lot de modifications à appliquer ; n'écrit rien lui-même. |
| [`relecture-fr`](./agents/relecture-fr.md) | Relit un document français en contexte neuf : calques de l'anglais, pronoms sans antécédent, accords, registre. Rend un constat sourcé `fichier:ligne` ; n'écrit rien lui-même. |

### Hooks

| Hook | Ce qu'il fait |
|---|---|
| [`validate-tool`](./hooks/validate-tool/HOOK.md) | Lance `scripts/validate.py` en fin de tour et empêche Claude de rendre la main tant que le validateur est au rouge. **Local au dépôt**, non distribué vers `~/.claude/`. |

## Arborescence

```
ia-tools/
├── CLAUDE.md            instructions de dépôt (point d'entrée de Claude)
├── README.md            ce fichier
├── LICENSE              licence MIT
├── docs/                règles d'écriture, installation (SETUP.md), prérequis
├── skills/              une skill par sous-dossier
├── agents/              un agent par fichier ; agents/docs/<nom>/ pour ses références
├── hooks/               un hook par sous-dossier ; hooks/README.md en donne l'état
├── scripts/             outillage du dépôt (développement seul, non installé)
│   ├── validate.py      validateur des sources
│   └── install.py       merge intelligent vers ~/.claude/
└── .claude/             config Claude du dépôt (enregistrement du hook local)
```

## Installation

```powershell
python scripts/install.py            # audit : n'écrit rien
python scripts/install.py --apply    # installe ou met à jour
python scripts/install.py --outil clean-android-tv --apply   # un seul outil
```

Une installation locale obsolète est remplacée par la version du dépôt. Un
fichier modifié à la main est signalé comme conflit et laissé intact. Le script
ne supprime aucun fichier local et ne modifie jamais `~/.claude/settings.json`.
Procédure détaillée : [SETUP.md](./docs/SETUP.md).

Sans le script, un outil s'installe par simple copie : le dossier
`skills/<nom>/` sous `~/.claude/skills/`, le fichier `agents/<nom>.md` sous
`~/.claude/agents/`. L'outil apparaît à la session suivante.

Prérequis système (`adb` pour `clean-android-tv`, Python pour les scripts) :
[PREREQUIS.md](./docs/PREREQUIS.md).

## Contribuer

Les règles d'écriture des outils sont dans
[CONVENTIONS.md](./docs/CONVENTIONS.md) ; [DOC_MAP.md](./docs/DOC_MAP.md)
rattache chaque tâche au document qui la régit. Toute modification doit passer
le validateur, que le hook `validate-tool` lance automatiquement en fin de tour :

```powershell
python scripts/validate.py
```

## Licence

MIT : voir [LICENSE](./LICENSE).

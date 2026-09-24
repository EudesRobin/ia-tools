# ia-tools

Outils pour Claude Code — **skills**, **agents** et **hooks** — rédigés en
français et publiés sous licence MIT.

Le dépôt sert à **versionner** ces outils et à les **installer / mettre à jour**
sur un environnement Claude local (`~/.claude/`), en séparant ce qui se
développe et se teste dans le dépôt de ce qui s'exécute réellement dans Claude.

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

## Documentation

`CLAUDE.md` est le point d'entrée de Claude ; il route vers
[docs/DOC_MAP.md](./docs/DOC_MAP.md), qui rattache chaque tâche au
document qui la régit :

| Document | Objet |
|---|---|
| [CONVENTIONS.md](./docs/CONVENTIONS.md) | Règles d'écriture des outils — structure, front-matter, checklists. **À suivre obligatoirement.** |
| [qualite-outils.md](./docs/qualite-outils.md) | Qualité d'écriture d'un outil — concision, découpage, latitude laissée à l'agent, suivi de progression, évaluation. |
| [VOCABULARY.md](./docs/VOCABULARY.md) | Termes retenus pour le projet, et ceux à ne pas employer. |

## Utiliser une seule skill

Une skill est autonome : son dossier contient tout ce qu'elle emploie. Pour
n'utiliser que l'une d'elles, copier son dossier sous `~/.claude/skills/` :

```powershell
Copy-Item -Recurse skills/clean-android-tv "$HOME/.claude/skills/"
```

```bash
cp -r skills/clean-android-tv ~/.claude/skills/
```

La skill apparaît à la session suivante. Ses prérequis système figurent dans
[PREREQUIS.md](./docs/PREREQUIS.md) — `adb` pour `clean-android-tv`.

## Installation et mise à jour

L'installation de l'ensemble passe par un script, qui classe chaque fichier et
n'écrit que ce qui ne peut rien détruire :

```powershell
python scripts/install.py            # audit : n'écrit rien
python scripts/install.py --apply    # écrit les cas sûrs
python scripts/install.py --outil clean-android-tv --apply   # un seul outil
```

Il compare chaque outil à sa version locale et distingue deux cas :

- l'installation locale est simplement **obsolète** — elle correspond à une
  version antérieure du dépôt : la version du dépôt est adoptée automatiquement,
  sans rien demander, puisque rien d'irrécupérable n'est perdu ;
- le fichier local porte une **édition manuelle**, ou appartient à un outil
  homonyme créé par l'utilisateur : c'est un conflit ; rien n'est écrit pour
  cet outil, l'écart est présenté et l'utilisateur tranche.

Le script ne supprime jamais un fichier présent seulement en local et ne
modifie jamais `~/.claude/settings.json` : les autres outils de l'utilisateur
restent intacts.

➡️ Voir **[SETUP.md](./docs/SETUP.md)** pour la procédure détaillée.

**[PREREQUIS.md](./docs/PREREQUIS.md)** liste les outils système supposés présents
(`adb`, et pour contribuer Python, `pyyaml` et `pwsh`).

## Contribuer

Toute modification de `skills/`, `agents/` ou `hooks/` doit satisfaire le
validateur :

```powershell
python scripts/validate.py
```

Il vérifie le front-matter et ses contraintes de chargement (longueur de `name`
et de `description`, jeu de caractères, absence de balise XML), la taille du
corps, la résolution des liens relatifs, la cohérence de `docs/` et l'absence de
chemin local en dur. Il requiert `pyyaml` ([PREREQUIS.md](./docs/PREREQUIS.md)). Le
hook [`validate-tool`](./hooks/validate-tool/HOOK.md) le lance automatiquement
en fin de tour.

Les conventions d'écriture sont dans
[docs/CONVENTIONS.md](./docs/CONVENTIONS.md).

## Périmètre

Ce dépôt **ne contient pas** de configuration sensible : ni
`~/.claude/settings.json`, ni identifiants, ni historique de sessions. Le seul
fichier de configuration versionné est `.claude/settings.json`, qui déclare
uniquement le hook local.

## Licence

Publié sous licence MIT : voir [LICENSE](./LICENSE).

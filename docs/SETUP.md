# SETUP — installer / mettre à jour les outils Claude

Procédure d'installation et de mise à jour des outils de ce dépôt vers
`~/.claude/`. **Le dépôt est la source de vérité** : par défaut, sa version est
adoptée. Un arbitrage n'est demandé que sur un **conflit non résoluble
automatiquement** (§2).

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

> **Prérequis système** (`adb`, Python, `pyyaml`,
> `pwsh`) — outils hôte supposés présents par certaines skills : voir
> [PREREQUIS.md](PREREQUIS.md). Étape optionnelle, distincte de la copie vers
> `~/.claude/` ci-dessous.

## 1. Cibles et variables

Sous Windows, `~/.claude/` = `C:\Users\<user>\.claude\`.

| Type        | Source du dépôt         | Cible locale                                           |
|-------------|-------------------------|--------------------------------------------------------|
| Skill       | `skills/<nom>/`         | `~/.claude/skills/<nom>/`                              |
| Agent       | `agents/<nom>.md`       | `~/.claude/agents/<nom>.md`                            |
| Docs agents | `agents/docs/<nom>/`    | `~/.claude/agents/docs/<nom>/`                         |
| Hook        | `hooks/<nom>/`          | `~/.claude/hooks/<nom>/` + entrée dans `settings.json` |

**Non distribué.** `docs/`, `README.md`, `scripts/`, `.claude/` et
`hooks/validate-tool/` régissent le dépôt lui-même et ne partent jamais vers
`~/.claude/`. Le hook `validate-tool` est délibérément **local au dépôt** — voir
[hooks/validate-tool/HOOK.md](../hooks/validate-tool/HOOK.md).

### Variables substituées à l'installation

La substitution de ces variables est la **seule** différence légitime entre un
fichier du dépôt et sa cible locale. Le dépôt contient des placeholders
`<NOM_VARIABLE>` que l'installation remplace par la valeur locale réelle.

Aucun fichier du dépôt ne porte aujourd'hui de placeholder : le rendu du dépôt
est la source telle quelle. Toute variable ajoutée se déclare dans la fonction
`variables()` de `scripts/install.py`, sans quoi elle n'est pas substituée.

## 2. Procédure — merge intelligent

Le merge intelligent est porté par **`scripts/install.py`**. Ne pas le refaire,
ne pas écrire de comparaison ad hoc : le script rend les sources, compare,
classe et applique les cas sûrs. Ce qui reste à la session, c'est l'arbitrage
des conflits.

```powershell
python scripts/install.py                     # audit : n'écrit rien
python scripts/install.py --apply             # écrit les cas sûrs
python scripts/install.py --diff <chemin>     # écart d'un fichier en conflit
python scripts/install.py --scope skills,agents
python scripts/install.py --outil clean-android-tv --apply
```

Le périmètre par défaut est `skills,agents,hooks`, tous outils compris.
`--outil` restreint l'examen et l'écriture aux outils nommés, séparés par des
virgules. `--target` permet de viser une autre racine que `~/.claude/`, et
`--json` produit la même sortie au format JSON.

**Un outil s'installe d'un bloc.** Si l'un des fichiers d'un outil est en
conflit, `--apply` n'écrit aucun de ses fichiers, y compris ceux classés
`absent`. Une skill ou un agent homonyme créé par l'utilisateur n'est ainsi
jamais complété ni modifié : le script le signale et le laisse intact.

### Ce que le script classe

| Classe | Ce que c'est | Ce que fait `--apply` |
|---|---|---|
| `identique` | le rendu et la cible ne diffèrent pas | rien |
| `absent` | la cible n'existe pas | écrit le rendu |
| `obsolete` | la cible est le rendu d'une révision antérieure du dépôt : installation propre devenue obsolète | écrit le rendu, sans demander |
| `conflit` | l'écart ne s'explique ni par les variables ni par une révision : **édition locale manuelle**, ou outil homonyme de l'utilisateur | **rien**, pour aucun fichier du même outil |
| `local seul` | fichier présent seulement en local | **rien**, jamais de suppression |

Code de sortie : `0` si aucun conflit ne reste, `1` sinon.

### Ce qui reste à la session

1. **Confirmer le périmètre** avant la première écriture, puis lancer `--apply`.
2. **Arbitrer chaque conflit** : afficher l'écart par `--diff <chemin>`, puis
   demander à l'utilisateur de choisir — adopter le dépôt / garder la version
   locale / fusionner écart par écart — et appliquer le choix. Le script n'écrit
   jamais un fichier en conflit.
3. **Traiter les fichiers en `local seul`** : les lister et demander l'accord de
   l'utilisateur avant toute suppression. Il peut s'agir d'une édition locale
   volontaire.
4. **Récapituler** : installé / mis à jour (automatiquement) / inchangé /
   arbitré.

## 3. Skills

`--scope skills` parcourt chaque dossier **fichier par fichier**, pas seulement
`SKILL.md` : un fichier embarqué présent uniquement dans le dépôt est classé
`absent` et ajouté par `--apply`, un fichier présent uniquement en local est
classé `local seul` et jamais supprimé.

La conformité du front-matter — `name` identique au nom du dossier — relève de
`scripts/validate.py`, à lancer avant toute installation.

| Skill               | Fichiers embarqués                          |
|---------------------|---------------------------------------------|
| `clean-android-tv`  | `reference-adb.md`, `paquets.md`             |
| `setup-harness`    | —                                            |

## 4. Agents

`--scope agents` couvre `agents/<nom>.md` et `agents/docs/<nom>/` d'un seul
tenant. Sur un conflit portant sur un fichier d'agent, examiner en priorité les
champs `tools` et `model` : un écart sur ces champs change les droits de
l'agent.

| Agent          | Documents de référence |
|----------------|------------------------|
| `audit-docs`   | —                      |
| `relecture-fr` | —                      |

## 5. Hooks

Un hook s'installe en deux temps : la copie du script, puis son enregistrement.

- Scripts → `~/.claude/hooks/<nom>/`, par le merge intelligent comme ci-dessus.
- Enregistrement dans `~/.claude/settings.json` (clé `hooks`) : **ne jamais
  écraser ce fichier en bloc**, fusionner seulement les entrées de hook
  concernées. Pas d'adoption automatique du fichier entier. Le script **n'écrit
  jamais** `settings.json` : il affiche l'entrée à fusionner ; la fusion reste
  manuelle.

Aucun hook de ce dépôt n'est distribué aujourd'hui : `validate-tool` est local
(§1). `--scope hooks` le constate et ne touche à rien.

## 6. Après installation

- Skills et agents : le `name` apparaît dans la liste des outils à la
  **prochaine session**, pas immédiatement.
- Hooks : tester le déclenchement réel. La présence du script et de son entrée
  dans `settings.json` ne prouve pas qu'il fonctionne.

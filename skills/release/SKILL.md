---
name: release
description: >-
  Publier une version d'un projet GitHub : choisir le numéro selon le
  versionnage sémantique, clore la section non publiée du journal des
  modifications, la livrer par une pull request, puis poser le tag annoté après
  le merge et vérifier la Release. À utiliser quand l'utilisateur demande de
  publier une version, de faire ou de préparer une nouvelle release, de poser
  un tag de version, de mettre à jour le changelog pour une version, ou de
  reprendre une publication après le merge de sa PR.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Bash(python {AGENT_DIR}/skills/release/journal_version.py *)
  - Bash(python --version)
  - Bash(git --version)
  - Bash(gh auth status)
  - Bash(git fetch --tags origin)
  - Bash(git switch:*)
  - Bash(git pull --ff-only)
---

# Publier une version

Conduire la publication d'une version d'un projet GitHub, du journal des
modifications jusqu'à la Release : numéro, clôture du journal, *pull request*,
tag annoté après le merge, vérification. Le journal suit le format
[Keep a Changelog](https://keepachangelog.com/) et le numéro le versionnage
sémantique ; les règles de version du projet l'emportent sur la table de la
[phase 2](#2-proposer-le-numéro). La livraison par PR est confiée à la skill
`pull-request`.

## Suivi de progression — impératif

La publication est une tâche en six phases, interrompue par le merge de la PR,
fait par l'utilisateur. Créer la liste ci-dessous **avant la
[phase 1](#1-établir-létat-et-létape)**, et la ré-afficher en entier à chaque
changement d'état, avec les marqueurs `[ ]` non commencée, `[~]` en cours,
`[x]` terminée, `[-]` abandonnée, cette dernière avec une raison courte sur la
même ligne. Plusieurs `[~]` simultanées seulement si les étapes sont réellement
menées en parallèle. Quand la session expose son propre outil de liste de
tâches, c'est cet outil qui est employé et qui fait l'affichage ; sinon le bloc
est écrit dans la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état du journal, des tags et l'étape de la publication
- [ ] Phase 2 : proposer le numéro de version et obtenir l'accord
- [ ] Phase 3 : clore la version et la livrer par une PR
- [ ] Phase 4 : après le merge, vérifier la branche par défaut et son intégration continue
- [ ] Phase 5 : obtenir l'accord, puis poser et pousser le tag
- [ ] Phase 6 : vérifier la Release

Les phases 4 et 6 sont des vérifications : chacune ne passe à `[x]` qu'avec sa
preuve nommée — `[x] Phase 4 : … — CI au vert, <sha>` d'après `--check`,
`[x] Phase 6 : vérifier la Release — publiée, <URL>` d'après `--release`.

Pendant la [phase 3](#3-clore-la-version-et-la-livrer), la liste de la skill
`pull-request` s'affiche sous la ligne de la phase 3, restée `[~]` ; la liste
ci-dessus reprend à la fin de la livraison.

## Prérequis (à vérifier, ne rien installer sans accord)

- **Python 3.10 ou une version ultérieure**, pour
  [journal_version.py](journal_version.py) : `python --version`.
- **Git** et **GitHub CLI** authentifié : `git --version`, `gh auth status`.
  Non authentifié → l'utilisateur lance lui-même `gh auth login`.
- **Skill `pull-request`**, employée à la phase 3 :
  `{AGENT_DIR}/skills/pull-request/SKILL.md` doit exister. Absente →
  s'arrêter et indiquer de l'installer : `python scripts/install.py --tool
  pull-request --apply` depuis un clone d'ia-tools, à défaut une copie de son
  dossier sous `{AGENT_DIR}/skills/`.

## Utilisation

[journal_version.py](journal_version.py) est un script à **lancer**, jamais à
lire. Il n'affiche qu'une ligne `clé : valeur` par information.

```text
python {AGENT_DIR}/skills/release/journal_version.py                       # état et étape
python {AGENT_DIR}/skills/release/journal_version.py --close X.Y.Z         # clôture
python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z --output <fichier>
python {AGENT_DIR}/skills/release/journal_version.py --check X.Y.Z         # avant le tag
python {AGENT_DIR}/skills/release/journal_version.py --release <tag>       # après le tag
```

Écrire la commande exactement sous cette forme, sans guillemets et sans
développer le chemin : Claude Code compare le texte de la commande à la règle
d'`allowed-tools`. Le shell développe lui-même un `~` placé hors guillemets ;
seul Windows PowerShell 5.1 ne le fait pas, et le chemin s'y écrit développé.
Un chemin qui contient une espace s'écrit entre guillemets ; l'appel passe
alors par une demande de confirmation. `--file <journal>` désigne le journal
quand le script ne le trouve pas de lui-même ; `--base <branche>` fixe la
branche par défaut quand `origin/HEAD` ne la donne pas ; `--date AAAA-MM-JJ`
fixe la date de clôture, aujourd'hui par défaut.

Codes de sortie : `0` état relevé ou opération faite ; `1` erreur d'usage,
opération refusée ou vérification en échec, motif sur la sortie ; `2`
anomalie d'environnement — git absent, dossier hors d'un dépôt git, journal
introuvable ou illisible, écriture impossible.

## Instructions

### 1. Établir l'état et l'étape

```text
git fetch --tags origin
python {AGENT_DIR}/skills/release/journal_version.py
```

Lire aussi les règles de version du projet : fichier d'instructions de l'agent
hôte, `AGENTS.md`, guide de contribution. Le champ `etape` aiguille la suite ;
le présenter à l'utilisateur avant d'agir :

| `etape` | Suite |
|---|---|
| `nouvelle` | [phase 2](#2-proposer-le-numéro) |
| `attente_merge (X.Y.Z, …)` | la clôture n'est pas sur la branche par défaut : signaler que la PR de clôture attend son merge, et s'arrêter |
| `tag (X.Y.Z, …)` | phases 1 à 3 à `[x]`, reprendre à la [phase 4](#4-vérifier-la-branche-par-défaut-après-le-merge) |
| `release (<tag>, …)` | phases 1 à 5 à `[x]`, reprendre à la [phase 6](#6-vérifier-la-release) |
| `rien` | signaler qu'il n'y a rien à publier, et s'arrêter |

Relever en outre `prefixe_tag`, `proposition`, `rubriques_inconnues`, `liens`,
`workflow_release`, `fichiers_version`, `base` et `git_dir`.

### 2. Proposer le numéro

`proposition` applique la règle suivante, d'après la rubrique non vide la plus
forte :

| Rubriques | Incrément |
|---|---|
| Removed, Breaking, suppressions, action requise | `MAJEUR` |
| Added, Changed, Deprecated, nouveautés, modifications, obsolescences | `MINEUR` |
| Fixed, Security, Documentation, Maintenance et équivalents | `CORRECTIF` |

Une règle du projet prévaut sur cette table. `rubriques_inconnues` → classer ces
entrées, écartées du calcul, d'après leur contenu. `prefixe_tag : indetermine`
→ faire choisir à l'utilisateur la forme du tag, `X.Y.Z` ou `vX.Y.Z`, d'après
ses habitudes et le filtre de tag de ses workflows. Présenter le numéro, son
motif et le tag qui en découlera, et **obtenir l'accord de l'utilisateur**
avant toute écriture.

### 3. Clore la version et la livrer

1. Lancer `--close X.Y.Z`. Un refus → en présenter le motif, sans chercher à le
   contourner. `liens` différent de `mis a jour` et d'`aucun` → mettre à jour à
   la main les liens de fin de journal en suivant la forme des liens existants.
   La ligne `notes` confirme que la section close reprend la section non
   publiée.
2. `fichiers_version` cite un ou plusieurs fichiers → y porter le numéro
   `X.Y.Z` par `Edit`, dans le même commit que le journal.
3. Lire `{AGENT_DIR}/skills/pull-request/SKILL.md` et en mener la livraison
   complète : elle crée la branche de travail avant le commit — la clôture
   n'est jamais committée sur la branche par défaut —, committe le journal et
   les fichiers de version, puis pousse et ouvre la PR après accord de
   l'utilisateur.

La phase s'arrête à la PR publiée : indiquer à l'utilisateur que la procédure
reprend une fois la PR mergée.

### 4. Vérifier la branche par défaut après le merge

```text
git switch <base>
git pull --ff-only
python {AGENT_DIR}/skills/release/journal_version.py --check X.Y.Z
```

`verdict : pret` → [phase 5](#5-poser-le-tag), avec le `sha` relevé.
`verdict : bloque (…)` :

- `ci : aucune execution` ou exécutions `en cours` → attendre la demande de
  l'utilisateur pour relancer `--check` ; un projet sans intégration continue
  sur la branche par défaut ne passe à la phase 5 qu'avec l'accord explicite de
  l'utilisateur ;
- exécution en échec, tag existant, entrées ajoutées depuis la clôture, HEAD
  différent de `origin/<base>` → s'arrêter et présenter le motif.

### 5. Poser le tag

Présenter le tag (`<prefixe_tag>X.Y.Z`, sans préfixe si `prefixe_tag : aucun`)
et le commit visé (`sha` de `--check`), en précisant que le tag est public et
immuable. **Obtenir l'accord explicite**, puis :

```text
git tag -a <tag> <sha> -m "<tag>"
git push origin <tag>
```

### 6. Vérifier la Release

```text
python {AGENT_DIR}/skills/release/journal_version.py --release <tag>
```

- `workflow : <fichier> : en cours` → attendre la demande de l'utilisateur pour
  relancer `--release`.
- `workflow : <fichier> : failure` (ou autre échec) → en signaler la cause, ne
  pas toucher au tag.
- `release : <URL>` → la phase passe à `[x]` avec cette URL.
- `release : absente`, sans workflow qui crée la Release, ou workflow terminé
  avec succès sans l'avoir créée → écrire les notes, présenter à l'utilisateur
  le tag, le titre et les notes, puis, après accord :

  ```text
  python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z --output <git_dir>/RELEASE_NOTES.md
  gh release create <tag> --verify-tag --title <tag> --notes-file <git_dir>/RELEASE_NOTES.md
  ```

  Le fichier de notes, écrit en UTF-8 par le script, reste hors du worktree.
  Relancer ensuite `--release <tag>`.

## Règles

- Tag **annoté**, posé sur le commit vérifié par `--check`, sur la branche par
  défaut après le merge, jamais sur une branche de travail.
- Un tag publié n'est jamais déplacé ni supprimé : une erreur se corrige par
  une nouvelle version.
- Obtenir l'accord explicite de l'utilisateur sur le numéro, avant tout push et
  avant toute création de Release.
- Aucune attribution d'outil d'IA dans un commit, une PR, un tag ou une
  Release.
- Ne jamais employer `--force`, `--no-verify`, ni `git switch
  --discard-changes` ou `git switch -C`.

## Limites

- GitHub seul, par `gh` ; journal au format Keep a Changelog seul.
- Versions `X.Y.Z`, avec ou sans préfixe `v`, sans pré-version (`-rc.1`) ni
  métadonnée de build ; un tag d'une autre forme (`release-1.2.0`) n'est pas
  reconnu.
- Un dépôt qui publie plusieurs paquets, chacun avec son journal et ses tags,
  n'est pas couvert.
- Pour une version `0.y.z`, un changement incompatible incrémente `MINEUR`.
- `allowed-tools` n'est appliqué que par Claude Code, où `git tag`, `git push`
  et `gh release create` restent soumis à une demande de confirmation, comme
  les commandes de la skill `pull-request` qui ne figurent pas dans ses règles.

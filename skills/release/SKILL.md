---
name: release
description: >-
  Publier une version d'un projet GitHub ou d'un dépôt git sans dépôt
  distant : choisir le numéro selon le versionnage sémantique, clore la section
  non publiée du journal des modifications, la livrer par une pull request ou
  par un merge local, puis poser le tag annoté après le merge et vérifier la
  Release, ou le tag sans dépôt distant. À utiliser quand l'utilisateur demande
  de publier une version, de faire ou de préparer une nouvelle release, de
  poser un tag de version, de mettre à jour le changelog pour une version, ou
  de reprendre une publication après le merge de sa PR.
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
modifications jusqu'à la Release : numéro, clôture du journal, *pull request* (PR),
tag annoté après le merge, vérification. Le journal suit le format
[Keep a Changelog](https://keepachangelog.com/) et le numéro le versionnage
sémantique ; les règles de version du projet l'emportent sur la table de la
[phase 2](#2-proposer-le-numéro). La livraison est confiée à la skill
`pull-request`.

Dans un dépôt sans dépôt distant (`distant : aucun`), la même procédure
s'applique sans GitHub : la clôture est livrée par un merge local, le tag
porte les notes de la version et n'est pas poussé, et c'est le tag, faute de
Release, que vérifie la [phase 6](#6-vérifier-la-release).

## Suivi de progression — impératif

La publication est une tâche en six phases, interrompue le temps que
l'utilisateur merge la PR. Créer la liste ci-dessous **avant la
[phase 1](#1-établir-létat-et-létape)**, et la ré-afficher en entier à chaque
changement d'état, avec les marqueurs `[ ]` non commencée, `[~]` en cours, `[x]`
terminée, `[-]` abandonnée ; une étape abandonnée porte une raison courte sur la
même ligne. Plusieurs `[~]` simultanées seulement si les étapes sont réellement
menées en parallèle. Quand la session expose son propre outil de liste de
tâches, c'est cet outil qui est employé et qui fait l'affichage ; sinon le bloc
est écrit dans la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état du journal, des tags et l'étape de la publication
- [ ] Phase 2 : proposer le numéro de version et obtenir l'accord
- [ ] Phase 3 : clore la version et la livrer (PR, ou merge local)
- [ ] Phase 4 : après le merge, vérifier la branche par défaut
- [ ] Phase 5 : obtenir l'accord, puis poser le tag et le pousser s'il existe un dépôt distant
- [ ] Phase 6 : vérifier la Release, ou le tag sans dépôt distant

Les phases 4 et 6 sont des vérifications : chacune n'est marquée `[x]` qu'avec
sa preuve nommée — `[x] Phase 4 : … — l'intégration continue passe, <sha>`
d'après `--check`,
`[x] Phase 6 : vérifier la Release — publiée, <URL>` d'après `--release`.
Sans dépôt distant, ces preuves deviennent
`— sans intégration continue (dépôt sans dépôt distant), <sha>` et
`— tag annoté, notes conformes, <sha>`, et la publication n'est pas
interrompue : la phase 3 s'achève par le merge local.

Pendant la [phase 3](#3-clore-la-version-et-la-livrer), la liste de la skill
`pull-request`, quand elle en tient une, s'affiche sous la ligne de la phase 3,
restée `[~]` ; le suivi de la liste ci-dessus reprend à la fin de la livraison.

## Prérequis (à vérifier, ne rien installer sans accord)

- **Python 3.10 ou une version ultérieure**, pour
  [journal_version.py](journal_version.py) : `python --version`.
- **Git** : `git --version`.
- **GitHub CLI** authentifié, pour un projet GitHub seulement : `gh auth status`.
  Non authentifié → l'utilisateur lance lui-même `gh auth login`.
- **Skill `pull-request`**, employée à la phase 3 :
  `{AGENT_DIR}/skills/pull-request/SKILL.md` doit exister et, sans dépôt
  distant, porter la section « 8. Merger localement ». Absente → s'arrêter et
  indiquer comment l'installer ou la mettre à jour :
  `python scripts/install.py apply --all --tool pull-request` depuis un clone
  d'ia-tools, à défaut, une copie de son dossier sous `{AGENT_DIR}/skills/`.

## Utilisation

[journal_version.py](journal_version.py) est un script à **lancer**, jamais à
lire. Il n'affiche qu'une ligne `clé : valeur` par information ; seul
`--notes` sans `--output` affiche le corps de la section.

```text
python {AGENT_DIR}/skills/release/journal_version.py                       # état et étape
python {AGENT_DIR}/skills/release/journal_version.py --close X.Y.Z         # clôture
python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z [--title <tag>] --output <fichier>
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
branche par défaut quand `origin/HEAD` ne la donne pas — ou, sans dépôt
distant, quand ni `main` ni `master` n'existe ; `--tag-prefix v`
ou `--tag-prefix none` fixe le préfixe des tags quand `prefixe_tag` est
indéterminé ; `--date AAAA-MM-JJ` fixe la date de clôture, aujourd'hui par
défaut.

Codes de sortie : `0` état relevé ou opération faite ; `1` erreur d'usage,
opération refusée ou vérification en échec, motif sur la sortie d'erreur ou
dans la ligne `verdict` de `--check` et de `--release` ; `2` anomalie
d'environnement — git absent, dossier hors d'un dépôt git, journal introuvable
ou illisible, écriture impossible. Des dépôts distants dont aucun ne s'appelle
`origin` sont refusés avec le code `1` : ce cas n'est pas couvert.

## Instructions

### 1. Établir l'état et l'étape

```text
git fetch --tags origin
python {AGENT_DIR}/skills/release/journal_version.py
```

Sans dépôt distant, `git fetch` échoue faute de dépôt `origin` : l'échec est
attendu ; poursuivre avec le script, qui signale l'absence de dépôt distant par
`distant : aucun (depot local)`. Avec `distant : origin`, un échec de
`git fetch` → s'arrêter et présenter l'erreur : l'état serait relevé sur des
références périmées.

Lire aussi les règles de version du projet : fichier d'instructions de l'agent
hôte, `AGENTS.md`, guide de contribution. Le champ `etape` aiguille la suite ;
le présenter à l'utilisateur avant d'agir :

| `etape` | Suite |
|---|---|
| `nouvelle` | [phase 2](#2-proposer-le-numéro) |
| `attente_merge (X.Y.Z, …)` | la clôture est faite dans la copie de travail mais absente de la branche par défaut distante : vérifier que sa PR est ouverte — à défaut, la livrer à la [phase 3](#3-clore-la-version-et-la-livrer) — puis s'arrêter jusqu'au merge. Sans dépôt distant : la clôture n'est pas encore mergée sur la branche par défaut → la livrer à la [phase 3](#3-clore-la-version-et-la-livrer) |
| `tag (X.Y.Z, …)` | phases 1 à 3 à `[x]`, reprendre à la [phase 4](#4-vérifier-la-branche-par-défaut-après-le-merge) |
| `release (<tag>, …)` | phases 1 à 5 à `[x]`, reprendre à la [phase 6](#6-vérifier-la-release) |
| `rien` | signaler qu'il n'y a rien à publier, et s'arrêter |

Relever en outre `distant`, `prefixe_tag`, `proposition`, `rubriques_inconnues`,
`liens`, `workflow_release`, `fichiers_version`, `base` et `git_dir`.
`base : indeterminee` → demander la branche par défaut à l'utilisateur, puis
passer `--base` à chaque appel suivant du script.

### 2. Proposer le numéro

`proposition` applique la règle suivante, d'après la rubrique non vide la plus
forte :

| Rubriques | Incrément |
|---|---|
| Removed, Breaking, suppressions, action requise et équivalents | `majeur` |
| Added, Changed, Deprecated, nouveautés, modifications, obsolescences et équivalents | `mineur` |
| Fixed, Security, Documentation, Maintenance et équivalents | `correctif` |

Une règle du projet prévaut sur cette table. `rubriques_inconnues` → classer d'après
leur contenu les entrées de ces rubriques, écartées du calcul. `prefixe_tag : indetermine`
→ faire choisir à l'utilisateur la forme du tag, `X.Y.Z` ou `vX.Y.Z`, d'après les usages du projet et le filtre de tag de ses workflows, puis passer
`--tag-prefix` à chaque appel suivant du script. Présenter le numéro, son
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
3. Lire `{AGENT_DIR}/skills/pull-request/SKILL.md` et mener la livraison
   complète que cette skill décrit : la skill crée la branche de travail avant
   le commit — la clôture
   n'est jamais committée sur la branche par défaut —, committe le journal et
   les fichiers de version, puis pousse et ouvre la PR après accord de
   l'utilisateur. Avec `distant : aucun`, mener à la place la livraison locale
   de cette skill, qui merge la branche de travail sur la branche par défaut.

La phase s'arrête à la PR publiée : indiquer à l'utilisateur que la procédure
reprend une fois la PR mergée. Sans dépôt distant, poursuivre directement à la
[phase 4](#4-vérifier-la-branche-par-défaut-après-le-merge).

### 4. Vérifier la branche par défaut après le merge

```text
git switch <base>
git pull --ff-only
python {AGENT_DIR}/skills/release/journal_version.py --check X.Y.Z
```

Sans dépôt distant, omettre `git pull --ff-only` : `--check` ne compare pas
HEAD à `origin` et affiche `ci : sans objet (depot local)`.

`verdict : pret` → [phase 5](#5-poser-le-tag), avec le `sha` relevé.
`verdict : bloque (…)` :

- `ci : aucune execution`, ou `ci` avec un nombre non nul d'exécutions
  `en cours` → attendre la demande de l'utilisateur pour relancer `--check`.
  Pour un projet sans intégration continue sur la branche par défaut, la
  publication ne passe à la phase 5 qu'avec l'accord explicite de
  l'utilisateur, la preuve de la phase 4 devenant
  `— sans intégration continue, accord de l'utilisateur, <sha>` ;
- branche courante différente de la branche par défaut, ou HEAD différent de
  `origin/<base>` → reprendre `git switch <base>`, puis `git pull --ff-only`
  s'il existe un dépôt distant ;
- `modifications non committees` → le journal lu ne serait pas celui de HEAD :
  s'arrêter et présenter les fichiers en cause ;
- `ci` avec un nombre non nul d'`echec`, `ci : indeterminee (…)`, version
  absente du journal, tag existant, entrées ajoutées depuis la clôture, branche
  par défaut indéterminée → s'arrêter et présenter le motif.

### 5. Poser le tag

Présenter le tag (`<prefixe_tag>X.Y.Z`, sans préfixe si `prefixe_tag : aucun`)
et le commit visé (`sha` de `--check`), en précisant que le tag est immuable
et, s'il est poussé, public. **Obtenir l'accord explicite**, puis :

```text
git tag -a <tag> <sha> -m "<tag>"
git push origin <tag>
```

Sans dépôt distant, le tag porte les notes de la version, faute de Release, et
n'est pas poussé. Écrire d'abord les notes, précédées du tag en titre, puis les
présenter avec le tag et le `sha` avant de demander l'accord. Le script les
écrit en UTF-8 — une redirection de Windows PowerShell 5.1 écrirait de
l'UTF-16 —, et `--cleanup=verbatim` conserve les lignes de titre `###`, que git
prendrait pour des commentaires et retirerait :

```text
python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z --title <tag> --output <git_dir>/RELEASE_NOTES.md
git tag -a <tag> <sha> --cleanup=verbatim -F <git_dir>/RELEASE_NOTES.md
```

### 6. Vérifier la Release

```text
python {AGENT_DIR}/skills/release/journal_version.py --release <tag>
```

Sans dépôt distant, le script vérifie le tag : `annote`, `sur_base`, `notes`,
puis `verdict`. `verdict : conforme` → la phase passe à `[x]`
(`— tag annoté, notes conformes, <sha>`). `verdict : ecart` → présenter la
ligne en défaut à l'utilisateur et le laisser trancher, sans toucher au tag.

Avec un dépôt distant :

- `workflow : <fichier> : en cours` ou `aucune execution` → attendre la
  demande de l'utilisateur pour relancer `--release`.
- `workflow : <fichier> : failure` (ou autre échec) → en signaler la cause, ne
  pas toucher au tag.
- `workflow : … : indetermine` ou `release : indeterminee (gh)` → signaler que
  GitHub n'a pas répondu, et relancer à la demande de l'utilisateur.
- `release : <URL>` → la phase passe à `[x]` avec cette URL.
- `release : <URL> (brouillon)` → signaler à l'utilisateur que la Release est
  en brouillon ; la phase reste `[~]` jusqu'à sa publication.
- `release : absente`, alors qu'aucun workflow ne crée la Release ou que ce
  workflow s'est terminé avec succès sans la créer → écrire les notes dans un
  fichier hors du worktree, en UTF-8 :

  ```text
  python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z --output <git_dir>/RELEASE_NOTES.md
  ```

  Présenter à l'utilisateur le tag, le titre et les notes, puis, après accord :

  ```text
  gh release create <tag> --verify-tag --title <tag> --notes-file <git_dir>/RELEASE_NOTES.md
  ```

  Relancer ensuite `--release <tag>`.

## Règles

- Tag **annoté**, posé sur le commit vérifié par `--check`, sur la branche par
  défaut après le merge, jamais sur une branche de travail.
- Un tag de version posé n'est jamais déplacé ni supprimé : une erreur se
  corrige par une nouvelle version.
- Obtenir l'accord explicite de l'utilisateur sur le numéro, avant tout tag,
  avant tout push et avant toute création de Release.
- Aucune attribution d'outil d'IA dans un commit, une PR, un tag ou une
  Release.
- Ne jamais employer `--force`, `--no-verify`, `git switch --discard-changes`
  ni `git switch -C`.

## Limites

- Sont couverts GitHub, par `gh`, et le dépôt sans dépôt distant ; GitLab,
  Bitbucket et Azure DevOps ne le sont pas, ni un dépôt dont les dépôts
  distants ne comptent aucun `origin`. Journal au format Keep a Changelog seul.
- Versions `X.Y.Z`, avec ou sans préfixe `v`, sans *pre-release* (`-rc.1`) ni
  métadonnée de build ; un tag d'une autre forme (`release-1.2.0`) n'est pas
  reconnu.
- Un dépôt qui publie plusieurs paquets, chacun avec son journal et ses tags,
  n'est pas couvert.
- Pour une version `0.y.z`, un changement incompatible incrémente `MINEUR`.
- `allowed-tools` n'est appliqué que par Claude Code, où `git tag`, `git push`
  et `gh release create` restent soumis à une demande de confirmation, comme
  les commandes de la skill `pull-request` absentes des règles
  d'`allowed-tools` de la présente skill.

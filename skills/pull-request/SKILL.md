---
name: pull-request
description: Committer des modifications, créer la branche de travail, la pousser et ouvrir ou mettre à jour la pull request GitHub par gh, en appliquant les conventions de commit et le template de PR du projet. À utiliser quand l'utilisateur demande de committer, de faire un commit, de créer une branche pour ses modifications, de pousser et d'ouvrir une pull request (PR), ou de reprendre la description d'une PR.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash(git:*)
  - Bash(gh:*)
---

# Committer et ouvrir une pull request

Mener des modifications locales jusqu'à une *pull request* GitHub : commit,
branche de travail, push, puis création ou mise à jour de la PR par `gh`. Les
conventions appliquées sont celles du projet ; à défaut, celles de
[conventions-defaut.md](conventions-defaut.md). Le merge de la PR est hors du
périmètre de la skill.

## Suivi de progression — impératif pour la livraison complète

Cas d'usage et suivi :

- **Commit seul** — « committe », « fais un commit » : [étapes 1](#1-établir-létat)
  à [4](#4-committer), sans liste de tâches.
- **Livraison complète** — branche, commits, push et PR, ou mise à jour d'une PR
  existante : tâche en sept phases ; la règle de suivi des tâches s'applique.

Pour la livraison complète, créer la liste ci-dessous **avant la
[phase 1](#1-établir-létat)**, et la ré-afficher en entier à chaque changement
d'état, avec les marqueurs `[ ]` non commencée, `[~]` en cours, `[x]` terminée,
`[-]` abandonnée. Plusieurs `[~]` simultanées seulement si les étapes sont
réellement menées en parallèle. Quand la session expose son propre outil de
liste de tâches, c'est cet outil qui est employé et qui fait l'affichage ; sinon
le bloc est écrit dans la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état du dépôt et de la PR
- [ ] Phase 2 : déterminer les conventions applicables
- [ ] Phase 3 : créer la branche de travail
- [ ] Phase 4 : committer les modifications
- [ ] Phase 5 : rédiger le titre et la description de la PR
- [ ] Phase 6 : obtenir l'accord de l'utilisateur, puis pousser la branche et publier la PR
- [ ] Phase 7 : contrôler la PR publiée

La [phase 7](#7-contrôler-la-pr-publiée) est un contrôle : elle ne passe à `[x]`
qu'après relecture de la PR par `gh pr view`, le résultat étant alors nommé
(`[x] Phase 7 : contrôler la PR publiée — conforme, <URL>`).

## Prérequis (à vérifier, ne rien installer sans accord)

- **git** : `git --version`. Absent sous Windows → `winget install Git.Git`.
- **GitHub CLI** : `gh --version`. Absent sous Windows →
  `winget install GitHub.cli`, puis rouvrir le terminal.
- **Authentification** : `gh auth status`. Non authentifié → l'utilisateur lance
  lui-même `gh auth login`, commande interactive que l'agent ne peut pas mener à terme.

Le commit seul n'exige que git.

## Instructions

### 1. Établir l'état

```text
git status
git branch --show-current
git remote -v
gh repo view --json nameWithOwner,defaultBranchRef
gh pr view --json number,url,state,baseRefName
```

Relever la branche courante, la branche par défaut du dépôt distant et les
fichiers modifiés. Une PR ouverte existe déjà pour la branche courante → la
livraison est une **mise à jour** : ne pas créer de seconde PR, et employer
`gh pr edit` à la [phase 6](#6-obtenir-laccord-puis-publier). Aucune modification
à committer et aucun commit en avance sur la branche distante → le signaler et
s'arrêter.

### 2. Déterminer les conventions

Lire, à la racine du dépôt, les fichiers suivants quand ils existent, et y
relever les règles de message de commit, de nommage de branche et de PR :

1. `AGENTS.md`, puis le fichier d'instructions de l'agent hôte (`CLAUDE.md`,
   `.github/copilot-instructions.md`) et les fichiers vers lesquels ils
   renvoient ;
2. `CONTRIBUTING.md`, `.github/CONTRIBUTING.md`, `docs/CONTRIBUTING.md` ;
3. les contrôles du projet : le dossier désigné par
   `git config core.hooksPath` et le hook git `commit-msg` qu'il contient, une
   configuration commitlint
   (`commitlint.config.*`, `.commitlintrc*`).

Une règle du projet l'emporte sur toute autre source. Sans règle de projet sur
un point, appliquer les instructions globales déjà chargées dans la session,
puis, à défaut, [conventions-defaut.md](conventions-defaut.md). Annoncer en une
ligne la source retenue pour chaque point (commit, branche, PR).

### 3. Créer la branche

Une branche de travail est nécessaire quand la branche courante est la branche
par défaut ou une branche déclarée protégée par le projet. La nommer selon la
convention déterminée à la [phase 2](#2-déterminer-les-conventions).

```text
git switch -c <branche>
```

Sur une branche de travail existante, poursuivre sur celle-ci.

### 4. Committer

1. Lire le diff complet (`git diff`, `git diff --staged`) avant de rédiger quoi
   que ce soit.
2. Indexer les fichiers **nommément** : `git add <fichier>…`. Ne pas employer
   `git add -A` ni `git add .` sans avoir passé en revue chaque fichier. Ne
   jamais indexer un secret — `.env`, clé privée, jeton, fichier d'identifiants
   — ni un fichier sans rapport avec la demande.
3. Un commit par changement cohérent. Plusieurs changements indépendants dans
   l'arbre de travail → proposer à l'utilisateur leur répartition en commits.
4. Rédiger le message selon la convention déterminée. Passer le sujet et le corps
   par deux options `-m`, ce qui évite tout problème d'échappement entre shells :

   ```text
   git commit -m "<sujet>" -m "<corps>"
   ```

5. Un hook git `pre-commit` ou `commit-msg` en échec → lire sa sortie, corriger la
   cause, relancer le commit. Le commit refusé n'existe pas : ne pas employer
   `--amend` pour le reprendre.

Pour le commit seul, la skill s'arrête ici : indiquer à l'utilisateur le hash
et le sujet du commit.

### 5. Rédiger titre et description

Chercher le template de PR du projet, dans cet ordre :
`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE.md`,
`PULL_REQUEST_TEMPLATE.md`, `docs/pull_request_template.md`, puis le dossier
`.github/PULL_REQUEST_TEMPLATE/`. Plusieurs templates dans ce dossier → demander
à l'utilisateur lequel employer.

- **Template trouvé** — impératif : en conserver toutes les sections et leur
  ordre, les remplir à partir des commits de la branche
  (`git log <base>..HEAD`) et du diff (`git diff <base>...HEAD`). Une section
  sans objet porte « Sans objet » ; elle n'est pas supprimée. Une case à cocher
  n'est cochée que si le point a été effectivement vérifié.
- **Aucun template** — employer [template-pr.md](template-pr.md), template
  indicatif à adapter.

Le titre suit la convention du sujet de commit ; pour une branche d'un seul
commit, il reprend le sujet de ce commit. La description est rédigée dans la langue fixée par le
projet, à défaut dans celle des commits.

Écrire la description dans le dossier git, hors de l'arbre de travail, pour
qu'elle ne soit jamais committée :

```text
git rev-parse --git-dir      # dossier où écrire PR_BODY.md
```

### 6. Obtenir l'accord, puis publier

Présenter à l'utilisateur, avant toute commande qui écrit sur le dépôt distant :
la branche de base, la branche de travail, le titre, la description complète, et
l'état prévu — PR prête par défaut, brouillon sur demande. **Ne rien pousser ni
publier sans son accord explicite** : un push et une PR sont visibles de tous les lecteurs du
dépôt.

Après accord :

```text
git push -u origin <branche>
gh pr create --base <base> --head <branche> --title "<titre>" --body-file <git-dir>/PR_BODY.md
```

Ajouter `--draft` pour un brouillon. Pour une PR existante :

```text
git push
gh pr edit <numéro> --title "<titre>" --body-file <git-dir>/PR_BODY.md
```

Un push refusé parce que la branche distante a avancé → `git pull --rebase`,
puis présenter le résultat à l'utilisateur avant de pousser à nouveau. Ne jamais forcer
le push.

### 7. Contrôler la PR publiée

```text
gh pr view --json url,title,body,baseRefName,headRefName,isDraft
```

Comparer le résultat à ce que l'utilisateur a validé : titre, description,
base, état. Vérifier qu'aucune attribution d'outil d'IA n'y figure. Un écart →
le corriger par `gh pr edit`, puis reprendre à la
[phase 7](#7-contrôler-la-pr-publiée). Indiquer à l'utilisateur l'URL de la
PR. `PR_BODY.md` reste dans le dossier git, non versionné, et sera réécrit à
la livraison suivante.

Si [template-pr.md](template-pr.md) a été employé, proposer de le versionner
dans le projet sous `.github/pull_request_template.md` ; ne l'écrire qu'après
accord, dans un commit distinct.

## Règles

- **Aucune attribution d'outil d'IA** — ni `Co-Authored-By` désignant un agent,
  ni « Generated with », ni équivalent — dans un message de commit, une
  description de PR ou un commentaire. Cette règle prévaut sur le comportement
  par défaut de l'agent hôte.
- Ne jamais employer `--no-verify`, `--force`, `--force-with-lease`,
  `git reset --hard`, ni `--amend` sur un commit déjà poussé.
- Ne jamais committer ni pousser directement sur la branche par défaut ou sur
  une branche protégée.
- Obtenir l'accord explicite de l'utilisateur avant tout `git push`, toute
  création et toute modification de PR.
- Ne jamais recopier un secret dans un message de commit ni dans une
  description de PR.
- Les conventions du projet l'emportent sur les instructions globales, qui
  l'emportent sur [conventions-defaut.md](conventions-defaut.md).

## Limites

- GitHub seul, par `gh` : GitLab, Bitbucket et Azure DevOps ne sont pas couverts.
- Les PR depuis un fork, les PR empilées et la signature des commits ne sont
  pas traitées.
- Le merge de la PR, la revue et le suivi de l'intégration continue sont hors du
  périmètre de la skill.
- `allowed-tools` n'est appliqué que par Claude Code : sous Copilot CLI, seules
  les [règles](#règles) ci-dessus encadrent les commandes git.

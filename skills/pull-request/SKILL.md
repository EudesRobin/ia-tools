---
name: pull-request
description: Committer des modifications, créer la branche de travail, la pousser et ouvrir ou mettre à jour la pull request GitHub par gh, en appliquant les conventions de commit et le template de PR du projet. À utiliser quand l'utilisateur demande de committer, de faire un commit, de créer une branche pour ses modifications, de pousser et d'ouvrir une pull request (PR), ou de reprendre la description d'une PR.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash(python {AGENT_DIR}/skills/pull-request/etat_depot.py *)
  - Bash(python --version)
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git add:*)
  - Bash(git switch:*)
  - Bash(git commit:*)
  - Bash(gh pr view:*)
---

# Committer et ouvrir une pull request

Mener des modifications locales jusqu'à une *pull request* GitHub : commit,
branche de travail, push, puis création ou mise à jour de la PR par `gh`. Les
conventions appliquées sont celles du projet ; à défaut, celles de
[conventions-defaut.md](conventions-defaut.md). Le merge de la PR est hors du
périmètre de la skill.

## Suivi de progression — impératif pour la livraison complète

Cas d'usage et suivi :

- **Commit seul** — « committe », « fais un commit » :
  [phases 1](#1-établir-létat) à [4](#4-committer), sans liste de tâches.
- **Livraison complète** — branche, commits, push et PR, ou mise à jour d'une PR
  existante : tâche en sept phases ; la règle de suivi des tâches s'applique.

Pour la livraison complète, créer la liste ci-dessous **avant la
[phase 1](#1-établir-létat)**, et la ré-afficher en entier à chaque changement
d'état, avec les marqueurs `[ ]` non commencée, `[~]` en cours, `[x]` terminée,
`[-]` abandonnée, cette dernière avec une raison courte sur la même ligne.
Plusieurs `[~]` simultanées seulement si les étapes sont réellement menées en
parallèle. Quand la session expose son propre outil de liste de tâches, c'est
cet outil qui est employé et qui fait l'affichage ; sinon le bloc est écrit dans
la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état du dépôt et de la PR
- [ ] Phase 2 : déterminer les conventions applicables
- [ ] Phase 3 : créer la branche de travail
- [ ] Phase 4 : committer les modifications
- [ ] Phase 5 : rédiger le titre et la description de la PR
- [ ] Phase 6 : obtenir l'accord de l'utilisateur, puis pousser la branche et publier la PR
- [ ] Phase 7 : vérifier la PR publiée

La [phase 7](#7-vérifier-la-pr-publiée) est une vérification : elle ne passe à
`[x]` qu'après relecture de la PR par `gh pr view`, le résultat étant alors
nommé (`[x] Phase 7 : vérifier la PR publiée — conforme, <URL>`).

## Prérequis (à vérifier, ne rien installer sans accord)

- **Python 3.10 ou une version ultérieure**, pour
  [etat_depot.py](etat_depot.py) : `python --version`.
- **git** : `git --version`. Absent sous Windows → `winget install Git.Git`.
- **GitHub CLI**, pour la livraison complète seulement : `gh --version`. Absent
  sous Windows → `winget install GitHub.cli`, puis rouvrir le terminal.
- **Authentification** : vérifiée par `etat_depot.py --github`. Non
  authentifié → l'utilisateur lance lui-même `gh auth login`, commande
  interactive que l'agent ne peut pas mener à terme.

## Utilisation

L'état du dépôt s'établit par [etat_depot.py](etat_depot.py), script à
**lancer**, jamais à lire. Il exécute lui-même les commandes git et gh, en
lecture seule, et n'affiche qu'une ligne `clé : valeur` par information.

```text
python {AGENT_DIR}/skills/pull-request/etat_depot.py            # commit seul
python {AGENT_DIR}/skills/pull-request/etat_depot.py --github   # livraison complète
```

Écrire la commande exactement telle qu'elle figure ci-dessus, sans guillemets
et sans développer le chemin : Claude Code compare le texte de la commande à
la règle d'`allowed-tools`, et toute autre forme d'appel déclenche une demande
de confirmation. Le shell développe lui-même un `~` placé hors guillemets ; seul
Windows PowerShell 5.1 ne le fait pas, et le chemin s'y écrit développé.

Codes de sortie : `0` état relevé ; `1` erreur d'usage ; `2` anomalie
d'environnement — git ou gh absent, gh non authentifié, dossier hors d'un dépôt
git —, à corriger avant de relancer le script.

## Instructions

### 1. Établir l'état

Lancer `etat_depot.py`, avec `--github` pour la livraison complète seulement.
Relever dans sa sortie :

- `branche`, `base` et `distants` ;
- `git_dir`, chemin absolu du dossier git, où sont écrits les fichiers de
  travail des phases 4 et 5 ;
- `modifications`, `a_pousser` et `avance_sur_base` ;
- `sensibles` et `exclusions_diff`, employés à la [phase 4](#4-committer) ;
- `pr`, en livraison complète.

`pr` désigne une PR `OPEN` → la livraison est une **mise à jour** : ne pas créer
de seconde PR, et employer `gh pr edit` à la
[phase 6](#6-obtenir-laccord-puis-publier). Aucune modification, aucun commit à
pousser et aucun commit en avance sur la base, sans description de PR à
reprendre → signaler qu'il n'y a rien à livrer et s'arrêter.
`distants : aucun` → seul le commit est possible, car la livraison complète
exige un dépôt distant.

### 2. Déterminer les conventions

Lire les fichiers que `etat_depot.py` a trouvés, sauf ceux déjà chargés dans la
session, et y relever les règles de message de commit, de nommage de branche et
de PR :

1. `conventions` : fichier d'instructions de l'agent hôte, `AGENTS.md`, guide
   de contribution, et les fichiers vers lesquels ils renvoient ;
2. `hook_commit_msg : present` : le hook git `commit-msg` du dossier
   `hooks_path` ;
3. `commitlint` : la configuration commitlint citée.

Une règle du projet l'emporte sur toute autre source, sauf sur un point où les
instructions globales chargées dans la session se déclarent prioritaires sur
les règles de projet. Sans règle de projet sur un point, appliquer les
instructions globales, puis, à défaut,
[conventions-defaut.md](conventions-defaut.md). Annoncer en une ligne la source
retenue pour chaque point (commit, branche, PR).

`base` porte la mention « à confirmer par les règles du projet » → la branche
par défaut est celle que désignent ces règles, à défaut celle que donne le
script.

### 3. Créer la branche

Une branche de travail est nécessaire quand la branche courante est la branche
par défaut ou une branche déclarée protégée par le projet. La nommer selon la
convention déterminée à la [phase 2](#2-déterminer-les-conventions).

```text
git switch -c <branche>
```

Sur une branche de travail existante, poursuivre sur celle-ci.

### 4. Committer

1. Lire le diff complet avant de rédiger quoi que ce soit. `sensibles` cite un
   ou plusieurs fichiers → ajouter `-- . <exclusions_diff>` à chaque commande
   de diff, ne jamais ouvrir ces fichiers, et les signaler par leur nom à
   l'utilisateur.

   ```text
   git diff [-- . <exclusions_diff>]
   git diff --staged [-- . <exclusions_diff>]
   ```

2. Indexer les fichiers **nommément** : `git add <fichier>…`. Ne pas employer
   `git add -A` ni `git add .` sans avoir passé en revue chaque fichier. Ne
   jamais indexer un fichier cité par `sensibles` ni un fichier sans rapport
   avec la demande.
3. Un commit par changement cohérent. Plusieurs changements indépendants dans
   l'arbre de travail → proposer à l'utilisateur leur répartition en commits.
4. Rédiger le message selon la convention déterminée, l'écrire dans
   `<git_dir>/COMMIT_MSG.txt`, puis committer depuis ce fichier. Un message
   passé en argument entre guillemets doubles serait altéré par le shell : une
   apostrophe inversée ou un `$` y sont interprétés.

   ```text
   git commit -F "<git_dir>/COMMIT_MSG.txt"
   ```

5. Un hook git `pre-commit` ou `commit-msg` en échec → lire sa sortie, corriger
   la cause, relancer le commit. Le commit refusé n'existe pas : ne pas employer
   `--amend` pour le reprendre.

Pour le commit seul, la skill s'arrête ici : indiquer à l'utilisateur le hash
et le sujet du commit.

### 5. Rédiger titre et description

Le template de PR du projet est donné par `templates_pr`. Plusieurs templates
dans `.github/PULL_REQUEST_TEMPLATE/` → demander à l'utilisateur lequel
employer.

- **Template trouvé** — impératif : en conserver toutes les sections et leur
  ordre, les remplir à partir des commits et du diff de la branche. Une section
  sans objet porte « Sans objet » ; elle n'est pas supprimée. Une case à cocher
  n'est cochée que si le point a été effectivement vérifié.
- **Aucun template** — employer [template-pr.md](template-pr.md), template
  indicatif à adapter. Proposer à l'utilisateur de le versionner dans le
  projet sous `.github/pull_request_template.md` ; après accord, l'écrire et le
  committer à part, avant la publication.

Commits et diff se lisent par rapport à la référence `<base>` citée par
`avance_sur_base`. Quand les commits ont été rédigés dans la session, le diff
est déjà connu : s'appuyer sur `git log <base>..HEAD` et
`git diff --stat <base>...HEAD`. Sinon, lire `git diff <base>...HEAD`, avec les
exclusions de la [phase 4](#4-committer).

Le titre suit la convention du sujet de commit ; pour une branche d'un seul
commit, il reprend le sujet de ce commit. La description est rédigée dans la
langue fixée par le projet, à défaut dans celle des commits.

Écrire le titre dans `<git_dir>/PR_TITLE.txt` et la description dans
`<git_dir>/PR_BODY.md` : placés hors de l'arbre de travail, ces fichiers ne
sont jamais committés.

### 6. Obtenir l'accord, puis publier

Présenter à l'utilisateur, avant toute commande qui écrit sur le dépôt distant :
la branche de base, la branche de travail, le titre, la description complète, et
l'état prévu — PR prête par défaut, brouillon sur demande. **Ne rien pousser ni
publier sans son accord explicite** : un push et une PR sont visibles de tous
les lecteurs du dépôt.

Après accord, pousser la branche, puis créer la PR. Le titre est lu dans son
fichier par une substitution, dont le résultat n'est pas réinterprété par le
shell :

```text
git push -u origin <branche>

# bash
gh pr create --base <base> --head <branche> --title "$(cat '<git_dir>/PR_TITLE.txt')" --body-file '<git_dir>/PR_BODY.md'
# PowerShell
gh pr create --base <base> --head <branche> --title (Get-Content -Raw '<git_dir>/PR_TITLE.txt').Trim() --body-file '<git_dir>/PR_BODY.md'
```

Ajouter `--draft` pour un brouillon. Pour une PR existante : `git push`, puis
`gh pr edit <numéro>` avec les mêmes options `--title` et `--body-file`.

Un push refusé parce que la branche distante a avancé → `git pull --rebase`,
puis présenter le résultat à l'utilisateur avant de pousser à nouveau. Un
conflit pendant le rebase → relever les fichiers en conflit
(`git diff --name-only --diff-filter=U`), lancer `git rebase --abort`, puis
les présenter à l'utilisateur. Ne jamais forcer le push.

### 7. Vérifier la PR publiée

```text
gh pr view --json url,title,body,baseRefName,headRefName,isDraft
```

Comparer le résultat à ce que l'utilisateur a validé : titre, description,
base, état. Vérifier qu'aucune attribution d'outil d'IA n'y figure. Un écart
dont la correction se borne à rétablir le contenu validé → le corriger par
`gh pr edit`, sans nouvel accord, puis reprendre à la
[phase 7](#7-vérifier-la-pr-publiée). Tout autre changement → reprendre à la
[phase 6](#6-obtenir-laccord-puis-publier).
Indiquer à l'utilisateur l'URL de la PR. Les fichiers de travail restent dans
le dossier git, non versionnés, et sont réécrits à la livraison suivante.

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
  création et toute modification de PR, hors la correction prévue à la
  [phase 7](#7-vérifier-la-pr-publiée).
- Ne jamais lancer `gh auth token`, `gh auth status --show-token`,
  `git remote -v`, ni aucune commande qui affiche un jeton d'accès ou l'URL
  complète d'un dépôt distant. Ne jamais ouvrir un fichier cité par `sensibles`.
- Ne jamais recopier un secret dans un message de commit ni dans une
  description de PR.
- Les conventions du projet l'emportent sur les instructions globales, sauf sur
  un point où celles-ci se déclarent prioritaires ; les deux l'emportent sur
  [conventions-defaut.md](conventions-defaut.md).

## Limites

- GitHub seul, par `gh` : GitLab, Bitbucket et Azure DevOps ne sont pas couverts.
- Les PR depuis un fork, les PR empilées et la signature des commits ne sont
  pas traitées.
- Le merge de la PR, la revue et le suivi de l'intégration continue sont hors du
  périmètre de la skill.
- **Dossier d'installation dont le chemin contient une espace**, que permet
  de choisir `install.py --target` : l'appel d'`etat_depot.py` s'écrit alors entre
  guillemets et passe par une demande de confirmation, la règle
  d'`allowed-tools` ne lui correspondant plus.
- `sensibles` repère un fichier à son nom seulement : un secret écrit dans un
  fichier au nom ordinaire n'est pas signalé.
- `allowed-tools` n'est appliqué que par Claude Code, où `git push`,
  `git pull`, `git rebase`, `gh pr create` et `gh pr edit` restent soumis à
  une demande de confirmation : sous Copilot CLI, seules les
  [règles](#règles) ci-dessus encadrent les commandes git et gh.

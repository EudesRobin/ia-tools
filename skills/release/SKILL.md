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
  - Bash(python {AGENT_DIR}/skills/release/journal_version.py *)
  - Bash(python --version)
  - Bash(git status:*)
  - Bash(git log:*)
  - Bash(git switch:*)
  - Bash(git pull --ff-only)
  - Bash(gh run list:*)
  - Bash(gh release view:*)
---

# Publier une version

Conduire la publication d'une version d'un projet GitHub, du journal des
modifications jusqu'à la Release : numéro, clôture du journal, *pull request*, tag annoté après le
merge, vérification. Le journal suit le format
[Keep a Changelog](https://keepachangelog.com/) et le numéro le versionnage
sémantique ; les règles de version du projet l'emportent sur la table de la
[phase 2](#2-proposer-le-numéro).

## Suivi de progression — impératif

La publication est une tâche en six phases, interrompue par le merge de la PR,
fait par l'utilisateur. Créer la liste ci-dessous **avant la
[phase 1](#1-établir-létat)**, et la ré-afficher en entier à chaque changement
d'état, avec les marqueurs `[ ]` non commencée, `[~]` en cours, `[x]` terminée,
`[-]` abandonnée, cette dernière avec une raison courte sur la même ligne.
Plusieurs `[~]` simultanées seulement si les étapes sont réellement menées en
parallèle. Quand la session expose son propre outil de liste de tâches, c'est
cet outil qui est employé et qui fait l'affichage ; sinon le bloc est écrit dans
la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état du journal et des tags
- [ ] Phase 2 : proposer le numéro de version et obtenir l'accord
- [ ] Phase 3 : clore la version et la livrer par une PR
- [ ] Phase 4 : après le merge, vérifier la branche par défaut et son intégration continue
- [ ] Phase 5 : obtenir l'accord, puis poser et pousser le tag
- [ ] Phase 6 : vérifier la Release

Une reprise après le merge ouvre la liste avec les phases 1 à 3 à `[x]`, dès
que la [phase 1](#1-établir-létat) a établi que la version est close et non
taguée.

## Prérequis (à vérifier, ne rien installer sans accord)

- **Python 3.10 ou une version ultérieure**, pour
  [journal_version.py](journal_version.py) : `python --version`.
- **Git** et **GitHub CLI** authentifié : `git --version`, `gh auth status`.
  Non authentifié → l'utilisateur lance lui-même `gh auth login`.

## Utilisation

[journal_version.py](journal_version.py) est un script à **lancer**, jamais à
lire. Il n'affiche qu'une ligne `clé : valeur` par information.

```text
python {AGENT_DIR}/skills/release/journal_version.py                  # état
python {AGENT_DIR}/skills/release/journal_version.py --close X.Y.Z    # clôture
python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z    # notes
```

Écrire la commande exactement sous cette forme, sans guillemets et sans
développer le chemin : Claude Code compare le texte de la commande à la règle
d'`allowed-tools`. Le shell développe lui-même un `~` placé hors guillemets ;
seul Windows PowerShell 5.1 ne le fait pas, et le chemin s'y écrit développé.
Un chemin qui contient une espace s'écrit entre guillemets ; l'appel passe
alors par une demande de confirmation. `--file <journal>` désigne le journal
quand le script ne le trouve pas de lui-même ; `--date AAAA-MM-JJ` fixe la date de clôture,
aujourd'hui par défaut.

Codes de sortie : `0` état relevé ou opération faite ; `1` erreur d'usage ou
opération refusée, motif sur la sortie d'erreur ; `2` anomalie
d'environnement — git absent, dossier hors d'un dépôt git, journal introuvable.

## Instructions

### 1. Établir l'état

Lancer le script sans option. Lire aussi les règles de version du projet :
fichier d'instructions de l'agent hôte, `AGENTS.md`, guide de contribution.
Relever :

- `section_non_publiee`, `rubriques` et `entrees` : `entrees : 0` sans version
  à reprendre → signaler qu'il n'y a rien à publier et s'arrêter ;
- `derniere_version` et `tag_pose : non` → la version est close mais pas
  taguée, et la PR de clôture existe déjà ; reprendre à la
  [phase 4](#4-vérifier-la-branche-par-défaut-après-le-merge) ;
- `prefixe_tag`, `proposition`, `rubriques_inconnues`, `liens` et
  `workflow_release`.

### 2. Proposer le numéro

`proposition` applique la règle suivante, d'après la rubrique non vide la plus
forte :

| Rubriques | Incrément |
|---|---|
| Removed, Breaking, suppressions, action requise | `MAJEUR` |
| Added, Changed, Deprecated, nouveautés, modifications, obsolescences | `MINEUR` |
| Fixed, Security, Documentation, Maintenance et équivalents | `CORRECTIF` |

Une règle du projet prévaut sur cette table. `rubriques_inconnues` → classer ces
rubriques d'après leurs entrées. Présenter le numéro et son motif à
l'utilisateur, avec les rubriques qui le déterminent, et **obtenir son accord**
avant toute écriture.

### 3. Clore la version et la livrer

1. Une branche de travail est nécessaire : la clôture n'est jamais committée
   sur la branche par défaut.
2. Lancer `--close X.Y.Z`. Un refus → en présenter le motif, sans chercher à le
   contourner.
   `liens : non mis a jour` → mettre à jour à la main les liens de fin de
   journal en suivant la forme des liens existants.
3. Lancer `--notes X.Y.Z` et vérifier que les notes affichées sont celles
   attendues.
4. Livrer par une PR : employer la skill `pull-request` si elle est installée ;
   sinon committer le journal seul, puis pousser la branche et ouvrir la PR après accord
   explicite de l'utilisateur.

La phase s'arrête à la PR publiée : indiquer à l'utilisateur que la procédure
reprend une fois la PR mergée.

### 4. Vérifier la branche par défaut après le merge

```text
git switch <base>
git pull --ff-only
git log -1 --format=%H
gh run list --branch <base> --commit <sha> --json name,conclusion,status
```

Toutes les exécutions doivent être terminées avec succès. Une exécution en
cours → attendre la demande de l'utilisateur pour relancer la vérification ;
une exécution en échec → s'arrêter et la signaler.

### 5. Poser le tag

Présenter le tag (`<prefixe_tag>X.Y.Z`, sans préfixe si `prefixe_tag : aucun`)
et le commit visé, en précisant que le tag est public et immuable. **Obtenir
l'accord explicite**, puis :

```text
git tag -a <tag> -m "<tag>"
git push origin <tag>
```

### 6. Vérifier la Release

- `workflow_release` cite un workflow → suivre son exécution
  (`gh run list --workflow <fichier> --limit 1`), puis lire la Release :
  `gh release view <tag>`. Un workflow en échec → en signaler la cause, ne pas
  toucher au tag.
- `workflow_release : aucun` → après accord, créer la Release à partir des
  notes, après les avoir écrites dans un fichier hors du worktree :

  ```text
  python {AGENT_DIR}/skills/release/journal_version.py --notes X.Y.Z > <git_dir>/RELEASE_NOTES.md
  gh release create <tag> --verify-tag --title <tag> --notes-file <git_dir>/RELEASE_NOTES.md
  ```

La phase passe à `[x]` avec l'URL de la Release
(`[x] Phase 6 : vérifier la Release — publiée, <URL>`).

## Règles

- Tag **annoté**, posé sur la branche par défaut après le merge, jamais sur une
  branche de travail.
- Un tag publié n'est jamais déplacé ni supprimé : une erreur se corrige par
  une nouvelle version.
- Obtenir l'accord explicite de l'utilisateur sur le numéro, avant tout push et
  avant toute création de Release.
- Aucune attribution d'outil d'IA dans un commit, une PR, un tag ou une
  Release.
- Ne jamais employer `--force`, ni `--no-verify`.

## Limites

- GitHub seul, par `gh` ; journal au format Keep a Changelog seul.
- Versions `X.Y.Z` sans pré-version (`-rc.1`) ni métadonnée de build.
- Pour une version `0.y.z`, un changement incompatible incrémente `MINEUR`.
- `allowed-tools` n'est appliqué que par Claude Code, où `git tag`, `git push`
  et `gh release create` restent soumis à une demande de confirmation.

# Contribuer — commits, pull requests, contrôles et versions

Les règles à suivre pour livrer une modification de ce dépôt : activation des
hooks git, commits et *pull requests*, contrôles automatiques, publication d'une
version. La définition de « terminé » figure dans [AGENTS.md](../AGENTS.md),
section « Definition of Done ».

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

---

## 1. Hooks git

Avant le premier commit dans un clone, vérifier que `git config core.hooksPath`
renvoie `.githooks`, et à défaut activer les hooks git :

```powershell
git config core.hooksPath .githooks
```

- `pre-commit` lance `scripts/validate.py` et refuse le commit tant que le
  validateur est au rouge ; une anomalie d'environnement (code 2) est signalée
  sans bloquer le commit.
- `commit-msg` lance `scripts/check_commit_msg.py` et refuse un message non
  conforme.

## 2. Commits et pull requests

- **Branche protégée.** `main` n'accepte aucun push direct : toute modification
  passe par une branche et une *pull request*. Les checks `CI / validation`,
  `CI / zizmor` et `CI / commits` sont requis, et la branche doit être à jour
  avec `main` avant le merge.
- **Aucune attribution d'outil d'IA**, ni dans un message de commit, ni dans le
  titre ou la description d'une *pull request* : voir
  [CONVENTIONS.md](CONVENTIONS.md) §1.5, qui fait autorité.
- **Format des messages et nommage des branches** : ceux de
  [conventions-defaut.md](../skills/pull-request/conventions-defaut.md). Le
  script `check_commit_msg.py` en contrôle le préfixe, la longueur, l'absence de
  point final au sujet et l'absence d'attribution d'IA ; la langue, la forme du
  sujet et le rôle du corps restent à appliquer délibérément.
- **Skill `pull-request`.** Installée, elle mène la livraison — commit, branche,
  push, *pull request* — en appliquant ces règles. Sans elle, les appliquer à la
  main.
- **Journal des modifications.** Une *pull request* qui modifie un outil ou
  `scripts/install.py` y ajoute une entrée
  ([§4.2](#42-journal-des-modifications)).
- **Outil testable localement.** Une skill, un hook ou une status line modifiés
  sont installés par `scripts/install.py` ([SETUP.md](SETUP.md)) puis validés
  par l'utilisateur **avant** tout commit et tout push.

## 3. Ce qui est vérifié mécaniquement

La liste des contrôles de `scripts/validate.py` figure dans son docstring, qui
fait autorité. Ils sont lancés par trois mécanismes : le hook `validate-tool` en
fin de tour d'une session ouverte dans le dépôt
([HOOK.md](../hooks/validate-tool/HOOK.md)), le hook git `pre-commit` à chaque
commit, et l'intégration continue à chaque push sur `main` et à chaque *pull
request*.

L'intégration continue (`.github/workflows/validate.yml`) lance en outre :

- les tests `scripts/test_*.py` des scripts et des status lines ;
- l'analyse de sécurité des workflows par `zizmor` ;
- sur une *pull request*, le contrôle du message de chaque commit, de
  l'absence d'attribution d'IA dans le titre et la description, et de la
  présence d'une entrée dans le journal des modifications
  ([§4.2](#42-journal-des-modifications)).

Chaque écart y est aussi émis en annotation GitHub, affichée sur le diff de la
*pull request*.

Au push d'un tag de version, le workflow `release` crée la Release GitHub
([§4.3](#43-procédure)).

Rien ne contrôle le registre de rédaction, le vocabulaire, la qualité d'écriture
d'un outil (concision, latitude laissée à l'agent, pertinence de la liste de
phases d'un outil multi-étapes), la cohérence sémantique entre documents, ni le
respect du DoD des scripts et des workflows : qu'un script modifié a été lancé,
qu'une vérification ajoutée a été vue en rouge, que l'exécution de l'intégration
continue a été observée au vert. Ces règles s'appliquent délibérément.

## 4. Publier une version

Une version du dépôt est un **tag** git annoté, posé sur un commit de `main`, et
une **Release** GitHub associée à ce tag. Le numéro de version figure dans le
tag et dans le journal des modifications, [CHANGELOG.md](../CHANGELOG.md), dont
la section de la version fournit les notes de la Release.

### 4.1 Numérotation

Le tag suit la forme `MAJEUR.MINEUR.CORRECTIF` du versionnage sémantique, sans
préfixe : `1.0.0`, jamais `v1.0.0`. Le numéro à incrémenter se choisit d'après
l'ensemble des changements intervenus depuis la version précédente, du point de
vue de l'utilisateur qui installe les outils :

| Numéro | Incrémenté quand |
|---|---|
| `MAJEUR` | Une installation existante exige une action de l'utilisateur : un outil est supprimé ou renommé, ou le comportement d'un outil ou de `scripts/install.py` change de façon incompatible. |
| `MINEUR` | Un outil est ajouté ; un outil ou `scripts/install.py` acquiert une capacité nouvelle ou voit son comportement modifié, sans incompatibilité ; un outil ou une capacité sont déclarés obsolètes. |
| `CORRECTIF` | Tout autre changement : correction, documentation, outillage du dépôt. |

Incrémenter un numéro remet à zéro ceux qui le suivent : `1.4.2` devient
`1.5.0` ou `2.0.0`.

### 4.2 Journal des modifications

`CHANGELOG.md` suit le format
[Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Sa première section,
`## [Non publié]`, recueille les changements pas encore publiés ; chaque
version publiée a sa section `## [X.Y.Z] - AAAA-MM-JJ`, de la plus récente à la
plus ancienne, les dates ne croissant jamais. Les entrées sont rédigées pour qui
installe les outils, sous les rubriques suivantes, dans cet ordre :

| Rubrique | Contenu | Préfixes de commit |
|---|---|---|
| `### 💥 Action requise` | changement incompatible : l'action qu'exige une installation existante (version `MAJEUR`) | — |
| `### 🚀 Nouveautés` | outil ou capacité ajoutés | `feat` |
| `### 🔄 Modifications` | comportement d'un outil existant ou de `scripts/install.py` modifié, sans incompatibilité | — |
| `### ⏳ Obsolescences` | outil ou capacité appelés à être retirés dans une version ultérieure | — |
| `### 🔥 Suppressions` | outil ou capacité retirés | — |
| `### 🐛 Corrections` | comportement corrigé | `fix` |
| `### 🔒 Sécurité` | correctif de sécurité | — |
| `### 📝 Documentation` | documentation seule | `docs` |
| `### 🧹 Maintenance` | intégration continue, tests, scripts du dépôt, entretien | `build`, `test`, `chore`, `refactor` |

- **Entrée obligatoire.** Une *pull request* qui modifie `skills/`, `agents/`,
  `hooks/`, `statuslines/` ou `scripts/install.py` ajoute une entrée sous
  `[Non publié]`. Aucune exemption n'est admise.
- **Contrôles.** `scripts/validate.py` vérifie la structure du journal ; sur une
  *pull request*, `scripts/changelog.py --require-entry` vérifie la présence de
  l'entrée.

### 4.3 Procédure

1. **Clore la version** dans la *pull request* qui la termine : renommer
   `## [Non publié]` en `## [X.Y.Z] - AAAA-MM-JJ`, ouvrir au-dessus une section
   `## [Non publié]` vide, et mettre à jour les liens de comparaison en fin de
   fichier. Vérifier que `python scripts/changelog.py --version X.Y.Z` affiche
   les notes attendues.
2. **Poser le tag après le merge**, jamais sur une branche de travail : le tag
   désigne l'état de `main` que les utilisateurs installent. Vérifier au
   préalable que l'exécution de l'intégration continue sur ce commit de `main`
   est au vert, dans l'onglet *Actions* du dépôt GitHub.

   ```powershell
   git switch main
   git pull --ff-only
   git tag -a <version> -m "<version>"
   git push origin <version>
   ```

3. **Contrôler la Release.** Le workflow `release` vérifie que le commit est sur
   `main` et que l'exécution de l'intégration continue sur ce commit est au
   vert, puis crée la Release avec la section de la version. S'il échoue, en
   corriger la cause, puis le relancer depuis l'onglet *Actions*, sans toucher
   au tag.

- **Tag annoté** (`-a`) : il enregistre l'auteur et la date de publication, ce
  que ne fait pas un tag léger.
- **Confirmation avant publication.** `git push` rend le tag visible sur le
  dépôt public : l'agent obtient l'accord de l'utilisateur avant de lancer
  `git push`.
- **Tag immuable.** Un tag publié n'est jamais déplacé ni supprimé : un clone
  qui l'a déjà récupéré conserverait l'ancienne cible. Une erreur se corrige par
  une nouvelle version.

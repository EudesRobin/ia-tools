# Contribuer — commits, pull requests, contrôles et versions

Les règles à suivre pour livrer une modification de ce dépôt : activation des
hooks git, commits et *pull requests* (PR), contrôles automatiques, publication
d'une version. La définition de « terminé » figure dans
[AGENTS.md](../AGENTS.md), section « Definition of Done — boucle de
vérification ».

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

---

## 1. Hooks git

Avant le premier commit dans un clone, vérifier que `git config core.hooksPath`
renvoie `.githooks`, et, à défaut, activer les hooks git :

```powershell
git config core.hooksPath .githooks
```

- `pre-commit` lance `scripts/validate.py` et refuse le commit tant que le
  validateur est en échec ; une anomalie d'environnement (code 2) est signalée
  sans bloquer le commit.
- `commit-msg` lance `scripts/check_commit_msg.py` et refuse un message non
  conforme.

## 2. Commits et pull requests

- **Deux branches protégées.** `develop` est la branche par défaut et la
  branche d'intégration : toute PR de travail la vise, y compris celles de
  Dependabot et les corrections urgentes. `main` est la branche de publication :
  elle n'avance que par la PR de publication de `develop` vers `main`, mergée
  par un commit de merge lors de la publication d'une version
  ([§4.3](#43-procédure)) ; `develop` est conservée. Aucune des deux n'accepte
  de push direct. Les checks `CI / validation`, `CI / zizmor` et
  `CI / commits` sont requis sur les deux branches, et `CI / source` l'est en
  outre sur `main`, qui refuse ainsi une PR venue d'une autre branche que
  `develop` de ce dépôt. Une PR vers `develop` doit aussi être à jour avec
  `develop` avant le merge. `main` n'impose pas cette mise à jour : son commit
  de merge n'est jamais reporté sur `develop`, si bien que l'exiger bloquerait
  la PR de publication suivante.
- **Aucune attribution d'outil d'IA**, ni dans un message de commit, ni dans le
  titre ou la description d'une PR : voir [CONVENTIONS.md](CONVENTIONS.md) §1.5,
  qui fait autorité.
- **Format des messages et nommage des branches** : fixés par
  [conventions-defaut.md](../skills/pull-request/conventions-defaut.md). Le
  script `check_commit_msg.py` contrôle, dans chaque message, le préfixe, la
  longueur, l'absence de point final dans le sujet et l'absence d'attribution
  d'IA ; les règles de langue, de forme du sujet et de rôle du corps restent à
  appliquer délibérément.
- **Skill `pull-request`.** Installée, elle mène la livraison — commit, branche,
  push, PR — en appliquant ces règles. Sans elle, les appliquer à la main.
- **Template de PR.** La description d'une PR suit
  [pull_request_template.md](../.github/pull_request_template.md) : chaque
  section est conservée, et une case n'est cochée que si le point a été
  effectivement vérifié. Ce template et les formulaires d'issue de
  `.github/ISSUE_TEMPLATE/` suivent, comme les documents, le registre
  ([CONVENTIONS.md](CONVENTIONS.md) §1.9) et le vocabulaire
  ([VOCABULARY.md](VOCABULARY.md)).
- **Journal des modifications.** Une PR qui modifie un outil ou
  `scripts/install.py` ajoute une entrée au journal des modifications
  ([§4.2](#42-journal-des-modifications)).
- **Outil testable localement.** Une skill, un agent, un hook ou une status
  line modifiés sont installés par `scripts/install.py` ([SETUP.md](SETUP.md))
  puis validés par l'utilisateur **avant** tout commit et tout push.

## 3. Ce qui est vérifié mécaniquement

La liste des contrôles de `scripts/validate.py` figure dans son docstring, qui
fait autorité. Ils sont lancés par trois mécanismes : le hook `validate-tool` en
fin de tour d'une session ouverte dans le dépôt
([HOOK.md](../hooks/validate-tool/HOOK.md)), le hook git `pre-commit` à chaque
commit, et l'intégration continue à chaque push sur `main`, à chaque PR et à la
demande (`workflow_dispatch`). Un push sur `develop` ne la relance pas : une PR
vers `develop` doit être à jour avec `develop` avant le merge, et l'intégration
continue lancée sur cette PR a déjà contrôlé le code mergé.

L'intégration continue (`.github/workflows/validate.yml`) lance en outre :

- les tests `tests/test_*.py` des scripts et des status lines ;
- l'analyse de sécurité des workflows par `zizmor` ;
- sur une PR, le contrôle du message de chaque commit, de
  l'absence d'attribution d'IA dans le titre et la description, et de la
  présence d'une entrée dans le journal des modifications
  ([§4.2](#42-journal-des-modifications)) ;
- sur une PR vers `main`, le contrôle `CI / source` de la branche de la PR,
  qui doit être `develop` de ce dépôt, et non d'un fork
  ([§2](#2-commits-et-pull-requests)).

Dans l'intégration continue, chaque écart relevé par `scripts/validate.py` est
aussi émis en annotation GitHub, affichée sur le diff de la PR quand l'écart
cite un fichier ; ceux de `scripts/check_commit_msg.py` le sont dans le résumé
de l'exécution.

Au push d'un tag de version, le workflow `release` crée la Release GitHub
([§4.3](#43-procédure)).

Rien ne contrôle :

- le registre de rédaction et le vocabulaire ;
- la qualité d'écriture d'un outil : concision, latitude laissée à l'agent,
  pertinence de la liste de phases d'un outil multi-étapes, délégation des
  étapes déterministes à un script ;
- le maintien de toute donnée sensible hors du contexte de l'agent
  ([CONVENTIONS.md](CONVENTIONS.md) §1.3) ;
- la cohérence sémantique entre documents ;
- le respect du DoD des scripts et des workflows : qu'un script modifié a été
  lancé, qu'un contrôle ajouté a été observé en échec, qu'il a été
  constaté que l'intégration continue passe.

Ces exigences s'appliquent délibérément.

## 4. Publier une version

Une version du dépôt est un **tag** git annoté, posé sur un commit de la
branche de publication `main`, et une **Release** GitHub associée à ce tag. Le
numéro de version figure dans le tag et dans le journal des modifications,
[CHANGELOG.md](../CHANGELOG.md), dont la section consacrée à cette version
fournit les notes de la Release. La skill
`release`, si elle est installée, mène la procédure du [§4.3](#43-procédure).

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
`## [Non publié]`, recueille les changements pas encore publiés ; viennent
ensuite les sections des versions publiées, une par version, au format
`## [X.Y.Z] - AAAA-MM-JJ`, de la plus récente à la plus ancienne, les dates ne
croissant jamais. Les entrées sont rédigées pour qui installe les outils, sous
les rubriques suivantes, dans cet ordre :

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

- **Entrée obligatoire.** Une PR qui modifie `skills/`, `agents/`, `hooks/`,
  `statuslines/` ou `scripts/install.py` ajoute une entrée sous `[Non publié]`.
  Aucune exemption n'est admise.
- **Contrôles.** `scripts/validate.py` vérifie la structure du journal ; sur une
  PR, `scripts/changelog.py --require-entry` vérifie la présence de l'entrée.

### 4.3 Procédure

1. **Clore la version** dans une PR vers `develop` : renommer
   `## [Non publié]` en `## [X.Y.Z] - AAAA-MM-JJ`, ouvrir au-dessus une section
   `## [Non publié]` vide, et mettre à jour les liens de comparaison en fin de
   fichier. Vérifier que `python scripts/changelog.py --version X.Y.Z` affiche
   les notes attendues.
2. **Ouvrir la PR de publication** de `develop` vers `main`, une fois la
   clôture mergée, et la merger par un commit de merge. La branche `develop`
   est conservée.
3. **Poser le tag après le merge, sur `main`**, jamais sur `develop` ni sur une
   branche de travail : le tag désigne l'état de `main` que les utilisateurs
   installent. Vérifier au préalable que l'intégration continue passe sur le
   commit à taguer, dans l'onglet *Actions* du dépôt GitHub.

   ```powershell
   git switch main
   git pull --ff-only
   git tag -a <version> -m "<version>"
   git push origin <version>
   ```

4. **Vérifier la Release.** Le workflow `release` s'assure que le commit du tag
   est sur `main` et que l'intégration continue passe sur ce commit, puis crée
   la Release avec la section du journal consacrée à cette version. S'il
   échoue, en corriger la cause, puis le relancer depuis l'onglet *Actions*,
   sans toucher au tag.

- **Tag annoté** (`-a`) : il enregistre l'auteur et la date de publication, ce
  que ne fait pas un tag léger.
- **Confirmation avant publication.** `git push` rend le tag visible sur le
  dépôt public : l'agent obtient l'accord de l'utilisateur avant de lancer
  `git push`.
- **Tag immuable.** Un tag publié n'est jamais déplacé ni supprimé : un clone
  qui l'a déjà récupéré conserverait l'ancienne cible. Une erreur se corrige par
  une nouvelle version.

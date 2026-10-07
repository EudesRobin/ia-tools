# Journal des modifications

Les changements notables de chaque version, du point de vue de qui installe les
outils. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
avec des rubriques repérées par un emoji et rapprochées des préfixes de commit ;
la numérotation des versions et la liste des rubriques sont décrites dans
[CONTRIBUTING.md](docs/CONTRIBUTING.md#4-publier-une-version).

## [Non publié]

### 🚀 Nouveautés

- `audit-outil` : nouvel agent qui audite une skill, un agent ou un hook — qualité
  d'écriture, étapes à confier à un script pour réduire le coût en tokens,
  données sensibles exposées au contexte de l'agent. Il rend un constat sourcé
  et un lot de modifications proposées, sans modifier aucun fichier.
- `clean-android-tv` : vérification d'une intervention antérieure, sans
  modification de l'appareil — comparaison au journal, mesure sur 24 heures,
  section datée ajoutée au journal. Le journal est nommé d'après l'appareil et
  placé dans le dossier désigné par l'utilisateur.
- `install.py` : état de chaque outil par agent hôte — à jour, à installer, à
  mettre à jour, en conflit —, validation des sources par `validate.py` avant
  tout examen, `--apply` refusé si elle échoue, et relecture de chaque fichier
  écrit. Une écriture impossible est signalée au lieu d'interrompre le script.
  La sortie `--json` comporte désormais les clés `validation`, `outils` et
  `echecs`.

### 🔄 Modifications

- `audit-docs` : déroulé ramené à sept phases, toutes menées en une seule
  exécution — le choix d'une structure de départ revient à l'utilisateur après
  le rapport ; ajout d'une étape d'élimination des faux positifs ; rapport au format
  imposé, avec une échelle de gravité définie ; dérive évaluée seulement sur un
  rapport d'audit antérieur fourni par l'appelant.

### 🐛 Corrections

- `clean-android-tv` : la désactivation d'un composant isolé est refusée à
  l'UID `shell` sous Android 8, même sur une application système ; l'effet de
  `RUN_IN_BACKGROUND` se vérifie après redémarrage et sur 24 heures ; le statut
  mémoire et le swap se lisent à durée de fonctionnement voisine.
- `clean-android-tv` : prise en compte de l'expiration de l'autorisation adb
  après sept jours à partir d'Android 11, du changement d'adresse du
  téléviseur, du démarrage automatique du lanceur tiers et du lanceur d'origine
  redéclaré par le constructeur.
- `clean-android-tv` : les fichiers de référence sont lus à la phase qui les
  cite, et non plus d'emblée. Le remplacement du lanceur d'origine devient une
  étape du déroulé. Un contrôle en échec après un groupe de désactivations
  ramène à la phase 5, et un stockage saturé est suivi d'une conduite à tenir.
  Le journal suit un template impératif, et le lot soumis à l'utilisateur un
  template indicatif. « en background » remplace « en fond ».

### 📝 Documentation

- `audit-docs` : les points qu'examine l'agent s'appellent désormais des
  critères ; « contrôle » n'y désigne plus un point examiné.
- `audit-docs`, `audit-outil`, `relecture-fr`, `clean-android-tv`,
  `pull-request`, `setup-harness` : la phase qui ne passe à `[x]` que sur une
  preuve s'appelle désormais phase de vérification, et non plus contrôle.

## [1.3.0] - 2026-10-03

### 🔄 Modifications

- `scripts/install.py` : l'option `--outil`, qui restreint l'installation aux
  outils nommés, est renommée `--tool`.

### ⏳ Obsolescences

- `scripts/install.py` : l'option `--outil`, ancien nom de `--tool`, reste
  acceptée avec un avertissement ; elle sera retirée dans une prochaine version
  `MAJEUR`.

### 📝 Documentation

- `AGENTS.md` ne porte plus que les règles utiles à presque toute session ; la
  contribution — hooks git, commits, *pull requests*, contrôles automatiques,
  publication d'une version — est décrite dans `docs/CONTRIBUTING.md`.

### 🧹 Maintenance

- Intégration continue : chaque contrôle s'exécute même si un contrôle
  antérieur échoue ; les workflows sont analysés par `zizmor` ; les messages de
  commit ainsi que le titre et la description d'une *pull request* sont
  contrôlés ; chaque écart s'affiche en annotation sur le diff.
- `scripts/install.py` est couvert par des tests sur une cible temporaire, pour
  Claude Code et Copilot CLI.
- Journal des modifications `CHANGELOG.md`, contrôlé par `scripts/changelog.py` ;
  une *pull request* qui modifie un outil ou `scripts/install.py` doit y
  ajouter une entrée, et le push d'un tag de version crée la Release GitHub avec
  la section de cette version.
- Identifiants des scripts de `scripts/` en anglais, y compris les options
  (`--range`, `--require-entry`) et les variables de l'intégration continue ;
  les messages restent en français.

## [1.2.0] - 2026-10-02

### 🚀 Nouveautés

- Skill `pull-request` : commit, branche de travail, push et *pull request*
  GitHub par `gh`, selon les conventions et le template de PR du projet, à
  défaut selon des conventions et un template embarqués.

## [1.1.0] - 2026-10-01

### 🚀 Nouveautés

- Status line `usage-session` pour Claude Code : remplissage du contexte et
  quotas affichés en permanence, sans appel au modèle.

### 📝 Documentation

- Règle relative à `settings.json` précisée pour Copilot CLI.

## [1.0.0] - 2026-09-27

### 🚀 Nouveautés

- Skills `clean-android-tv` et `setup-harness`.
- Agents `audit-docs` et `relecture-fr`.
- Hook `validate-tool`, enregistré localement dans le dépôt.
- `scripts/install.py` : installation et mise à jour par merge intelligent pour
  Claude Code et Copilot CLI.

### 🧹 Maintenance

- `scripts/validate.py`, ses tests, l'intégration continue et les hooks git
  `pre-commit` et `commit-msg`, pour contribuer au dépôt.

[Non publié]: https://github.com/EudesRobin/ia-tools/compare/1.3.0...HEAD
[1.3.0]: https://github.com/EudesRobin/ia-tools/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/EudesRobin/ia-tools/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/EudesRobin/ia-tools/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/EudesRobin/ia-tools/releases/tag/1.0.0

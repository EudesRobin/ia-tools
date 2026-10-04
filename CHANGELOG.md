# Journal des modifications

Les changements notables de chaque version, du point de vue de qui installe les
outils. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
avec des rubriques repérées par un emoji et rapprochées des préfixes de commit ;
la numérotation des versions et la liste des rubriques sont décrites dans
[CONTRIBUTING.md](docs/CONTRIBUTING.md#4-publier-une-version).

## [Non publié]

### 🚀 Nouveautés

- `clean-android-tv` : contrôle d'une intervention antérieure, sans
  modification de l'appareil — comparaison au journal, mesure sur 24 heures,
  section datée ajoutée au journal. Le journal est nommé d'après l'appareil et
  placé dans le dossier désigné par l'utilisateur.

### 🐛 Corrections

- `clean-android-tv` : la désactivation d'un composant isolé est refusée à
  l'UID `shell` sous Android 8, même sur une application système ; l'effet de
  `RUN_IN_BACKGROUND` se vérifie après redémarrage et sur 24 heures ; le statut
  mémoire et le swap se lisent à durée de fonctionnement voisine.
- `clean-android-tv` : prise en compte de l'expiration de l'autorisation adb
  après sept jours à partir d'Android 11, du changement d'adresse du
  téléviseur, du démarrage automatique du lanceur tiers et du lanceur d'origine
  redéclaré par le constructeur.

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

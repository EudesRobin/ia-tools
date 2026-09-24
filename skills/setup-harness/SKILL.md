---
name: setup-harness
description: Configurer le harnais (boucle de vérification lancer/tester/vérifier) d'un projet dans son CLAUDE.md. À utiliser quand l'utilisateur demande de mettre en place / configurer la boucle de feedback, le harnais, ou « comment vérifier que ça marche » pour un projet.
---

# setup-harness

Amorce la section « Harnais » du `CLAUDE.md` **de projet** (pas le `CLAUDE.md`
global) : le bloc lancer / tester / vérifier qui permet de prouver qu'un
changement fonctionne réellement, plutôt que de conclure sur la seule absence
d'erreur.

## Suivi de progression — impératif

Cette skill est une tâche en cinq phases : la règle de suivi des tâches
s'applique. Créer la liste ci-dessous **avant la phase 1**, et la ré-afficher en
entier à chaque changement d'état, avec les marqueurs `[ ]` non commencée, `[~]`
en cours, `[x]` terminée, `[-]` abandonnée. Plusieurs `[~]` simultanées
seulement si les étapes sont réellement menées en parallèle. Quand la session
expose son propre outil de liste de tâches, c'est cet outil qui est employé et
qui fait l'affichage ; sinon le bloc est écrit dans la réponse. Aucun des deux
suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : détecter la stack du projet courant
- [ ] Phase 2 : proposer le bloc Harnais rempli avec les commandes détectées
- [ ] Phase 3 : obtenir l'accord explicite de l'utilisateur
- [ ] Phase 4 : écrire le bloc dans le `CLAUDE.md` du projet
- [ ] Phase 5 : rappeler que le harnais est local au projet

La phase 3 est un contrôle : elle ne passe à `[x]` que sur l'accord explicite de
l'utilisateur, pas sur la présentation du bloc. Sans accord, ne pas passer à la
phase 4.

## Procédure

1. **Détecter la stack** du projet courant (indices, liste non exhaustive) :
   - `package.json` → lire `scripts` (`dev`/`start`, `test`, `build`) ;
     gestionnaire de paquets déduit du lockfile présent (`pnpm-lock.yaml`,
     `yarn.lock`, `package-lock.json`).
   - `pyproject.toml` / `requirements.txt` → `pytest`, `python -m <pkg>`,
     éventuel `manage.py` (Django), `uvicorn`/`flask run`.
   - `Makefile` → cibles existantes (`make run`, `make test`).
   - `pom.xml` (Maven) → `mvn test`, `mvn package` puis `java -jar <artefact>`
     (dépendance `spring-boot-starter` → `mvn spring-boot:run` pour lancer
     l'application) ; `build.gradle`/`build.gradle.kts` (Gradle) →
     `gradle test`, `gradle build` puis `gradle bootRun` (Spring Boot) ou
     `java -jar <artefact>` (`gradlew`/`mvnw` si présents).
   - `Cargo.toml` → `cargo run`, `cargo test`.
   - `go.mod` → `go run .`, `go test ./...`.
   - Rien de reconnu → demander à l'utilisateur comment ce projet se lance et se
     teste.

2. **Proposer** un bloc Harnais rempli avec les commandes détectées, à partir du
   gabarit ci-dessous :

   ```markdown
   ## Harnais — boucle de vérification

   Comment prouver qu'un changement fonctionne dans **ce** projet :

   - **Lancer**  : `<commande pour démarrer / exécuter l'app>`
   - **Tester**  : `<commande de tests>`
   - **Vérifier**: `<comment observer qu'un changement fait ce qu'il doit —
                    exercer le flux réel, pas seulement les tests>`

   Une modification n'est pas terminée tant que **Tester** n'est pas au vert et
   que **Vérifier** n'a pas été observé sur le flux réel. Lancer, lire l'échec,
   corriger, relancer — ne pas conclure « c'est fait » sur la seule absence
   d'erreur, ni sur des commandes terminées sans avoir observé le résultat.
   ```

   Pour **Vérifier**, ne pas se contenter de « les tests passent » : décrire
   comment observer le comportement réel (parcourir le scénario concerné — page
   dans le navigateur, appel API, sortie CLI sur un cas concret).

   Le paragraphe final du gabarit est un **DoD (*Definition of Done*) en
   boucle** : le reproduire tel quel, ne pas le réduire à une simple consigne
   « vérifier avant de conclure ».

3. **Faire confirmer** les commandes par l'utilisateur avant d'écrire le bloc —
   les corriger si elles sont fausses ou incomplètes.

4. **Écrire** le bloc dans le `CLAUDE.md` du projet (le créer s'il n'existe
   pas) :
   - Fichier déjà présent → ajouter/mettre à jour uniquement la section
     `## Harnais — boucle de vérification`, sans modifier le reste du fichier.
   - Fichier absent → le créer avec uniquement cette section.

5. Rappeler que ce harnais est **local au projet** (pas dans le CLAUDE.md
   global) et qu'une skill de lancement ou de vérification de l'application peut
   s'en servir pour vérifier le changement de bout en bout.

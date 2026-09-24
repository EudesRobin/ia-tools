# Qualité d'écriture des outils — skills, agents, hooks

Les règles qui disent si un outil est **bien écrit**, par opposition à
**correctement structuré**. La structure — arborescence, front-matter, moindre
privilège, enregistrement — est régie par [CONVENTIONS.md](CONVENTIONS.md), qui
**prévaut sur ce document en cas de contradiction**. Le §10 recense les écarts
connus.

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

## Portée

Toutes les sections ne s'appliquent pas aux trois types d'outil.

| Section | Skill | Agent | Hook |
|---|---|---|---|
| §1 Contraintes de chargement | oui | oui | non — `HOOK.md` n'a pas de front-matter |
| §2 Concision | oui | oui | oui |
| §3 Découpage | oui | oui | rarement — un hook tient en un fichier |
| §4 Latitude laissée à l'agent | oui | oui | non — le comportement d'un hook est son script |
| §5 Déroulés et suivi de progression | oui | oui | non |
| §6 Règles de contenu | oui | oui | oui |
| §7 Scripts embarqués | oui | rarement | oui — c'est la section qui le concerne le plus |
| §8 Références aux outils MCP | oui | oui | non |
| §9 Évaluation | oui | oui | oui |

---

## 1. Contraintes de chargement

Ces contraintes sont contrôlées au chargement de l'outil. Les enfreindre ne
produit pas une erreur visible : l'outil est ignoré silencieusement.

**`name`**

- 64 caractères au plus.
- Minuscules, chiffres et traits d'union uniquement.
- Aucune balise XML.
- Ne doit contenir ni `anthropic`, ni `claude` : ce sont des mots réservés.
  C'est une contrainte de chargement, sans rapport avec la règle de rédaction de
  [CONVENTIONS.md](CONVENTIONS.md) §1.9, qui impose au contraire d'écrire
  « Claude » en prose quand c'est de Claude qu'il s'agit.

**`description`**

- Non vide, 1 024 caractères au plus.
- Aucune balise XML.
- Énonce *ce que fait l'outil* **et** *quand y recourir*.

## 2. Concision et coût en contexte

Le contexte est une ressource partagée. Seuls le `name` et la `description` de
chaque outil installé sont chargés au démarrage ; le corps ne l'est qu'une fois
l'outil jugé pertinent. La `description` est donc peu coûteuse et le corps
coûteux — et une fois chargé, ce corps entre en concurrence avec l'historique de
la conversation.

L'hypothèse par défaut est que **l'agent est déjà compétent**. N'ajouter que ce
qu'il ne sait pas. Pour chaque paragraphe : est-il nécessaire ? relève-t-il de
la connaissance générale ? justifie-t-il son coût ?

Une instruction concise nomme la bibliothèque retenue et montre l'appel. Une
instruction verbeuse explique en plus ce qu'est le format de fichier, pourquoi
cette bibliothèque a été choisie et comment l'installer — trois choses que
l'agent sait déjà.

## 3. Découpage : limiter la longueur du document canonique

Le document canonique — `SKILL.md`, le fichier d'un agent — est une vue
d'ensemble qui renvoie au détail. Un fichier embarqué ne coûte rien tant qu'il
n'est pas lu : c'est ce qui rend le découpage gratuit.

- **Corps de moins de 500 lignes.** Au-delà, répartir le détail dans des
  fichiers embarqués.
- **Références à un seul niveau.** Chaque fichier embarqué est lié directement
  depuis le document canonique. Quand une référence renvoie à une autre
  référence, l'agent peut survoler cette seconde référence au lieu de la lire,
  et agir à partir d'une information incomplète.
- **Sommaire au-delà de 100 lignes.** Un fichier de référence long s'ouvre par
  un sommaire, pour que sa portée reste visible même en lecture partielle.
- **Organiser par domaine, pas par séquence.** `reference/finance.md`,
  `reference/fiscalite.md` — jamais `doc1.md`, `doc2.md`. Une demande sur un
  domaine ne charge alors que le fichier de ce domaine.
- **Nommer les fichiers explicitement.**

## 4. Latitude laissée à l'agent

Ajuster la précision de l'instruction à la fragilité de la tâche.

| Latitude | Forme | Quand |
|---|---|---|
| Large | Prose, points d'attention | Plusieurs approches valables ; la décision dépend du contexte |
| Moyenne | Gabarit, ou script paramétré | Un motif est préférable, une part de variation est acceptable |
| Étroite | Une commande exacte, sans paramètre | L'opération est fragile, la constance est critique, la séquence est fixe |

Une opération fragile appelle « lancer exactement cette commande, sans ajouter
d'option ». Un examen ouvert appelle une liste de points d'attention et aucun
script. La plupart des outils de ce dépôt relèvent à juste titre de la latitude
étroite : la choisir délibérément, pas par défaut.

## 5. Déroulés et suivi de progression

**Déroulés.** Décomposer une opération complexe en étapes numérotées, dans
l'ordre d'exécution. Des étapes explicites empêchent qu'une vérification soit
sautée.

### Le protocole de suivi de progression

Le protocole est la forme concrète que prend le suivi d'un déroulé dans ce
dépôt : la progression reste visible pendant l'exécution de l'outil, et aucune
étape n'est abandonnée en silence. Un outil réellement multi-étapes, dont la
séquence comporte une vérification que l'agent tend à sauter, prescrit à l'agent
ce qui suit.

1. **Ouvrir la liste avant la première action** du déroulé, une ligne par étape,
   formulée à l'impératif. Les marqueurs sont exactement `[ ]` non commencée,
   `[~]` en cours, `[x]` terminée, `[-]` abandonnée — cette dernière avec une
   raison courte sur la même ligne. Une étape porte `[~]` dès que son travail
   est engagé, et plusieurs peuvent le porter en même temps lorsqu'elles sont
   réellement menées en parallèle — le marqueur décrit ce qui est en cours, pas
   une intention.

2. **Ré-afficher la liste entière à chaque changement d'état** : une étape
   démarre, une étape se termine, une étape est ajoutée après avoir été
   découverte en cours de route, une étape est abandonnée. Plusieurs changements
   survenant dans une même réponse produisent un seul rendu à jour, pas un par
   changement. La forme rendue est toujours :

   ```markdown
   **Tâches**
   - [x] Étape terminée
   - [~] Étape en cours
   - [ ] Étape non commencée
   ```

3. **Faire de la vérification une étape comme les autres, et nommer le contrôle
   auquel elle s'adosse.** Une étape ne passe à `[x]` que sur un contrôle réel,
   jamais sur une simple déclaration :
   `[x] Valider les outils — validateur au vert` est adossé au validateur,
   `[x] Valider les outils` seul ne l'est pas.

4. **Clore sur la liste terminée.** La dernière réponse de la tâche se termine
   par le rendu final, pour qu'une étape sautée y apparaisse comme non terminée.
   La liste est un artefact de travail, pas un résumé : ne jamais la
   reconstituer après coup pour une tâche qui n'a pas été suivie pendant son
   déroulement.

**Les deux suivis.** Quand la session expose son propre outil de liste de
tâches, c'est cet outil qui est employé et qui fait l'affichage ; le bloc
Markdown ne s'écrit pas en double à côté. Quand aucun outil de ce type n'est
exposé, le bloc s'écrit dans la réponse. Les deux suivis satisfont le protocole
**à égalité** : aucun n'est un repli ni un échec, et un outil ne prescrit pas
d'en préférer un. Un outil qui nomme le suivi applicable le déduit des outils de
session dont il dispose réellement, et non d'une hypothèse sur la session.

**Quand l'appliquer.** Le suivi s'impose dès que le travail compte trois étapes
distinctes ou plus, plusieurs fichiers ou modules touchés, ou un déroulé en
phases. En deçà — une modification en une seule étape, une commande unique, une
question directe — le formalisme coûterait plus qu'il ne rapporterait (§2). Pour
un outil qui couvre **plusieurs cas d'usage d'ampleur inégale** — certains en
plusieurs étapes, d'autres réduits à une lecture ou à un appel unique — trancher
dans l'outil : énumérer les cas qui demandent le suivi et ceux qui s'en passent,
une fois pour toutes, plutôt que de laisser l'agent rejuger la question à chaque
exécution.

**Où l'énoncer.** Le protocole occupe une **section dédiée**, titrée « Suivi de
progression — impératif » ou « — indicatif », placée **en tête de l'outil** :
après l'introduction, avant le déroulé. Elle se lit donc avant la première
action au lieu d'être découverte au milieu des étapes. Elle porte, dans cet
ordre : la déclaration du nombre de phases, les marqueurs et l'obligation de
ré-affichage, le suivi applicable, la liste `**Tâches**`, puis la phase de
contrôle et ce à quoi elle s'adosse. `skills/clean-android-tv/SKILL.md` en est
la forme de référence.

**Comment l'énoncer.** Dire dans l'outil si le suivi est **impératif**
(« toujours suivre ce déroulé ») ou **indicatif** (§6). L'outil ne réénonce pas
la règle : il déclare conduire une tâche en plusieurs phases, recopie les
marqueurs et l'obligation de ré-affichage, et fournit sa propre liste de phases
sous l'en-tête `**Tâches**`. Ne pas nommer l'outil de liste — écrire « la liste
de tâches de la session », car le nom change d'un environnement à l'autre. Si la
session conditionne l'accès à sa liste de tâches au champ `tools` d'un agent,
accorder l'outil de liste de tâches dans ce champ
([CONVENTIONS.md](CONVENTIONS.md) §4.1).

**Auto-suffisance.** Une skill ou un agent s'installe isolément et ne peut pas
renvoyer vers ce document ([CONVENTIONS.md](CONVENTIONS.md) §1.7). Le protocole
se **recopie** dans l'outil, adapté à son déroulé ; il ne s'y lie pas.

**Boucles de vérification.** La boucle est *lancer → observer → corriger →
relancer*, et c'est le levier de qualité le plus fort. Le contrôle n'a pas à
être un script : un document de style que l'agent relit et auquel il compare son
travail en est un. Énoncer la boucle, sa condition de sortie (« ne poursuivre
qu'une fois le contrôle au vert ») et le point de retour en cas d'échec
(« reprendre à l'étape 2 »).

## 6. Règles de contenu

- **Aucune information datée.** Ne pas écrire « avant telle version, employer
  l'ancienne interface ». Énoncer la méthode courante, et reléguer ce qui est
  dépassé dans une section à part si le contexte historique est nécessaire.
- **Terminologie constante.** Choisir un terme et s'y tenir. C'est l'objet de
  [VOCABULARY.md](VOCABULARY.md) : un vocabulaire flottant dégrade la lecture.
- **Ne pas offrir de catalogue d'options.** Donner une valeur par défaut, puis
  nommer l'exception qui la remplace (« employer X ; pour un document scanné,
  employer Y »), plutôt que cinq bibliothèques interchangeables.
- **Gabarits.** Fournir le format de sortie explicitement, et le marquer
  **impératif** (« reproduire ce gabarit tel quel ») ou **indicatif** (« une
  valeur par défaut raisonnable, à adapter »). Un gabarit non marqué est ambigu.
- **Exemples.** Quand la qualité de la sortie dépend de la forme, donner des
  couples entrée/sortie concrets. Un exemple transmet la forme visée plus
  fidèlement qu'une description de cette forme.
- **Branchements explicites.** Là où le déroulé bifurque, nommer le point de
  décision (« s'agit-il d'une création ? suivre le déroulé de création
  ci-dessous »). Quand une branche grossit, la déplacer dans son propre fichier
  et prescrire de lire celui qui correspond à la tâche.

## 7. Scripts embarqués

Un script préécrit est plus fiable que du code produit à la volée, ne consomme
aucun contexte tant qu'il n'a rien affiché, et garantit la constance d'une
exécution à l'autre.

- **Résoudre plutôt que reporter.** Traiter les cas d'erreur dans le script —
  fichier absent, autorisation refusée — au lieu de laisser remonter une
  exception que l'agent devra interpréter.
- **Aucune constante injustifiée.** Chaque délai, chaque nombre de tentatives,
  chaque seuil porte un commentaire qui explique sa valeur. Une valeur que
  l'auteur ne sait pas justifier est une valeur sur laquelle l'agent ne peut pas
  raisonner non plus.
- **Dire si le script se lance ou se lit.** « Lancer `export.py` pour produire
  le rapport » ou « voir `export.py` pour l'algorithme ». Sans précision, c'est
  qu'il se lance.
- **Déclarer les dépendances.** Ne pas supposer qu'un paquet est installé ;
  lister les dépendances, en renvoyant vers [PREREQUIS.md](PREREQUIS.md)
  plutôt qu'en recopiant une procédure.
- **Passer par un état intermédiaire contrôlable.** Pour une opération par lot,
  destructive ou à fort enjeu, employer *planifier → valider → appliquer* :
  faire écrire un plan dans un fichier, le valider par un script, et n'appliquer
  qu'ensuite. Les erreurs sont détectées avant toute modification, et le plan se
  reprend sans toucher aux originaux.
- **Rendre les messages de validation précis.** « Champ `date_signature`
  introuvable. Champs disponibles : nom_client, total, date_signature_signee »
  permet de corriger ; « échec de la validation » ne dit rien.

## 8. Références aux outils MCP

Quand un outil prescrit d'appeler un outil MCP, employer la forme qualifiée
`Serveur:nom_outil`. Sans le préfixe de serveur, la résolution peut échouer, en
particulier quand plusieurs serveurs MCP sont connectés.

## 9. Évaluation et itération

**Construire les scénarios avant la documentation**, pour que l'outil réponde à
des défaillances observées et non supposées :

1. Faire traiter des tâches représentatives **sans** l'outil, et relever les
   défaillances précises et le contexte manquant.
2. Construire au moins trois scénarios couvrant ces manques.
3. Établir le résultat de référence sans l'outil.
4. Écrire le minimum d'instructions qui comble les manques.
5. Rejouer, comparer à la référence, affiner.

Un scénario tient en quelques lignes : les outils chargés, la demande, les
fichiers d'entrée, et le comportement attendu sous forme d'énoncés observables.
Rien n'automatise ici l'exécution de ces scénarios : elle est manuelle.

**Itérer sur deux sessions.** Employer une session pour écrire et affiner
l'outil, et une session neuve pour l'**utiliser** sur du travail réel. Observer
la seconde et ramener les observations dans la première : quel fichier a été lu
en premier, quelle référence n'a jamais été ouverte, quelle règle énoncée n'a
pas été appliquée. Réorganiser d'après le comportement observé, pas d'après une
supposition — une règle ignorée demande en général à être rendue plus visible ou
formulée plus fermement, pas à être répétée.

## 10. Écarts locaux — où `CONVENTIONS.md` prévaut

Ce document est une synthèse de règles d'écriture d'usage général. Ce dépôt s'en
écarte sur les points suivants ; c'est [CONVENTIONS.md](CONVENTIONS.md) qui fait
autorité.

| Règle générale | Position de ce dépôt |
|---|---|
| `description` à la troisième personne (« Convertit un document… ») | Ce dépôt écrit les `description` à l'**infinitif** (« Convertir un document Markdown… »), forme idiomatique en français pour désigner une capacité. `CONVENTIONS.md` §2.1 fait autorité |
| Nom d'outil au gérondif (`processing-pdfs`) | Ce dépôt emploie le groupe nominal ou le verbe d'action — `clean-android-tv`, `setup-harness` |
| `allowed-tools` obligatoire | `CONVENTIONS.md` §2.1 le rend facultatif ; le moindre privilège du §2.2 s'applique dès que le champ est renseigné |
| Liste de déclencheurs incluant la forme `/nom` | `CONVENTIONS.md` §2.1 exige « À utiliser quand… », formulé avec les mots de l'utilisateur ; la forme `/nom` n'est pas requise |
| Placeholder d'un dossier d'agent, pour un outil installable sous plusieurs environnements | Sans objet : ce dépôt est spécifique à Claude. Le seul placeholder est `<NOM_VARIABLE>` (`CONVENTIONS.md` §1.2) |
| Prose neutre entre outils (« l'agent », jamais « Claude ») | Sans objet : `CONVENTIONS.md` §1.9 impose l'inverse. Sans contradiction avec l'interdiction du mot `claude` dans `name` (§1), qui est une contrainte de chargement et non une règle de rédaction |
| Séparateurs de chemin en `/` sans exception | **Non repris.** Ce dépôt ne fixe aucune convention de séparateur et n'a aucun script embarqué qui construise un chemin absolu ; la règle serait sans objet |

## 11. Checklist

Les items marqués **[mécanique]** sont vérifiés par `scripts/validate.py`. Les
autres relèvent du jugement : rien ne les vérifie mécaniquement ; ils dépendent
de la seule prose de ce document.

**Qualité de base**

- [ ] **[mécanique]** `name` tient en 64 caractères et n'emploie que minuscules,
      chiffres et traits d'union.
- [ ] **[mécanique]** `name` et `description` ne contiennent aucune balise XML.
- [ ] **[mécanique]** `description` est non vide et tient en 1 024 caractères.
- [ ] **[mécanique]** Le corps tient en moins de 500 lignes.
- [ ] `name` ne contient ni `anthropic` ni `claude`.
- [ ] `description` énonce ce que fait l'outil **et** ses conditions de
      déclenchement.
- [ ] Le détail est scindé en fichiers embarqués plutôt que de gonfler le corps.
- [ ] Les références sont à un seul niveau depuis le document canonique.
- [ ] Tout fichier de référence de plus de 100 lignes s'ouvre par un sommaire.
- [ ] Aucune information datée, ou elle est reléguée dans une section dédiée.
- [ ] La terminologie est constante et conforme à [VOCABULARY.md](VOCABULARY.md).
- [ ] Les exemples sont concrets plutôt qu'abstraits.
- [ ] La latitude laissée à l'agent correspond à la fragilité de la tâche.
- [ ] Les déroulés sont numérotés et portent une condition de sortie.
- [ ] **[mécanique]** Un outil multi-étapes porte l'en-tête `**Tâches**` et les
      quatre marqueurs `[ ]` `[~]` `[x]` `[-]` (§5).
- [ ] La liste de phases fournie par l'outil correspond réellement à son déroulé,
      et l'omission du suivi, quand elle a lieu, est délibérée et assumée.

**Scripts embarqués**

- [ ] Le script traite ses propres cas d'erreur.
- [ ] Chaque constante est justifiée par un commentaire.
- [ ] Les dépendances sont déclarées.
- [ ] Le document dit si le script se lance ou se lit.
- [ ] Une validation existe pour toute opération destructive ou par lot.

**Mise à l'épreuve**

- [ ] Au moins trois scénarios d'évaluation existent.
- [ ] L'outil a été employé sur du travail réel, dans une session neuve, pas
      seulement sur des cas construits.

# Projet 3 : Portail de notes du Lycée de Makepe (Groupe03, GLO niveau 5)

Application Flask + SQLite : les enseignants saisissent et corrigent les notes, chaque
élève consulte son bulletin (matricule + code), le proviseur consulte les statistiques.
La structure du bulletin (6 séquences, 14 matières en 4 groupes, coefficients, rang,
moyennes de classe, discipline, décision du conseil) reprend celle du Lycée de Makepe.

**Les élèves, enseignants et notes sont entièrement fictifs.**

## Installation

```
python -m venv venv
venv\Scripts\activate            (Windows)     ou     source venv/bin/activate     (Linux, macOS)
pip install -r requirements.txt
```

## Lancement (la base `projet.db` est déjà remplie)

```
python app.py
```

puis ouvrir http://127.0.0.1:5000

## Comptes de test

| Espace | Identifiant | Mot de passe / code |
|---|---|---|
| Élève, 6e Bilingue 1 | matricule `2025010001` | code `123456` |
| Élève, 5e Bilingue 2 | matricule `2025020001` | code `123456` |
| Élève, 4e Bilingue 1 | matricule `2025030001` | code `123456` |
| Élève, 3e Bilingue 3 | matricule `2025040001` | code `123456` |
| Proviseur (statistiques, toutes les classes) | login `admin` | `Admin!2026` |
| Enseignant de mathématiques (6e et 5e) | login `nkou` | `Prof!2026` |

Les autres enseignants (`tagne`, `essomba`, `kamga`, `mvondo`, `biyong`, `fokou`, `ndzana`,
`tchamba`, `ayissi`) ont le même mot de passe `Prof!2026`. Les 120 matricules et codes des
élèves sont listés dans `identifiants_test.csv`.

## Que tester ?

1. **Élève** : connexion, bulletin des séquences 1 à 4 (la séquence 5 est vide), historique avec
   graphique, fiche d'informations, impression du bulletin (bouton « Imprimer »).
2. **Enseignant** (`nkou`) : « Mes classes » puis une séquence. Le formulaire de saisie est
   pré-rempli. **Corriger une note, c'est changer sa valeur et enregistrer** (c'est la même
   page que la saisie). Essayer `25` : refus immédiat en JavaScript, puis refus par le serveur.
   Saisir la séquence 5 : la moyenne de la classe se calcule en direct.
3. **Proviseur** (`admin`) : statistiques de la séquence choisie.
4. **Sécurité** : un élève ne voit que son bulletin ; un enseignant ne saisit que ses matières
   dans ses classes (sinon page « Accès refusé »).

## Recréer la base de test

```
python donnees_test.py        (≈ 20 secondes : le hachage des 131 mots de passe est volontairement lent)
python exporter.py            (régénère export_projet.sql)
python tests_calculs.py       (vérifie moyennes, rangs et appréciations)
```

`donnees_test.py` utilise `random.seed(42)` : on obtient toujours les mêmes données. La base
peut aussi être recréée à partir de `export_projet.sql`
(`db.executescript(open("export_projet.sql", encoding="utf-8").read())`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | l'application Flask : routes, accès à la base, API JSON |
| `calculs.py` | règles de calcul sans Flask : moyenne coefficientée, rang avec ex æquo, trimestre, année, appréciation, décision |
| `schema.sql` | création des 8 tables, clés étrangères, contraintes `NOT NULL`, `UNIQUE`, `CHECK` |
| `donnees_test.py` | base de test : 4 classes, 120 élèves, 14 matières, 56 enseignements, séquences 1 à 4 |
| `templates/` | gabarits Jinja2, tous hérités de `base.html` |
| `static/css/main.css` | CSS commun à toutes les pages (mobile d'abord, ruptures à 768 px et 992 px) |
| `static/css/pages/` | un fichier CSS par page, pour ce qui n'est utilisé que par elle (`bulletin.css`, `saisie.css`, `statistiques.css`...) |
| `static/js/main.js` | JavaScript commun : menu, outils partagés par les graphiques (`fetch`) |
| `static/js/pages/` | un fichier JavaScript par page (`connexion.js`, `saisie.js`, `historique.js`...) |
| `static/js/lib/chart.umd.js` | bibliothèque Chart.js 4.4.1 (licence MIT), servie localement : le site fonctionne sans Internet |

## Règles de calcul

* **Moyenne d'une séquence** = Σ(note × coefficient) / Σ(coefficients des matières notées). Une
  matière sans note n'entre pas dans le calcul.
* **Trimestre** = moyenne de ses deux séquences ; **année** = moyenne des trimestres disponibles.
* **Rang** : deux élèves à égalité (moyenne arrondie à 2 décimales) ont le même rang, le suivant prend le
  rang d'après (1, 2, 2, 4).
* **Appréciation** : ≥ 18 Excellent, ≥ 16 Très bien, ≥ 14 Bien, ≥ 12 Assez bien, ≥ 10 Passable,
  ≥ 8 Insuffisant, sinon Médiocre.

## Routes

| Adresse | Méthode | Rôle |
|---|---|---|
| `/` | GET | accueil et connexion élève |
| `/connexion`, `/deconnexion` | POST | connexion et déconnexion |
| `/bulletin`, `/bulletin/<seq>` | GET | bulletin de la séquence (élève connecté) |
| `/historique`, `/fiche` | GET | moyennes par séquence et graphique ; fiche d'informations |
| `/enseignant/connexion` | GET, POST | connexion enseignant ou proviseur |
| `/enseignant` | GET | mes matières, mes classes |
| `/enseignant/saisie/<classe>/<matiere>/<seq>` | GET, POST | saisie **et correction** des notes d'une classe |
| `/enseignant/classe/<id>` | GET | liste de classe : moyennes, rangs |
| `/admin/statistiques` | GET | statistiques (proviseur) |
| `/api/classe/<id>/moyennes` | GET | moyennes et rangs d'une classe (JSON) |
| `/api/eleve/<id>/evolution` | GET | moyennes d'un élève et de sa classe par séquence (JSON) |
| `/api/statistiques` | GET | statistiques de toutes les classes (JSON) |

## Pour la mise en ligne

`debug=False` est déjà réglé dans `app.py`. Définir une vraie clé secrète :
`set SECRET_KEY=une-longue-phrase-secrete` (Windows) ou `export SECRET_KEY=...` (Linux).

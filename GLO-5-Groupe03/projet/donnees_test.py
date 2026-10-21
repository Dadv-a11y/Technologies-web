"""donnees_test.py : crée projet.db et la remplit avec des données de test réalistes.

Lancement : python donnees_test.py
Les élèves, enseignants et notes sont INVENTÉS (aucune donnée personnelle réelle).
Les séquences 1 à 4 sont remplies ; les séquences 5 et 6 restent vides pour
pouvoir montrer la saisie des notes en direct.
"""
import csv
import os
import random
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

DOSSIER = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(DOSSIER, "projet.db")
NB_ELEVES_PAR_CLASSE = 30
SEQUENCES_REMPLIES = [1, 2, 3, 4]

NOMS = ["Mbarga", "Ngo Bassa", "Fotso", "Atangana", "Njoya", "Ekane", "Tchoupo", "Bello",
        "Essomba", "Kamga", "Tagne", "Onana", "Mvondo", "Fokou", "Nana", "Abena",
        "Biyong", "Ngassa", "Tchamba", "Mbella", "Manga", "Nguimfack", "Ndzana", "Kouam",
        "Tala", "Ayissi", "Zambo", "Etoundi", "Simo", "Nkoulou", "Owona", "Djeukam"]
PRENOMS_M = ["Paul", "Kevin", "Ibrahim", "Moussa", "Brice", "Arnaud", "Junior", "Yannick",
             "Stéphane", "Cyrille", "Franck", "Hervé", "Samuel", "Joël", "Dimitri", "Boris"]
PRENOMS_F = ["Aline", "Marie", "Sandra", "Rose", "Ornella", "Estelle", "Christelle", "Grâce",
             "Nadège", "Vanessa", "Pamela", "Laurelle", "Prisca", "Sylvie", "Mireille", "Carine"]
VILLES = ["Douala", "Yaoundé", "Bafoussam", "Garoua", "Kribi", "Bamenda", "Édéa", "Limbé"]

# (nom, login) : le premier mot de passe de test est identique pour tous les enseignants.
ENSEIGNANTS = [
    ("Mme Nkou Hortense", "nkou"),        # 0
    ("M. Tagne Bertrand", "tagne"),       # 1
    ("M. Essomba Alain", "essomba"),      # 2
    ("Mme Kamga Pulchérie", "kamga"),     # 3
    ("M. Mvondo Rodrigue", "mvondo"),     # 4
    ("Mme Biyong Clarisse", "biyong"),    # 5
    ("M. Fokou Armand", "fokou"),         # 6
    ("Mme Ndzana Josiane", "ndzana"),     # 7
    ("M. Tchamba Éric", "tchamba"),       # 8
    ("Mme Ayissi Colette", "ayissi"),     # 9
]

GROUPES = ["Sciences et Technologies", "Langues et Littératures",
           "Développement personnel", "Sciences Humaines"]

# (matière, coefficient, numéro de groupe, enseignant de chacune des 4 classes)
MATIERES = [
    ("Mathématiques", 4, 0, [0, 0, 1, 1]),
    ("Sciences", 2, 0, [2, 2, 2, 2]),
    ("Informatique générale", 2, 0, [3, 3, 3, 3]),
    ("English", 2, 1, [4, 4, 4, 4]),
    ("Étude de texte", 2, 1, [5, 5, 5, 5]),
    ("Expression orale", 1, 1, [5, 5, 5, 5]),
    ("Latin", 2, 1, [6, 6, 6, 6]),
    ("Orthographe", 1, 1, [5, 5, 5, 5]),
    ("Rédaction", 2, 1, [5, 5, 5, 5]),
    ("Travail manuel", 2, 2, [7, 7, 7, 7]),
    ("Éducation physique", 2, 2, [8, 8, 8, 8]),
    ("ESF", 1, 2, [7, 7, 7, 7]),
    ("Histoire-Géographie", 4, 3, [9, 9, 9, 9]),
    ("Éducation civique", 2, 3, [9, 9, 9, 9]),
]

# (nom de la classe, année de naissance habituelle, professeur principal)
CLASSES = [
    ("6e Bilingue 1", 2014, 3),
    ("5e Bilingue 2", 2013, 5),
    ("4e Bilingue 1", 2012, 0),
    ("3e Bilingue 3", 2011, 9),
]


def telephone():
    """Numéro camerounais fictif : 9 chiffres commençant par 6."""
    return "6" + "".join(random.choice("0123456789") for _ in range(8))


def note_plausible(niveau_eleve, ecart_matiere, sequence):
    """Une note sur 20, arrondie au demi-point, autour du niveau de l'élève."""
    brute = niveau_eleve + ecart_matiere + random.gauss(0, 1.2) + 0.15 * sequence
    return min(20.0, max(0.0, round(brute * 2) / 2))


def remplir(db):
    # --- 1. Tables « indépendantes » d'abord : enseignants, groupes, matières ---
    db.execute("INSERT INTO enseignants (nom, login, empreinte, role) VALUES (?, ?, ?, 'admin')",
               ("M. le Proviseur", "admin", generate_password_hash("Admin!2026")))
    for nom, login in ENSEIGNANTS:
        db.execute("INSERT INTO enseignants (nom, login, empreinte) VALUES (?, ?, ?)",
                   (nom, login, generate_password_hash("Prof!2026")))
    ids_enseignants = [l[0] for l in db.execute(
        "SELECT id FROM enseignants WHERE role = 'enseignant' ORDER BY id")]

    for ordre, nom in enumerate(GROUPES, start=1):
        db.execute("INSERT INTO groupes_matieres (nom, ordre) VALUES (?, ?)", (nom, ordre))
    for ordre, (nom, coef, groupe, _) in enumerate(MATIERES, start=1):
        db.execute("INSERT INTO matieres (nom, coefficient, groupe_id, ordre) VALUES (?, ?, ?, ?)",
                   (nom, coef, groupe + 1, ordre))

    # --- 2. Classes et enseignements (qui enseigne quoi dans quelle classe) ---
    for nom, _, principal in CLASSES:
        db.execute("INSERT INTO classes (nom, filiere, effectif_max, professeur_principal_id) "
                   "VALUES (?, 'Enseignement général bilingue', 60, ?)",
                   (nom, ids_enseignants[principal]))
    for c in range(len(CLASSES)):
        for m, (_, _, _, profs) in enumerate(MATIERES):
            db.execute("INSERT INTO enseignements (classe_id, matiere_id, enseignant_id) "
                       "VALUES (?, ?, ?)", (c + 1, m + 1, ids_enseignants[profs[c]]))

    # --- 3. Élèves, puis leurs notes et leur discipline ---
    identifiants = []
    for c, (nom_classe, annee_naiss, _) in enumerate(CLASSES, start=1):
        for n in range(1, NB_ELEVES_PAR_CLASSE + 1):
            sexe = random.choice("MF")
            prenom = random.choice(PRENOMS_M if sexe == "M" else PRENOMS_F)
            nom = random.choice(NOMS)
            matricule = f"2025{c:02d}{n:04d}"
            code = "123456" if n == 1 else str(random.randint(100000, 999999))
            naissance = date(annee_naiss, 1, 1) + timedelta(days=random.randint(0, 364))
            cur = db.execute(
                "INSERT INTO eleves (matricule, nom, prenom, sexe, date_naissance, lieu_naissance, "
                "statut, classe_id, code_empreinte, nom_pere, tel_pere, nom_mere, tel_mere) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (matricule, nom, prenom, sexe, naissance.isoformat(), random.choice(VILLES),
                 random.choice(["ancien"] * 4 + ["nouveau"]), c,
                 generate_password_hash(code),
                 "M. " + nom + " " + random.choice(PRENOMS_M), telephone(),
                 "Mme " + nom + " " + random.choice(PRENOMS_F), telephone()))
            eleve_id = cur.lastrowid
            identifiants.append((matricule, nom, prenom, nom_classe, code))

            niveau = random.gauss(11.5, 2.8)
            ecarts = [random.gauss(0, 1.8) for _ in MATIERES]
            for seq in SEQUENCES_REMPLIES:
                for m, (_, _, _, profs) in enumerate(MATIERES):
                    if random.random() < 0.015:      # élève absent à l'évaluation : pas de note
                        continue
                    db.execute(
                        "INSERT INTO notes (eleve_id, matiere_id, sequence, valeur, enseignant_id) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (eleve_id, m + 1, seq, note_plausible(niveau, ecarts[m], seq),
                         ids_enseignants[profs[c - 1]]))
                absences = random.choice([0, 0, 0, 1, 2, 3, 5])
                db.execute(
                    "INSERT INTO discipline (eleve_id, sequence, absences, absences_justifiees, "
                    "consignes, exclusions) VALUES (?, ?, ?, ?, ?, ?)",
                    (eleve_id, seq, absences, random.randint(0, absences),
                     random.choice([0] * 8 + [1, 2]), random.choice([0] * 15 + [1])))
    db.commit()
    return identifiants


if __name__ == "__main__":
    random.seed(42)                                   # mêmes données à chaque lancement
    if os.path.exists(BASE):
        os.remove(BASE)
    db = sqlite3.connect(BASE)
    db.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(DOSSIER, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    identifiants = remplir(db)

    # Liste des identifiants de test (aucune donnée réelle) pour essayer les comptes élèves.
    with open(os.path.join(DOSSIER, "identifiants_test.csv"), "w", encoding="utf-8", newline="") as f:
        ecrivain = csv.writer(f, delimiter=";")
        ecrivain.writerow(["matricule", "nom", "prenom", "classe", "code"])
        ecrivain.writerows(identifiants)

    for table in ("enseignants", "classes", "matieres", "eleves", "enseignements", "notes", "discipline"):
        n = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table} : {n} lignes")
    db.close()

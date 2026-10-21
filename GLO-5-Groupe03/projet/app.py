"""app.py : portail de notes du Lycée de Makepe (Projet 3, GLO-5-Groupe03).

Les élèves consultent leur bulletin (matricule + code), les enseignants saisissent
et corrigent les notes de leurs classes, le proviseur consulte les statistiques.
Les règles de calcul (moyennes, rangs, appréciations) sont dans calculs.py.
"""
import math
import os
import re
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import calculs

app = Flask(__name__)
# La clé signe le cookie de session : en production, la fournir par variable d'environnement.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "changez-moi-en-production")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"      # le cookie n'accompagne pas les POST venus d'un autre site

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projet.db")
ANNEE_SCOLAIRE = "2025/2026"
NB_SEQUENCES = calculs.NB_SEQUENCES
# Empreinte factice : on la compare même quand le matricule n'existe pas,
# pour que le temps de réponse ne révèle pas si un matricule est valide.
EMPREINTE_FACTICE = generate_password_hash("empreinte-factice")


# ---------- Connexion à la base ----------
def get_db():
    """Ouvre une connexion par requête et la réutilise pendant cette requête."""
    if "db" not in g:
        g.db = sqlite3.connect(BASE)
        g.db.row_factory = sqlite3.Row                  # lignes accessibles par nom de colonne
        g.db.execute("PRAGMA foreign_keys = ON")        # SQLite ne vérifie les clés qu'à la demande
    return g.db


@app.teardown_appcontext
def fermer_db(exception):
    """Ferme la connexion à la fin de chaque requête."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crée les tables à partir de schema.sql (efface les données existantes)."""
    with app.app_context():
        db = get_db()
        with open(os.path.join(os.path.dirname(BASE), "schema.sql"), encoding="utf-8") as f:
            db.executescript(f.read())
        db.commit()


# ---------- Affichage : filtres et variables communes aux gabarits ----------
@app.template_filter("note")
def filtre_note(valeur, decimales=2):
    """14.8393 -> « 14,84 » ; pas de valeur -> un tiret."""
    if valeur is None:
        return "—"
    return f"{calculs.arrondir(valeur, decimales):.{decimales}f}".replace(".", ",")


@app.template_filter("rang")
def filtre_rang(valeur):
    """1 -> « 1er », 4 -> « 4e »."""
    if valeur is None:
        return "—"
    return "1er" if valeur == 1 else f"{valeur}e"


@app.template_filter("date_fr")
def filtre_date(texte):
    """2013-04-14 -> 14/04/2013."""
    return "/".join(reversed(texte.split("-"))) if texte else ""


@app.context_processor
def variables_communes():
    """Ce que base.html doit savoir sur la personne connectée."""
    return {
        "annee_scolaire": ANNEE_SCOLAIRE,
        "nb_sequences": NB_SEQUENCES,
        "role": session.get("role"),
        "nom_connecte": session.get("nom"),
    }


# ---------- Protection des pages ----------
def eleve_requis(fonction):
    """Réserve une page aux élèves connectés."""
    @wraps(fonction)
    def decorateur(*args, **kwargs):
        if "eleve_id" not in session:
            flash("Connectez-vous avec votre matricule et votre code d'accès.", "erreur")
            return redirect(url_for("accueil"))
        return fonction(*args, **kwargs)
    return decorateur


def connexion_requise(fonction):
    """Réserve une page aux enseignants (et au proviseur) connectés."""
    @wraps(fonction)
    def decorateur(*args, **kwargs):
        if "enseignant_id" not in session:
            flash("Connectez-vous pour accéder à l'espace enseignant.", "erreur")
            return redirect(url_for("connexion_enseignant"))
        return fonction(*args, **kwargs)
    return decorateur


def admin_requis(fonction):
    """Réserve une page au proviseur (rôle admin)."""
    @wraps(fonction)
    @connexion_requise
    def decorateur(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return fonction(*args, **kwargs)
    return decorateur


def peut_voir_classe(db, classe_id):
    """Le proviseur voit tout ; un enseignant voit les classes où il enseigne ou dont il est principal."""
    if session.get("role") == "admin":
        return True
    ligne = db.execute(
        "SELECT 1 FROM classes WHERE id = ? AND (professeur_principal_id = ? "
        "OR id IN (SELECT classe_id FROM enseignements WHERE enseignant_id = ?))",
        (classe_id, session["enseignant_id"], session["enseignant_id"])).fetchone()
    return ligne is not None


def lire_sequence(defaut):
    """Lit ?seq=3 dans l'adresse ; 404 si ce n'est pas un nombre de 1 à 6."""
    if "seq" not in request.args:
        return defaut
    seq = request.args.get("seq", type=int)
    if seq is None or not 1 <= seq <= NB_SEQUENCES:
        abort(404)
    return seq


# ---------- Chargement et analyse d'une classe ----------
def charger_classe(db, classe_id):
    """Lit en 4 requêtes tout ce qu'il faut pour calculer les moyennes d'une classe."""
    classe = db.execute("SELECT * FROM classes WHERE id = ?", (classe_id,)).fetchone()
    if classe is None:
        abort(404)
    eleves = db.execute("SELECT * FROM eleves WHERE classe_id = ? ORDER BY nom, prenom",
                        (classe_id,)).fetchall()
    matieres = db.execute(
        "SELECT m.*, g.nom AS groupe_nom FROM matieres m "
        "JOIN groupes_matieres g ON g.id = m.groupe_id ORDER BY g.ordre, m.ordre").fetchall()
    lignes = db.execute(
        "SELECT n.eleve_id, n.matiere_id, n.sequence, n.valeur FROM notes n "
        "JOIN eleves e ON e.id = n.eleve_id WHERE e.classe_id = ?", (classe_id,)).fetchall()
    notes = {(l["eleve_id"], l["matiere_id"], l["sequence"]): l["valeur"] for l in lignes}
    return classe, eleves, matieres, notes


def analyser_classe(db, classe_id):
    """Charge la classe et calcule la moyenne de chaque élève pour chaque séquence."""
    classe, eleves, matieres, notes = charger_classe(db, classe_id)
    coefs = {m["id"]: m["coefficient"] for m in matieres}
    ids = [e["id"] for e in eleves]
    moyennes = {seq: calculs.moyennes_classe(notes, coefs, ids, seq)
                for seq in range(1, NB_SEQUENCES + 1)}
    avec_notes = [seq for seq in moyennes if any(m is not None for m in moyennes[seq].values())]
    return {
        "classe": classe, "eleves": eleves, "matieres": matieres, "notes": notes,
        "ids": ids, "moyennes": moyennes,
        "derniere_sequence": max(avec_notes, default=1),
    }


def moyenne_annuelle_a(analyse, eleve_id, seq):
    """Moyenne annuelle d'un élève en tenant compte des séquences 1 à seq."""
    par_sequence = {s: analyse["moyennes"][s][eleve_id] for s in range(1, seq + 1)}
    return calculs.moyenne_annuelle(par_sequence)


def moyenne_de_la_classe(moyennes_seq):
    """Moyenne des moyennes des élèves qui ont au moins une note."""
    return calculs.moyenne(m for m in moyennes_seq.values() if m is not None)


def resume_classe(analyse, seq):
    """Tableau de classe d'une séquence : moyennes, rangs, appréciations et chiffres clés."""
    moy_seq = analyse["moyennes"][seq]
    rangs = calculs.classer(moy_seq)
    annuelles = {e: moyenne_annuelle_a(analyse, e, seq) for e in analyse["ids"]}
    rangs_annuels = calculs.classer(annuelles)
    lignes = []
    for e in analyse["eleves"]:
        lignes.append({
            "id": e["id"], "matricule": e["matricule"], "nom": e["nom"], "prenom": e["prenom"],
            "moyenne": moy_seq[e["id"]], "rang": rangs.get(e["id"]),
            "appreciation": calculs.appreciation(moy_seq[e["id"]]),
            "annuelle": annuelles[e["id"]], "rang_annuel": rangs_annuels.get(e["id"]),
        })
    # Classés par rang ; les élèves sans note à la fin, par ordre alphabétique.
    lignes.sort(key=lambda l: (l["rang"] is None, l["rang"] or 0, l["nom"], l["prenom"]))
    valides = [m for m in moy_seq.values() if m is not None]
    return {
        "sequence": seq, "lignes": lignes,
        "effectif": len(analyse["eleves"]), "notes": len(valides),
        "moyenne": moyenne_de_la_classe(moy_seq),
        "premier": max(valides, default=None), "dernier": min(valides, default=None),
        "reussites": sum(1 for m in valides if calculs.a_reussi(m)),
        "taux": 100 * sum(1 for m in valides if calculs.a_reussi(m)) / len(valides) if valides else None,
    }


def construire_bulletin(db, eleve, seq):
    """Rassemble tout ce que le bulletin d'une séquence affiche pour un élève."""
    a = analyser_classe(db, eleve["classe_id"])
    moy_seq = a["moyennes"][seq]
    rang = calculs.classer(moy_seq).get(eleve["id"])
    annuelle = moyenne_annuelle_a(a, eleve["id"], seq)
    annuelles = {e: moyenne_annuelle_a(a, e, seq) for e in a["ids"]}
    profs = {l["matiere_id"]: l["nom"] for l in db.execute(
        "SELECT en.matiere_id, p.nom FROM enseignements en "
        "JOIN enseignants p ON p.id = en.enseignant_id WHERE en.classe_id = ?",
        (eleve["classe_id"],))}

    groupes = []
    for m in a["matieres"]:
        if not groupes or groupes[-1]["nom"] != m["groupe_nom"]:
            groupes.append({"nom": m["groupe_nom"], "matieres": [], "points": 0.0, "coef": 0})
        groupe = groupes[-1]
        de_la_classe = {e: a["notes"][(e, m["id"], seq)] for e in a["ids"]
                        if (e, m["id"], seq) in a["notes"]}
        note = de_la_classe.get(eleve["id"])
        if note is not None:
            groupe["points"] += note * m["coefficient"]
            groupe["coef"] += m["coefficient"]
        groupe["matieres"].append({
            "nom": m["nom"], "coefficient": m["coefficient"], "note": note,
            "points": None if note is None else note * m["coefficient"],
            "rang": calculs.classer(de_la_classe).get(eleve["id"]),
            "moyenne_classe": calculs.moyenne(de_la_classe.values()),
            "professeur": profs.get(m["id"], ""), "appreciation": calculs.appreciation(note),
        })
    for groupe in groupes:
        groupe["moyenne"] = groupe["points"] / groupe["coef"] if groupe["coef"] else None

    valides = [x for x in moy_seq.values() if x is not None]
    discipline = db.execute("SELECT * FROM discipline WHERE eleve_id = ? AND sequence = ?",
                            (eleve["id"], seq)).fetchone()
    moy = moy_seq[eleve["id"]]
    return {
        "eleve": eleve, "classe": a["classe"], "sequence": seq, "groupes": groupes,
        "moyenne": moy, "rang": rang, "effectif": len(a["eleves"]),
        "appreciation": calculs.appreciation(moy), "decision": calculs.decision_conseil(moy),
        "moyenne_classe": moyenne_de_la_classe(moy_seq),
        "premier": max(valides, default=None), "dernier": min(valides, default=None),
        "reussites": sum(1 for x in valides if calculs.a_reussi(x)),
        "trimestre": calculs.trimestre_de(seq),
        "moyenne_trimestre": calculs.moyenne_trimestre(
            {s: a["moyennes"][s][eleve["id"]] for s in range(1, seq + 1)}, calculs.trimestre_de(seq)),
        "annuelle": annuelle, "rang_annuel": calculs.classer(annuelles).get(eleve["id"]),
        "discipline": discipline, "derniere_sequence": a["derniere_sequence"],
        "a_des_notes": moy is not None,
    }


def construire_historique(db, eleve):
    """Moyenne, rang et moyenne de classe de chaque séquence pour un élève."""
    a = analyser_classe(db, eleve["classe_id"])
    lignes = []
    for seq in range(1, NB_SEQUENCES + 1):
        moy_seq = a["moyennes"][seq]
        lignes.append({
            "sequence": seq, "moyenne": moy_seq[eleve["id"]],
            "rang": calculs.classer(moy_seq).get(eleve["id"]),
            "moyenne_classe": moyenne_de_la_classe(moy_seq),
        })
    par_sequence = {l["sequence"]: l["moyenne"] for l in lignes}
    return {
        "lignes": lignes, "effectif": len(a["eleves"]),
        "trimestres": [{"numero": t, "moyenne": calculs.moyenne_trimestre(par_sequence, t)}
                       for t in calculs.TRIMESTRES],
        "annuelle": calculs.moyenne_annuelle(par_sequence),
    }


def calculer_statistiques(db, seq):
    """Les 4 statistiques demandées, classe par classe, pour une séquence."""
    resultat = []
    for classe in db.execute("SELECT id, nom FROM classes ORDER BY id").fetchall():
        a = analyser_classe(db, classe["id"])
        resume = resume_classe(a, seq)
        # 2. moyenne de chaque matière
        par_matiere = []
        for m in a["matieres"]:
            valeurs = [a["notes"][(e, m["id"], seq)] for e in a["ids"] if (e, m["id"], seq) in a["notes"]]
            par_matiere.append({"matiere": m["nom"],
                                "moyenne": calculs.arrondir(calculs.moyenne(valeurs)),
                                "notes": len(valeurs)})
        # 3. les trois premiers
        premiers = [{"rang": l["rang"], "nom": f"{l['nom']} {l['prenom']}",
                     "moyenne": calculs.arrondir(l["moyenne"])}
                    for l in resume["lignes"] if l["rang"] is not None][:3]
        # 4. répartition par tranches
        tranches = {nom: 0 for nom in calculs.TRANCHES}
        for m in a["moyennes"][seq].values():
            if m is not None:
                tranches[calculs.tranche(m)] += 1
        resultat.append({
            "classe_id": classe["id"], "classe": classe["nom"], "effectif": resume["effectif"],
            "notes": resume["notes"],
            "moyenne_generale": calculs.arrondir(resume["moyenne"]),       # 1.
            "taux_reussite": None if resume["taux"] is None else round(resume["taux"], 1),
            "par_matiere": par_matiere, "premiers": premiers, "tranches": tranches,
        })
    return resultat


# ---------- Espace élève ----------
@app.route("/")
def accueil():
    if "eleve_id" in session:
        return redirect(url_for("bulletin"))
    return render_template("index.html", matricule="")


@app.route("/connexion", methods=["POST"])
def connexion():
    matricule = request.form.get("matricule", "").strip()
    code = request.form.get("code", "").strip()
    erreurs = []
    if not re.fullmatch(r"\d{10}", matricule):
        erreurs.append("Le matricule comporte 10 chiffres.")
    if not re.fullmatch(r"\d{6}", code):
        erreurs.append("Le code d'accès comporte 6 chiffres.")
    if erreurs:
        for e in erreurs:
            flash(e, "erreur")
        return render_template("index.html", matricule=matricule), 400

    eleve = get_db().execute(
        "SELECT id, nom, prenom, code_empreinte FROM eleves WHERE matricule = ?",
        (matricule,)).fetchone()
    empreinte = eleve["code_empreinte"] if eleve else EMPREINTE_FACTICE
    if not check_password_hash(empreinte, code) or eleve is None:
        flash("Matricule ou code d'accès incorrect.", "erreur")
        return render_template("index.html", matricule=matricule), 401

    session.clear()                                     # repart d'une session neuve
    session["eleve_id"] = eleve["id"]
    session["nom"] = f"{eleve['prenom']} {eleve['nom']}"
    session["role"] = "eleve"
    return redirect(url_for("bulletin"))


@app.route("/deconnexion", methods=["POST"])
def deconnexion():
    session.clear()
    flash("Vous êtes déconnecté(e).", "succes")
    return redirect(url_for("accueil"))


def eleve_connecte(db):
    """L'élève de la session : l'identifiant ne vient jamais de l'adresse."""
    eleve = db.execute("SELECT e.*, c.nom AS classe_nom FROM eleves e "
                       "JOIN classes c ON c.id = e.classe_id WHERE e.id = ?",
                       (session["eleve_id"],)).fetchone()
    if eleve is None:                                   # compte supprimé entre-temps
        session.clear()
        abort(403)
    return eleve


@app.route("/bulletin")
@app.route("/bulletin/<int:seq>")
@eleve_requis
def bulletin(seq=None):
    db = get_db()
    eleve = eleve_connecte(db)
    if seq is not None and not 1 <= seq <= NB_SEQUENCES:
        abort(404)
    if seq is None:                                     # par défaut : la dernière séquence notée
        seq = analyser_classe(db, eleve["classe_id"])["derniere_sequence"]
    return render_template("bulletin.html", b=construire_bulletin(db, eleve, seq))


@app.route("/historique")
@eleve_requis
def historique():
    db = get_db()
    eleve = eleve_connecte(db)
    return render_template("historique.html", eleve=eleve, h=construire_historique(db, eleve))


@app.route("/fiche")
@eleve_requis
def fiche():
    db = get_db()
    eleve = eleve_connecte(db)
    principal = db.execute(
        "SELECT p.nom FROM classes c LEFT JOIN enseignants p ON p.id = c.professeur_principal_id "
        "WHERE c.id = ?", (eleve["classe_id"],)).fetchone()
    effectif = db.execute("SELECT COUNT(*) FROM eleves WHERE classe_id = ?",
                          (eleve["classe_id"],)).fetchone()[0]
    discipline = db.execute("SELECT * FROM discipline WHERE eleve_id = ? ORDER BY sequence",
                            (eleve["id"],)).fetchall()
    return render_template("fiche.html", eleve=eleve, principal=principal["nom"],
                           effectif=effectif, discipline=discipline)


# ---------- Espace enseignant ----------
@app.route("/enseignant/connexion", methods=["GET", "POST"])
def connexion_enseignant():
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")
        if not login or not mot_de_passe:
            flash("Le login et le mot de passe sont obligatoires.", "erreur")
            return render_template("enseignant_connexion.html", login=login), 400
        ens = get_db().execute("SELECT * FROM enseignants WHERE login = ?", (login,)).fetchone()
        empreinte = ens["empreinte"] if ens else EMPREINTE_FACTICE
        if not check_password_hash(empreinte, mot_de_passe) or ens is None:
            flash("Login ou mot de passe incorrect.", "erreur")
            return render_template("enseignant_connexion.html", login=login), 401
        session.clear()
        session["enseignant_id"] = ens["id"]
        session["nom"] = ens["nom"]
        session["role"] = ens["role"]
        return redirect(url_for("tableau_enseignant"))
    return render_template("enseignant_connexion.html", login="")


@app.route("/enseignant")
@connexion_requise
def tableau_enseignant():
    db = get_db()
    moi = session["enseignant_id"]
    enseignements = db.execute(
        "SELECT en.classe_id, en.matiere_id, c.nom AS classe, m.nom AS matiere "
        "FROM enseignements en JOIN classes c ON c.id = en.classe_id "
        "JOIN matieres m ON m.id = en.matiere_id "
        "WHERE en.enseignant_id = ? ORDER BY c.id, m.ordre", (moi,)).fetchall()
    if session["role"] == "admin":
        classes = db.execute("SELECT id, nom FROM classes ORDER BY id").fetchall()
    else:
        classes = db.execute(
            "SELECT id, nom FROM classes WHERE professeur_principal_id = ? "
            "OR id IN (SELECT classe_id FROM enseignements WHERE enseignant_id = ?) ORDER BY id",
            (moi, moi)).fetchall()
    return render_template("enseignant_tableau.html", enseignements=enseignements, classes=classes)


@app.route("/enseignant/saisie/<int:classe_id>/<int:matiere_id>/<int:seq>", methods=["GET", "POST"])
@connexion_requise
def saisie(classe_id, matiere_id, seq):
    """Saisie ET correction des notes d'une matière pour toute une classe.

    Le formulaire est pré-rempli avec les notes déjà enregistrées : pour corriger
    une note, on change sa valeur et on enregistre ; une case laissée vide est ignorée.
    """
    db = get_db()
    if not 1 <= seq <= NB_SEQUENCES:
        abort(404)
    classe = db.execute("SELECT * FROM classes WHERE id = ?", (classe_id,)).fetchone()
    matiere = db.execute("SELECT * FROM matieres WHERE id = ?", (matiere_id,)).fetchone()
    if classe is None or matiere is None:
        abort(404)
    # Un enseignant ne saisit que les matières qu'il enseigne dans cette classe.
    if db.execute("SELECT 1 FROM enseignements WHERE classe_id = ? AND matiere_id = ? "
                  "AND enseignant_id = ?", (classe_id, matiere_id, session["enseignant_id"])).fetchone() is None:
        abort(403)

    eleves = db.execute("SELECT id, matricule, nom, prenom FROM eleves WHERE classe_id = ? "
                        "ORDER BY nom, prenom", (classe_id,)).fetchall()
    enregistrees = {l["eleve_id"]: l["valeur"] for l in db.execute(
        "SELECT eleve_id, valeur FROM notes WHERE matiere_id = ? AND sequence = ? "
        "AND eleve_id IN (SELECT id FROM eleves WHERE classe_id = ?)", (matiere_id, seq, classe_id))}
    affichees = {e["id"]: enregistrees.get(e["id"], "") for e in eleves}

    if request.method == "POST":
        nouvelles, erreurs = {}, []
        for e in eleves:
            texte = request.form.get(f"note_{e['id']}", "").strip()
            affichees[e["id"]] = texte                  # on garde la saisie si une erreur survient
            if texte == "":
                continue
            nom = f"{e['nom']} {e['prenom']}"
            try:
                valeur = float(texte.replace(",", "."))
            except ValueError:
                erreurs.append(f"{nom} : « {texte} » n'est pas un nombre.")
                continue
            if not math.isfinite(valeur) or not 0 <= valeur <= 20:
                erreurs.append(f"{nom} : la note doit être comprise entre 0 et 20.")
            elif abs(valeur * 100 - round(valeur * 100)) > 1e-6:
                erreurs.append(f"{nom} : deux décimales au maximum.")
            else:
                nouvelles[e["id"]] = valeur
        if erreurs:                                     # rien n'est enregistré si une note est fausse
            for e in erreurs:
                flash(e, "erreur")
            return render_template("saisie.html", classe=classe, matiere=matiere, seq=seq,
                                   eleves=eleves, affichees=affichees, enregistrees=enregistrees), 400

        ajoutees = corrigees = 0
        for eleve_id, valeur in nouvelles.items():
            if eleve_id not in enregistrees:
                ajoutees += 1
            elif enregistrees[eleve_id] != valeur:
                corrigees += 1
            else:
                continue                                # note inchangée
            # Insère la note ; si elle existe déjà (UNIQUE), la met à jour : c'est la correction.
            db.execute(
                "INSERT INTO notes (eleve_id, matiere_id, sequence, valeur, enseignant_id) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (eleve_id, matiere_id, sequence) DO UPDATE SET "
                "valeur = excluded.valeur, enseignant_id = excluded.enseignant_id, "
                "modifie_le = CURRENT_TIMESTAMP",
                (eleve_id, matiere_id, seq, valeur, session["enseignant_id"]))
        db.commit()
        if ajoutees or corrigees:
            flash(f"Enregistré : {ajoutees} note(s) ajoutée(s), {corrigees} note(s) corrigée(s).", "succes")
        else:
            flash("Aucune modification à enregistrer.", "succes")
        return redirect(url_for("saisie", classe_id=classe_id, matiere_id=matiere_id, seq=seq))

    return render_template("saisie.html", classe=classe, matiere=matiere, seq=seq,
                           eleves=eleves, affichees=affichees, enregistrees=enregistrees)


@app.route("/enseignant/classe/<int:classe_id>")
@connexion_requise
def liste_classe(classe_id):
    db = get_db()
    if not peut_voir_classe(db, classe_id):
        abort(403)
    a = analyser_classe(db, classe_id)
    seq = lire_sequence(a["derniere_sequence"])
    return render_template("liste_classe.html", classe=a["classe"], seq=seq,
                           r=resume_classe(a, seq))


@app.route("/admin/statistiques")
@admin_requis
def statistiques():
    db = get_db()
    defaut = max(analyser_classe(db, c["id"])["derniere_sequence"]
                 for c in db.execute("SELECT id FROM classes"))
    seq = lire_sequence(defaut)
    return render_template("statistiques.html", seq=seq, stats=calculer_statistiques(db, seq),
                           tranches=calculs.TRANCHES)


# ---------- API JSON (utilisée par fetch, voir static/js/script.js) ----------
def arrondi_json(valeur):
    return calculs.arrondir(valeur)                     # None devient null en JSON


@app.route("/api/classe/<int:classe_id>/moyennes")
def api_moyennes_classe(classe_id):
    """Moyennes, rangs et chiffres clés d'une classe pour une séquence (?seq=)."""
    if "enseignant_id" not in session:
        abort(401)
    db = get_db()
    if not peut_voir_classe(db, classe_id):
        abort(403)
    a = analyser_classe(db, classe_id)
    seq = lire_sequence(a["derniere_sequence"])
    r = resume_classe(a, seq)
    return jsonify({
        "classe": a["classe"]["nom"], "sequence": seq, "effectif": r["effectif"],
        "moyenne_classe": arrondi_json(r["moyenne"]),
        "taux_reussite": None if r["taux"] is None else round(r["taux"], 1),
        "tranches": {nom: sum(1 for l in r["lignes"] if calculs.tranche(l["moyenne"]) == nom)
                     for nom in calculs.TRANCHES},
        "eleves": [{"id": l["id"], "matricule": l["matricule"], "nom": l["nom"],
                    "prenom": l["prenom"], "moyenne": arrondi_json(l["moyenne"]),
                    "rang": l["rang"]} for l in r["lignes"]],
    })


@app.route("/api/eleve/<int:eleve_id>/evolution")
def api_evolution(eleve_id):
    """Moyenne de l'élève et de sa classe, séquence par séquence (pour le graphique)."""
    if "eleve_id" not in session and "enseignant_id" not in session:
        abort(401)
    db = get_db()
    eleve = db.execute("SELECT id, nom, prenom, classe_id FROM eleves WHERE id = ?",
                       (eleve_id,)).fetchone()
    if eleve is None:
        abort(404)
    # Un élève ne peut demander que ses propres résultats.
    if "eleve_id" in session and session["eleve_id"] != eleve_id:
        abort(403)
    if "enseignant_id" in session and not peut_voir_classe(db, eleve["classe_id"]):
        abort(403)
    h = construire_historique(db, eleve)
    return jsonify({
        "eleve": f"{eleve['prenom']} {eleve['nom']}",
        "sequences": [f"Séq {l['sequence']}" for l in h["lignes"]],
        "moyennes": [arrondi_json(l["moyenne"]) for l in h["lignes"]],
        "moyennes_classe": [arrondi_json(l["moyenne_classe"]) for l in h["lignes"]],
    })


@app.route("/api/statistiques")
def api_statistiques():
    """Statistiques de toutes les classes pour une séquence (?seq=), réservées au proviseur."""
    if "enseignant_id" not in session:
        abort(401)
    if session.get("role") != "admin":
        abort(403)
    db = get_db()
    defaut = max(analyser_classe(db, c["id"])["derniere_sequence"]
                 for c in db.execute("SELECT id FROM classes"))
    seq = lire_sequence(defaut)
    return jsonify({"sequence": seq, "tranches": calculs.TRANCHES,
                    "classes": calculer_statistiques(db, seq)})


# ---------- Pages d'erreur ----------
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
def page_erreur(erreur):
    """JSON pour l'API, page personnalisée pour le reste."""
    if request.path.startswith("/api/"):
        return jsonify({"erreur": erreur.name}), erreur.code
    return render_template("erreur.html", code=erreur.code), erreur.code


if __name__ == "__main__":
    app.run(debug=False)                                # debug=True seulement en développement

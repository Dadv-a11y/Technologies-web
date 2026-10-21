"""calculs.py : les règles de calcul du bulletin (moyennes, rangs, appréciations).

Ce fichier ne contient que des fonctions « pures » : pas de Flask, pas de base
de données. On leur donne des nombres, elles rendent des nombres. C'est ce qui
permet de les tester seules (voir tests_calculs.py).
"""
from decimal import Decimal, ROUND_HALF_UP

NB_SEQUENCES = 6
# Un trimestre regroupe deux séquences.
TRIMESTRES = {1: (1, 2), 2: (3, 4), 3: (5, 6)}
TRANCHES = ["Moins de 8", "8 à 10", "10 à 12", "12 à 14", "14 et plus"]


def arrondir(valeur, decimales=2):
    """Arrondit « à l'école » (14,575 -> 14,58), contrairement à round() de Python."""
    if valeur is None:
        return None
    quantum = Decimal(1).scaleb(-decimales)
    return float(Decimal(str(valeur)).quantize(quantum, rounding=ROUND_HALF_UP))


def moyenne(valeurs):
    """Moyenne simple d'une liste de nombres ; None si la liste est vide."""
    valeurs = list(valeurs)
    if not valeurs:
        return None
    return sum(valeurs) / len(valeurs)


def moyenne_ponderee(couples):
    """Moyenne coefficientée d'une liste de couples (note, coefficient).

    Une matière sans note n'est tout simplement pas dans la liste : son
    coefficient n'entre pas dans le total (comme sur le bulletin papier).
    """
    total_coef = sum(coef for _, coef in couples)
    if total_coef == 0:
        return None
    return sum(note * coef for note, coef in couples) / total_coef


def moyennes_classe(notes, coefs, eleves_ids, sequence):
    """Moyenne coefficientée de chaque élève pour une séquence.

    notes : dictionnaire {(eleve_id, matiere_id, sequence): note}
    coefs : dictionnaire {matiere_id: coefficient}
    Renvoie {eleve_id: moyenne ou None si l'élève n'a aucune note}.
    """
    resultat = {}
    for eleve_id in eleves_ids:
        couples = [
            (notes[(eleve_id, matiere_id, sequence)], coef)
            for matiere_id, coef in coefs.items()
            if (eleve_id, matiere_id, sequence) in notes
        ]
        resultat[eleve_id] = moyenne_ponderee(couples)
    return resultat


def trimestre_de(sequence):
    """Séquences 1-2 -> trimestre 1, 3-4 -> 2, 5-6 -> 3."""
    return (sequence + 1) // 2


def moyenne_trimestre(moyennes_seq, trimestre):
    """Moyenne des séquences connues du trimestre. moyennes_seq = {sequence: moyenne}."""
    debut, fin = TRIMESTRES[trimestre]
    connues = [moyennes_seq[s] for s in (debut, fin) if moyennes_seq.get(s) is not None]
    return moyenne(connues)


def moyenne_annuelle(moyennes_seq):
    """Moyenne des moyennes trimestrielles disponibles."""
    trimestriels = [moyenne_trimestre(moyennes_seq, t) for t in TRIMESTRES]
    return moyenne(t for t in trimestriels if t is not None)


def classer(valeurs):
    """Rang de chaque élément d'un dictionnaire {id: valeur}, ex æquo gérés.

    Deux valeurs égales (après arrondi à 2 décimales, comme sur le bulletin)
    ont le même rang et le suivant « saute » : 1, 2, 2, 4. Les valeurs None
    (pas de note) ne sont pas classées.
    """
    arrondies = {cle: arrondir(v) for cle, v in valeurs.items() if v is not None}
    rangs = {}
    for cle, v in arrondies.items():
        rangs[cle] = 1 + sum(1 for autre in arrondies.values() if autre > v)
    return rangs


def appreciation(note):
    """Appréciation d'une note ou d'une moyenne sur 20."""
    if note is None:
        return ""
    note = arrondir(note)
    if note >= 18:
        return "Excellent"
    if note >= 16:
        return "Très bien"
    if note >= 14:
        return "Bien"
    if note >= 12:
        return "Assez bien"
    if note >= 10:
        return "Passable"
    if note >= 8:
        return "Insuffisant"
    return "Médiocre"


def decision_conseil(moyenne_generale):
    """Mention du conseil de classe selon la moyenne (TH = Tableau d'honneur)."""
    if moyenne_generale is None:
        return ""
    m = arrondir(moyenne_generale)
    if m >= 16:
        return "Travail Très bien + Félicitations + TH"
    if m >= 14:
        return "Travail Bien + Encouragements + TH"
    if m >= 12:
        return "Travail Assez bien + Encouragements"
    if m >= 10:
        return "Travail Passable"
    if m >= 8:
        return "Travail Insuffisant + Avertissement"
    return "Travail Médiocre + Blâme"


def a_reussi(moyenne_generale):
    """Vrai si la moyenne affichée (arrondie) est d'au moins 10."""
    return moyenne_generale is not None and arrondir(moyenne_generale) >= 10


def tranche(moyenne_generale):
    """Nom de la tranche de moyenne (voir TRANCHES), None s'il n'y a pas de moyenne."""
    if moyenne_generale is None:
        return None
    m = arrondir(moyenne_generale)
    if m < 8:
        return TRANCHES[0]
    if m < 10:
        return TRANCHES[1]
    if m < 12:
        return TRANCHES[2]
    if m < 14:
        return TRANCHES[3]
    return TRANCHES[4]

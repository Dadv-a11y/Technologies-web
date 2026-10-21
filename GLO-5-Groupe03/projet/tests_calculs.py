"""tests_calculs.py : vérifie les règles de calcul. Lancement : python tests_calculs.py"""
import calculs


def test_moyenne_du_bulletin_reel():
    # Séquence 1 d'un vrai bulletin de Makepe : 415,5 points pour 28 de coefficient.
    # L'Expression orale n'a pas de note : son coefficient n'est pas compté.
    couples = [
        (17, 4), (12, 2), (19, 2),                      # Sciences et Technologies : 130
        (11.5, 2), (14, 2), (20, 2), (15.5, 1), (13, 2),  # Langues (sans Expression orale)
        (11, 2), (15, 2), (20, 1),                      # Développement personnel : 72
        (13, 4), (14.5, 2),                             # Sciences Humaines : 81
    ]
    assert sum(coef for _, coef in couples) == 28
    assert sum(n * c for n, c in couples) == 415.5
    assert calculs.arrondir(calculs.moyenne_ponderee(couples)) == 14.84


def test_matiere_sans_note_ignoree():
    notes = {(1, 10, 1): 10, (1, 20, 1): 20}        # l'élève n'a pas de note dans la matière 30
    coefs = {10: 1, 20: 3, 30: 5}
    assert calculs.moyennes_classe(notes, coefs, [1], 1)[1] == 17.5
    assert calculs.moyennes_classe(notes, coefs, [2], 1)[2] is None   # élève sans aucune note


def test_rangs_ex_aequo():
    moyennes = {"a": 14.0, "b": 12.5, "c": 12.5, "d": 11.0, "e": None}
    assert calculs.classer(moyennes) == {"a": 1, "b": 2, "c": 2, "d": 4}


def test_rang_apres_arrondi():
    # 12,499 et 12,501 s'affichent tous deux 12,50 : même rang.
    assert calculs.classer({"a": 12.499, "b": 12.501}) == {"a": 1, "b": 1}


def test_arrondi_a_l_ecole():
    assert calculs.arrondir(14.575) == 14.58        # round(14.575, 2) donnerait 14.57
    assert calculs.arrondir(None) is None


def test_trimestre_et_annee():
    moyennes = {1: 14.0, 2: 16.0, 3: 12.0, 4: None}
    assert calculs.moyenne_trimestre(moyennes, 1) == 15.0
    assert calculs.moyenne_trimestre(moyennes, 2) == 12.0    # séquence 4 pas encore notée
    assert calculs.moyenne_trimestre(moyennes, 3) is None
    assert calculs.moyenne_annuelle(moyennes) == 13.5
    assert calculs.moyenne_annuelle({}) is None


def test_appreciations_et_decisions():
    assert calculs.appreciation(19) == "Excellent"
    assert calculs.appreciation(14) == "Bien"
    assert calculs.appreciation(9.999) == "Passable"          # s'affiche 10,00
    assert calculs.appreciation(3) == "Médiocre"
    assert calculs.decision_conseil(14.84) == "Travail Bien + Encouragements + TH"
    assert calculs.decision_conseil(None) == ""


def test_tranches_et_reussite():
    assert calculs.tranche(7.994) == "Moins de 8"
    assert calculs.tranche(7.996) == "8 à 10"                   # s'affiche 8,00
    assert calculs.tranche(10) == "10 à 12"
    assert calculs.tranche(14) == "14 et plus"
    assert calculs.a_reussi(9.996) and not calculs.a_reussi(9.99)


if __name__ == "__main__":
    for nom, fonction in sorted(globals().items()):
        if nom.startswith("test_"):
            fonction()
            print("OK  ", nom)
    print("Tous les tests passent.")

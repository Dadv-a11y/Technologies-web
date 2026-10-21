# exporter.py : sauvegarde toute la base dans un fichier SQL lisible
import os
import sqlite3

DOSSIER = os.path.dirname(os.path.abspath(__file__))

db = sqlite3.connect(os.path.join(DOSSIER, "projet.db"))
with open(os.path.join(DOSSIER, "export_projet.sql"), "w", encoding="utf-8") as f:
    for ligne in db.iterdump():                       # CREATE TABLE puis tous les INSERT
        f.write(ligne + "\n")
db.close()
print("Export terminé : export_projet.sql")

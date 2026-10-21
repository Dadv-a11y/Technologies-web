-- schema.sql : structure de la base du portail de notes (Lycée de Makepe)
-- Les clés étrangères ne sont vérifiées par SQLite que si on les active
-- à chaque connexion (voir get_db() dans app.py).
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS discipline;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS enseignements;
DROP TABLE IF EXISTS eleves;
DROP TABLE IF EXISTS matieres;
DROP TABLE IF EXISTS groupes_matieres;
DROP TABLE IF EXISTS classes;
DROP TABLE IF EXISTS enseignants;

-- Les enseignants (et le proviseur, de rôle 'admin') se connectent par login.
CREATE TABLE enseignants (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    login     TEXT NOT NULL UNIQUE,
    empreinte TEXT NOT NULL,                       -- mot de passe haché, jamais en clair
    role      TEXT NOT NULL DEFAULT 'enseignant'
              CHECK (role IN ('enseignant', 'admin'))
);

CREATE TABLE classes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                     TEXT NOT NULL UNIQUE,  -- ex. : 5e Bilingue 2
    filiere                 TEXT NOT NULL,
    effectif_max            INTEGER NOT NULL CHECK (effectif_max > 0),
    professeur_principal_id INTEGER REFERENCES enseignants (id)
);

-- Les quatre blocs du bulletin : Sciences et Technologies, Langues et Littératures...
CREATE TABLE groupes_matieres (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nom   TEXT NOT NULL UNIQUE,
    ordre INTEGER NOT NULL                         -- ordre d'affichage sur le bulletin
);

CREATE TABLE matieres (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,
    coefficient INTEGER NOT NULL CHECK (coefficient > 0),
    groupe_id   INTEGER NOT NULL REFERENCES groupes_matieres (id),
    ordre       INTEGER NOT NULL
);

CREATE TABLE eleves (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    matricule      TEXT NOT NULL UNIQUE
                   CHECK (matricule GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    nom            TEXT NOT NULL,
    prenom         TEXT NOT NULL,
    sexe           TEXT NOT NULL CHECK (sexe IN ('M', 'F')),
    date_naissance TEXT NOT NULL,                  -- AAAA-MM-JJ
    lieu_naissance TEXT NOT NULL,
    statut         TEXT NOT NULL DEFAULT 'nouveau' CHECK (statut IN ('ancien', 'nouveau')),
    classe_id      INTEGER NOT NULL REFERENCES classes (id),
    code_empreinte TEXT NOT NULL,                  -- code d'accès haché
    nom_pere       TEXT,
    tel_pere       TEXT,
    nom_mere       TEXT,
    tel_mere       TEXT
);

-- Qui enseigne quelle matière dans quelle classe (un seul enseignant par couple).
CREATE TABLE enseignements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id     INTEGER NOT NULL REFERENCES classes (id),
    matiere_id    INTEGER NOT NULL REFERENCES matieres (id),
    enseignant_id INTEGER NOT NULL REFERENCES enseignants (id),
    UNIQUE (classe_id, matiere_id)
);

-- Une note par élève, par matière et par séquence : la contrainte UNIQUE
-- interdit la double saisie, la correction se fait par mise à jour.
CREATE TABLE notes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id      INTEGER NOT NULL REFERENCES eleves (id),
    matiere_id    INTEGER NOT NULL REFERENCES matieres (id),
    sequence      INTEGER NOT NULL CHECK (sequence BETWEEN 1 AND 6),
    valeur        REAL NOT NULL CHECK (valeur BETWEEN 0 AND 20),
    enseignant_id INTEGER REFERENCES enseignants (id),   -- qui a saisi ou corrigé
    modifie_le    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (eleve_id, matiere_id, sequence)
);

CREATE TABLE discipline (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id            INTEGER NOT NULL REFERENCES eleves (id),
    sequence            INTEGER NOT NULL CHECK (sequence BETWEEN 1 AND 6),
    absences            INTEGER NOT NULL DEFAULT 0 CHECK (absences >= 0),
    absences_justifiees INTEGER NOT NULL DEFAULT 0 CHECK (absences_justifiees >= 0),
    consignes           INTEGER NOT NULL DEFAULT 0 CHECK (consignes >= 0),
    exclusions          INTEGER NOT NULL DEFAULT 0 CHECK (exclusions >= 0),
    CHECK (absences_justifiees <= absences),
    UNIQUE (eleve_id, sequence)
);

CREATE INDEX idx_eleves_classe ON eleves (classe_id);
CREATE INDEX idx_notes_matiere_seq ON notes (matiere_id, sequence);

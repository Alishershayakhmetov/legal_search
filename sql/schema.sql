PRAGMA foreign_keys = ON;

-- Reference dimensions (one row per distinct value)
CREATE TABLE legal_force (
    force_id   INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE db_section (
    section_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE region (
    region_id  INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE form (
    form_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE legal_area (
    area_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

CREATE TABLE body (
    body_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE
);

-- One row per legal act (KazakhLawCorpus laws_metadata.csv)
CREATE TABLE act (
    law_id         TEXT PRIMARY KEY,
    adopted_date   TEXT CHECK (adopted_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    adopted_year   INTEGER,
    published_date TEXT,
    force_id       INTEGER REFERENCES legal_force (force_id),
    region_id      INTEGER REFERENCES region (region_id),
    section_id     INTEGER REFERENCES db_section (section_id),
    is_repealed    INTEGER NOT NULL CHECK (is_repealed IN (0, 1)),
    adilet_url     TEXT NOT NULL
);

-- Titles in each language; a missing or captcha title is simply absent or flagged
CREATE TABLE act_title (
    law_id         TEXT NOT NULL REFERENCES act (law_id),
    lang           TEXT NOT NULL CHECK (lang IN ('ru', 'kk')),
    title          TEXT NOT NULL,
    is_placeholder INTEGER NOT NULL DEFAULT 0 CHECK (is_placeholder IN (0, 1)),
    PRIMARY KEY (law_id, lang)
);

-- Many-to-many: an act can have several forms, regulation areas and adopting bodies
CREATE TABLE act_form (
    law_id  TEXT    NOT NULL REFERENCES act (law_id),
    form_id INTEGER NOT NULL REFERENCES form (form_id),
    PRIMARY KEY (law_id, form_id)
);

CREATE TABLE act_area (
    law_id  TEXT    NOT NULL REFERENCES act (law_id),
    area_id INTEGER NOT NULL REFERENCES legal_area (area_id),
    PRIMARY KEY (law_id, area_id)
);

CREATE TABLE act_body (
    law_id  TEXT    NOT NULL REFERENCES act (law_id),
    body_id INTEGER NOT NULL REFERENCES body (body_id),
    PRIMARY KEY (law_id, body_id)
);

-- Full-text files from the Mendeley corpus; law_id stays NULL when the act is not identified
CREATE TABLE text_file (
    file_id     INTEGER PRIMARY KEY,
    law_id      TEXT REFERENCES act (law_id),
    lang        TEXT NOT NULL CHECK (lang IN ('ru', 'kk')),
    rel_path    TEXT NOT NULL UNIQUE,
    size_bytes  INTEGER NOT NULL,
    match_type  TEXT NOT NULL,
    n_candidates INTEGER NOT NULL,
    match_score REAL NOT NULL
);

CREATE INDEX idx_act_year        ON act (adopted_year);
CREATE INDEX idx_act_region      ON act (region_id);
CREATE INDEX idx_act_title_text  ON act_title (lang, title);
CREATE INDEX idx_act_form_form   ON act_form (form_id);
CREATE INDEX idx_act_area_area   ON act_area (area_id);
CREATE INDEX idx_act_body_body   ON act_body (body_id);
CREATE INDEX idx_text_file_law   ON text_file (law_id, lang);

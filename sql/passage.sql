-- Passage metadata only; the text itself stays in data/processed/chunks_{lang}.parquet.
-- law_id and lang are not repeated here: both follow from file_id (third normal form).
DROP TABLE IF EXISTS passage;

CREATE TABLE passage (
    chunk_id   INTEGER PRIMARY KEY,
    file_id    INTEGER NOT NULL REFERENCES text_file (file_id),
    ord        INTEGER NOT NULL,
    article_no TEXT,
    heading    TEXT,
    section    TEXT,
    n_chars    INTEGER NOT NULL,
    is_table   INTEGER NOT NULL CHECK (is_table IN (0, 1)),
    text_hash  TEXT NOT NULL
);

CREATE INDEX idx_passage_file ON passage (file_id, ord);
CREATE INDEX idx_passage_hash ON passage (text_hash);

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS habit (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 40),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS check_in (
    check_in_date TEXT PRIMARY KEY
        CHECK (check_in_date GLOB '????-??-??'),
    created_at TEXT NOT NULL
);

"""SQLite schema and connection management for engine/version/docset indexes."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .config import DB_PATH, DB_SCHEMA_VERSION, MAX_CONTENT_LENGTH
from .docsets import DocsetSpec
from .models import ApiRecord, GuideRecord


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ===========================================================================
-- API records: classes, methods, properties, modules, Blueprint nodes, ...
-- ===========================================================================
CREATE TABLE IF NOT EXISTS api_records (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL DEFAULT '',
    relative_path     TEXT NOT NULL UNIQUE,
    symbol_name       TEXT NOT NULL DEFAULT '',
    class_name        TEXT NOT NULL DEFAULT '',
    namespace         TEXT NOT NULL DEFAULT '',
    module_name       TEXT NOT NULL DEFAULT '',
    topic_path        TEXT NOT NULL DEFAULT '',
    member_type       TEXT NOT NULL DEFAULT '',
    signature         TEXT NOT NULL DEFAULT '',
    parameters_json   TEXT NOT NULL DEFAULT '',
    returns_text      TEXT NOT NULL DEFAULT '',
    summary           TEXT NOT NULL DEFAULT '',
    remarks           TEXT NOT NULL DEFAULT '',
    header_path       TEXT NOT NULL DEFAULT '',
    include_text      TEXT NOT NULL DEFAULT '',
    source_path       TEXT NOT NULL DEFAULT '',
    inheritance_json  TEXT NOT NULL DEFAULT '',
    inputs_json       TEXT NOT NULL DEFAULT '',
    outputs_json      TEXT NOT NULL DEFAULT '',
    content_text      TEXT NOT NULL DEFAULT '',
    source_html_path  TEXT NOT NULL DEFAULT '',
    last_indexed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_symbol_name ON api_records(symbol_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_api_class_name  ON api_records(class_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_api_title       ON api_records(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_api_namespace   ON api_records(namespace COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_api_module_name ON api_records(module_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_api_member_type ON api_records(member_type);
CREATE INDEX IF NOT EXISTS idx_api_topic_path  ON api_records(topic_path COLLATE NOCASE);

CREATE VIRTUAL TABLE IF NOT EXISTS api_fts USING fts5(
    symbol_name,
    title,
    class_name,
    namespace,
    module_name,
    topic_path,
    signature,
    summary,
    remarks,
    content_text,
    content='api_records',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS api_records_ai AFTER INSERT ON api_records BEGIN
    INSERT INTO api_fts(
        rowid, symbol_name, title, class_name, namespace, module_name,
        topic_path, signature, summary, remarks, content_text
    )
    VALUES (
        new.id, new.symbol_name, new.title, new.class_name, new.namespace, new.module_name,
        new.topic_path, new.signature, new.summary, new.remarks, new.content_text
    );
END;
CREATE TRIGGER IF NOT EXISTS api_records_ad AFTER DELETE ON api_records BEGIN
    INSERT INTO api_fts(
        api_fts, rowid, symbol_name, title, class_name, namespace, module_name,
        topic_path, signature, summary, remarks, content_text
    )
    VALUES (
        'delete', old.id, old.symbol_name, old.title, old.class_name, old.namespace, old.module_name,
        old.topic_path, old.signature, old.summary, old.remarks, old.content_text
    );
END;
CREATE TRIGGER IF NOT EXISTS api_records_au AFTER UPDATE ON api_records BEGIN
    INSERT INTO api_fts(
        api_fts, rowid, symbol_name, title, class_name, namespace, module_name,
        topic_path, signature, summary, remarks, content_text
    )
    VALUES (
        'delete', old.id, old.symbol_name, old.title, old.class_name, old.namespace, old.module_name,
        old.topic_path, old.signature, old.summary, old.remarks, old.content_text
    );
    INSERT INTO api_fts(
        rowid, symbol_name, title, class_name, namespace, module_name,
        topic_path, signature, summary, remarks, content_text
    )
    VALUES (
        new.id, new.symbol_name, new.title, new.class_name, new.namespace, new.module_name,
        new.topic_path, new.signature, new.summary, new.remarks, new.content_text
    );
END;

-- ===========================================================================
-- Guide records: manuals, overviews, quickstarts, conceptual pages
-- ===========================================================================
CREATE TABLE IF NOT EXISTS guide_records (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL DEFAULT '',
    relative_path     TEXT NOT NULL UNIQUE,
    guide_type        TEXT NOT NULL DEFAULT 'general',
    topic_path        TEXT NOT NULL DEFAULT '',
    summary           TEXT NOT NULL DEFAULT '',
    content_text      TEXT NOT NULL DEFAULT '',
    key_topics_json   TEXT NOT NULL DEFAULT '',
    source_html_path  TEXT NOT NULL DEFAULT '',
    last_indexed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_guide_title      ON guide_records(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_guide_type       ON guide_records(guide_type);
CREATE INDEX IF NOT EXISTS idx_guide_topic_path ON guide_records(topic_path COLLATE NOCASE);

CREATE VIRTUAL TABLE IF NOT EXISTS guide_fts USING fts5(
    title,
    topic_path,
    key_topics,
    summary,
    content_text,
    content='guide_records',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS guide_records_ai AFTER INSERT ON guide_records BEGIN
    INSERT INTO guide_fts(rowid, title, topic_path, key_topics, summary, content_text)
    VALUES (new.id, new.title, new.topic_path, new.key_topics_json, new.summary, new.content_text);
END;
CREATE TRIGGER IF NOT EXISTS guide_records_ad AFTER DELETE ON guide_records BEGIN
    INSERT INTO guide_fts(guide_fts, rowid, title, topic_path, key_topics, summary, content_text)
    VALUES ('delete', old.id, old.title, old.topic_path, old.key_topics_json, old.summary, old.content_text);
END;
CREATE TRIGGER IF NOT EXISTS guide_records_au AFTER UPDATE ON guide_records BEGIN
    INSERT INTO guide_fts(guide_fts, rowid, title, topic_path, key_topics, summary, content_text)
    VALUES ('delete', old.id, old.title, old.topic_path, old.key_topics_json, old.summary, old.content_text);
    INSERT INTO guide_fts(rowid, title, topic_path, key_topics, summary, content_text)
    VALUES (new.id, new.title, new.topic_path, new.key_topics_json, new.summary, new.content_text);
END;
"""


def get_connection(db_path: Optional[Path] = None, readonly: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection."""

    path = db_path or DB_PATH
    if readonly and not path.exists():
        raise FileNotFoundError(path)

    if not readonly:
        path.parent.mkdir(parents=True, exist_ok=True)

    uri = f"file:{path}"
    if readonly:
        uri += "?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    if not readonly:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def write_metadata(conn: sqlite3.Connection, metadata: dict[str, str]) -> None:
    conn.executemany(
        """
        INSERT INTO metadata(key, value) VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        metadata.items(),
    )


def read_metadata(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM metadata").fetchall()
    }


def init_db(conn: sqlite3.Connection, docset: DocsetSpec | None = None) -> None:
    conn.executescript(_SCHEMA_SQL)
    metadata = {"schema_version": DB_SCHEMA_VERSION}
    if docset:
        metadata.update(
            {
                "engine": docset.engine,
                "version": docset.version,
                "docset": docset.docset,
                "label": docset.label,
                "docs_root": str(docset.docs_root),
                "parser_kind": docset.parser_kind,
                "description": docset.description,
            }
        )
    write_metadata(conn, metadata)
    conn.commit()


def rebuild_db(conn: sqlite3.Connection, docset: DocsetSpec | None = None) -> None:
    """Drop everything and recreate. Also clears any legacy single-table schema."""

    conn.executescript(
        """
        DROP TRIGGER IF EXISTS api_records_ai;
        DROP TRIGGER IF EXISTS api_records_ad;
        DROP TRIGGER IF EXISTS api_records_au;
        DROP TRIGGER IF EXISTS guide_records_ai;
        DROP TRIGGER IF EXISTS guide_records_ad;
        DROP TRIGGER IF EXISTS guide_records_au;
        DROP TABLE IF EXISTS api_fts;
        DROP TABLE IF EXISTS guide_fts;
        DROP TABLE IF EXISTS api_records;
        DROP TABLE IF EXISTS guide_records;
        DROP TABLE IF EXISTS metadata;
        -- legacy schema cleanup
        DROP TRIGGER IF EXISTS doc_pages_ai;
        DROP TRIGGER IF EXISTS doc_pages_ad;
        DROP TRIGGER IF EXISTS doc_pages_au;
        DROP TABLE IF EXISTS doc_pages_fts;
        DROP TABLE IF EXISTS doc_pages;
        """
    )
    init_db(conn, docset=docset)


def upsert_api_record(conn: sqlite3.Connection, rec: ApiRecord) -> int:
    content_text = rec.content_text[:MAX_CONTENT_LENGTH]
    row = conn.execute(
        "SELECT id FROM api_records WHERE relative_path = ?",
        (rec.relative_path,),
    ).fetchone()

    values = (
        rec.title,
        rec.symbol_name,
        rec.class_name,
        rec.namespace,
        rec.module_name,
        rec.topic_path,
        rec.member_type,
        rec.signature,
        rec.parameters_json,
        rec.returns_text,
        rec.summary,
        rec.remarks,
        rec.header_path,
        rec.include_text,
        rec.source_path,
        rec.inheritance_json,
        rec.inputs_json,
        rec.outputs_json,
        content_text,
        rec.source_html_path,
    )

    if row:
        conn.execute(
            """
            UPDATE api_records SET
                title=?, symbol_name=?, class_name=?, namespace=?, module_name=?,
                topic_path=?, member_type=?, signature=?, parameters_json=?, returns_text=?,
                summary=?, remarks=?, header_path=?, include_text=?, source_path=?,
                inheritance_json=?, inputs_json=?, outputs_json=?, content_text=?,
                source_html_path=?, last_indexed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (*values, row["id"]),
        )
        return row["id"]

    cursor = conn.execute(
        """
        INSERT INTO api_records (
            title, relative_path, symbol_name, class_name, namespace, module_name,
            topic_path, member_type, signature, parameters_json, returns_text,
            summary, remarks, header_path, include_text, source_path,
            inheritance_json, inputs_json, outputs_json, content_text, source_html_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (rec.title, rec.relative_path, *values[1:]),
    )
    return cursor.lastrowid


def upsert_guide_record(conn: sqlite3.Connection, rec: GuideRecord) -> int:
    content_text = rec.content_text[:MAX_CONTENT_LENGTH]
    row = conn.execute(
        "SELECT id FROM guide_records WHERE relative_path = ?",
        (rec.relative_path,),
    ).fetchone()

    if row:
        conn.execute(
            """
            UPDATE guide_records SET
                title=?, guide_type=?, topic_path=?, summary=?, content_text=?,
                key_topics_json=?, source_html_path=?, last_indexed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                rec.title,
                rec.guide_type,
                rec.topic_path,
                rec.summary,
                content_text,
                rec.key_topics_json,
                rec.source_html_path,
                row["id"],
            ),
        )
        return row["id"]

    cursor = conn.execute(
        """
        INSERT INTO guide_records (
            title, relative_path, guide_type, topic_path, summary, content_text,
            key_topics_json, source_html_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rec.title,
            rec.relative_path,
            rec.guide_type,
            rec.topic_path,
            rec.summary,
            content_text,
            rec.key_topics_json,
            rec.source_html_path,
        ),
    )
    return cursor.lastrowid

import sqlite3
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./rag.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def run_migrations():
    """Ensure SQLite table columns and relationships are up-to-date without losing data."""
    try:
        with engine.connect() as conn:
            # 1. Check documents table columns
            res_docs = conn.execute(text("PRAGMA table_info(documents)"))
            doc_cols = [row[1] for row in res_docs.fetchall()]
            if doc_cols:
                if "file_size" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0"))
                    logging.info("Added file_size column to documents table")
                if "error_message" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN error_message TEXT"))
                    logging.info("Added error_message column to documents table")
                if "updated_at" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN updated_at DATETIME"))
                    logging.info("Added updated_at column to documents table")
                if "status" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'uploaded'"))
                    logging.info("Added status column to documents table")
                conn.commit()

            # 2. Check conversations table columns
            res_convs = conn.execute(text("PRAGMA table_info(conversations)"))
            conv_cols = [row[1] for row in res_convs.fetchall()]
            if conv_cols:
                if "title" not in conv_cols:
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN title TEXT DEFAULT 'New Conversation'"))
                    logging.info("Added title column to conversations table")
                if "updated_at" not in conv_cols:
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN updated_at DATETIME"))
                    logging.info("Added updated_at column to conversations table")
                conn.commit()

            # 3. Create messages table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    latency_seconds REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """))
            conn.commit()

    except Exception as e:
        logging.warning(f"Database migration check: {e}")
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "../../db/saas.db"))


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'trial',
                trial_ends_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chatbots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                business_name TEXT NOT NULL,
                business_type TEXT,
                system_prompt TEXT,
                widget_color TEXT DEFAULT '#4F46E5',
                welcome_message TEXT DEFAULT 'Hi! How can I help you today?',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chatbot_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                visitor_message TEXT,
                bot_response TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (chatbot_id) REFERENCES chatbots(id)
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                business_name TEXT,
                business_type TEXT,
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                address TEXT,
                city TEXT,
                source TEXT,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS outreach_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                status TEXT DEFAULT 'draft',
                sent_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS outreach_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                sent_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (campaign_id) REFERENCES outreach_campaigns(id),
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            );
        """)


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

import sqlite3
import os
import json

DB_PATH = "/root/telegram/data.db"

os.makedirs("/root/telegram", exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, chat_type TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
        conn.commit()

init_db()

def add_user(user_id):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

def get_all_users():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT user_id FROM users")]

def add_chat(chat_id, chat_type):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO chats (chat_id, chat_type) VALUES (?, ?)", (chat_id, chat_type))
        conn.commit()

def get_all_chats():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT chat_id FROM chats")]

def get_group_chats():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT chat_id FROM chats WHERE chat_type IN ('group', 'supergroup')")]

def increment_interaction():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM stats WHERE key = 'interactions'")
        row = c.fetchone()
        if row:
            c.execute("UPDATE stats SET value = value + 1 WHERE key = 'interactions'")
        else:
            c.execute("INSERT INTO stats (key, value) VALUES ('interactions', 1)")
        conn.commit()

def get_interaction_count():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM stats WHERE key = 'interactions'")
        row = c.fetchone()
        return row[0] if row else 0

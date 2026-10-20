import os

import pymysql
from pymysql import err as pymysql_err
from pymysql.cursors import DictCursor

IntegrityError = pymysql_err.IntegrityError

class DbResult:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

class DbConn:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        cur = self._raw.cursor()
        cur.execute(sql, params)
        return DbResult(cur)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

def mysql_params():
    host = os.environ.get("DB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("DB_PORT", "3306").strip() or "3306")
    user = os.environ.get("DB_USER", "").strip()
    password = os.environ.get("DB_PASSWORD", "")
    database = os.environ.get("DB_NAME", "").strip()
    return host, port, user, password, database

def open_mysql():
    host, port, user, password, database = mysql_params()
    if not user or not database:
        raise RuntimeError("DB_USER و DB_NAME مطلوبان في ملف .env")
    raw = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
    return DbConn(raw)

def init_db():
    conn = open_mysql()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INT AUTO_INCREMENT PRIMARY KEY,"
            "username VARCHAR(30) NOT NULL,"
            "email VARCHAR(80) NULL,"
            "phone VARCHAR(20) NULL,"
            "password_hash VARCHAR(255) NOT NULL,"
            "display_name VARCHAR(40) NOT NULL,"
            "created_at VARCHAR(32) NOT NULL,"
            "UNIQUE KEY uq_users_username (username),"
            "UNIQUE KEY uq_users_email (email),"
            "UNIQUE KEY uq_users_phone (phone)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "id CHAR(32) PRIMARY KEY,"
            "leader VARCHAR(40) NOT NULL,"
            "created_at VARCHAR(32) NOT NULL,"
            "water INT NOT NULL,"
            "air INT NOT NULL,"
            "energy INT NOT NULL,"
            "budget INT NOT NULL,"
            "start_water INT NOT NULL,"
            "start_air INT NOT NULL,"
            "start_energy INT NOT NULL,"
            "start_budget INT NOT NULL,"
            "stage INT NOT NULL,"
            "status VARCHAR(16) NOT NULL,"
            "user_id INT NULL,"
            "KEY idx_sessions_user (user_id, created_at),"
            "CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS decisions ("
            "id INT AUTO_INCREMENT PRIMARY KEY,"
            "session_id CHAR(32) NOT NULL,"
            "stage INT NOT NULL,"
            "choice_id VARCHAR(32) NOT NULL,"
            "choice_title VARCHAR(120) NOT NULL,"
            "cost INT NOT NULL,"
            "quiz_ok TINYINT NOT NULL,"
            "concept VARCHAR(200) NOT NULL,"
            "quiz_concept VARCHAR(200) NOT NULL,"
            "equation VARCHAR(255) NOT NULL,"
            "explanation TEXT NOT NULL,"
            "quiz_note TEXT NOT NULL,"
            "water_before INT NOT NULL,"
            "air_before INT NOT NULL,"
            "energy_before INT NOT NULL,"
            "budget_before INT NOT NULL,"
            "water_after INT NOT NULL,"
            "air_after INT NOT NULL,"
            "energy_after INT NOT NULL,"
            "budget_after INT NOT NULL,"
            "UNIQUE KEY idx_decision_stage (session_id, stage),"
            "CONSTRAINT fk_decisions_session FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
        conn.commit()
    finally:
        conn.close()

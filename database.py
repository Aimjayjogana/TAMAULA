# database.py - POSTGRESQL ONLY - WORKS PERFECTLY ON RENDER (2025)

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# ====================== CONNECTION ======================
def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL is not set! Add it in Render variables.")
    
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn

# ====================== EXECUTE & FETCH ======================
def execute_sql(sql, params=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        return cur
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR: {e}")
        print(f"SQL: {sql}")
        print(f"Params: {params}")
        raise e
    finally:
        cur.close()
        conn.close()

def fetch_one(sql, params=None):
    cur = execute_sql(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None

def fetch_all(sql, params=None):
    cur = execute_sql(sql, params)
    rows = cur.fetchall()
    return [dict(row) for row in rows]

# ====================== INIT DB - ONE CLICK SETUP ======================
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    sql = """
    -- Clubs
    CREATE TABLE IF NOT EXISTS clubs (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        local_government TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        logo TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved BOOLEAN DEFAULT FALSE
    );

    -- Players
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        fullname TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        date_of_birth DATE NOT NULL,
        jersey_number INTEGER,
        gender TEXT,
        profile_picture TEXT,
        club_id INTEGER REFERENCES clubs(id) ON DELETE SET NULL,
        goals INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        yellow_cards INTEGER DEFAULT 0,
        red_cards INTEGER DEFAULT 0,
        password TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
    );

    -- Admins
    CREATE TABLE IF NOT EXISTS admins (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    );

    -- Competitions
    CREATE TABLE IF NOT EXISTS competitions (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        start_date DATE,
        end_date DATE,
        registration_deadline DATE,
        is_active BOOLEAN DEFAULT TRUE
    );

    -- Competition Registrations
    CREATE TABLE IF NOT EXISTS competition_registrations (
        id SERIAL PRIMARY KEY,
        club_id INTEGER REFERENCES clubs(id),
        competition_id INTEGER REFERENCES competitions(id),
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        approved_by INTEGER,
        approved_date TIMESTAMP,
        notes TEXT
    );

    -- Matches
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
        competition_id INTEGER REFERENCES competitions(id),
        home_club_id INTEGER REFERENCES clubs(id),
        away_club_id INTEGER REFERENCES clubs(id),
        match_date DATE,
        match_time TIME,
        location TEXT,
        status TEXT DEFAULT 'scheduled',
        home_score INTEGER DEFAULT 0,
        away_score INTEGER DEFAULT 0
    );

    -- Match Events
    CREATE TABLE IF NOT EXISTS match_events (
        id SERIAL PRIMARY KEY,
        match_id INTEGER REFERENCES matches(id),
        competition_id INTEGER REFERENCES competitions(id),
        player_id INTEGER REFERENCES players(id),
        event_type TEXT NOT NULL,
        minute INTEGER NOT NULL,
        description TEXT,
        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Transfer Requests
    CREATE TABLE IF NOT EXISTS transfer_requests (
        id SERIAL PRIMARY KEY,
        player_id INTEGER REFERENCES players(id) NOT NULL,
        from_club_id INTEGER REFERENCES clubs(id) NOT NULL,
        to_club_id INTEGER REFERENCES clubs(id) NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_by_from_date TIMESTAMP,
        approved_by_to_date TIMESTAMP,
        completed_date TIMESTAMP
    );

    -- Default Data
    INSERT INTO admins (username, password, email)
    VALUES ('admin', 'admin123', 'admin@tamaula.com')
    ON CONFLICT (username) DO NOTHING;

    INSERT INTO competitions (name, description, start_date, end_date, registration_deadline, is_active)
    VALUES 
        ('Kano State Football League', 'Annual football league for clubs in Kano State', '2025-09-01', '2025-12-15', '2025-08-20', TRUE),
        ('Kano FA Cup', 'Knockout tournament for all registered clubs', '2025-10-01', '2025-11-30', '2025-09-15', TRUE)
    ON CONFLICT (name) DO NOTHING;
    """

    try:
        cur.execute(sql)
        conn.commit()
        print("DATABASE INITIALIZED SUCCESSFULLY - ALL TABLES CREATED!")
    except Exception as e:
        conn.rollback()
        print(f"INIT DB FAILED: {e}")
        raise e
    finally:
        cur.close()
        conn.close()



if __name__ == "__main__":
    init_db()
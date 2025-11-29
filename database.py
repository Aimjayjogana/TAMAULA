import sqlite3
from datetime import datetime
import os
import shutil
import json
import sys

# Database configuration - AUTOMATICALLY SWITCHES BETWEEN SQLITE AND POSTGRESQL
def get_db_config():
    """Detect if we're in production (Railway/Render) or development (local)"""
    if os.environ.get('DATABASE_URL'):
        return 'postgresql'  # Production
    else:
        return 'sqlite'     # Development

def get_db_path():
    """Get database path for SQLite"""
    if os.path.exists('/tmp'):
        return '/tmp/tamaula.db'
    else:
        return 'tamaula.db'

def get_db_connection():
    """Get database connection - automatically switches between SQLite and PostgreSQL"""
    db_type = get_db_config()
    
    if db_type == 'postgresql':
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            db_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            return conn
        except ImportError:
            print("⚠️  psycopg2 not available, falling back to SQLite")
            return get_sqlite_connection()
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            raise e
    else:
        return get_sqlite_connection()

def get_sqlite_connection():
    """Get SQLite connection for local development"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def execute_sql(conn, sql, params=None):
    """Execute SQL query with proper parameter handling for both databases"""
    db_type = get_db_config()
    
    # Convert SQLite-style ? placeholders to PostgreSQL-style %s
    if db_type == 'postgresql' and '?' in sql:
        sql = sql.replace('?', '%s')
    
    cursor = conn.cursor()
    
    try:
        if params is None:
            cursor.execute(sql)
        else:
            if not isinstance(params, (tuple, list)):
                params = (params,)
            cursor.execute(sql, params)
        return cursor
    except Exception as e:
        conn.rollback()
        print(f"❌ SQL Error in execute_sql: {e}")
        print(f"   SQL: {sql}")
        print(f"   Params: {params}")
        raise e

def fetch_one(conn, sql, params=None):
    """Fetch one row"""
    try:
        cursor = execute_sql(conn, sql, params)
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            if get_db_config() == 'postgresql':
                return dict(result)
            else:
                return dict(result)
        return None
    except Exception as e:
        print(f"❌ Error in fetch_one: {e}")
        print(f"   SQL: {sql}")
        print(f"   Params: {params}")
        return None

def fetch_all(conn, sql, params=None):
    """Fetch all rows"""
    try:
        cursor = execute_sql(conn, sql, params)
        results = cursor.fetchall()
        cursor.close()
        
        if results:
            if get_db_config() == 'postgresql':
                return [dict(row) for row in results]
            else:
                return [dict(row) for row in results]
        return []
    except Exception as e:
        print(f"❌ Error in fetch_all: {e}")
        print(f"   SQL: {sql}")
        print(f"   Params: {params}")
        return []

def init_db():
    """Initialize the appropriate database based on environment"""
    db_type = get_db_config()
    print(f"🔄 Initializing {db_type} database...")
    
    if db_type == 'sqlite':
        create_sqlite_database()
    else:
        create_postgresql_database()

def create_sqlite_database():
    """Your existing SQLite creation code"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print("🔄 Creating new SQLite database...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # ALL YOUR EXISTING TABLE CREATION CODE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                local_government TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password TEXT NOT NULL,
                logo TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                date_of_birth DATE NOT NULL,
                jersey_number INTEGER,
                gender TEXT,
                profile_picture TEXT,
                club_id INTEGER,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                yellow_cards INTEGER DEFAULT 0,
                red_cards INTEGER DEFAULT 0,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (club_id) REFERENCES clubs (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO admins (username, password, email)
            VALUES ('admin', 'Tama123', 'admin@tamaula.com')
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                start_date DATE,
                end_date DATE,
                registration_deadline DATE,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER,
                competition_id INTEGER,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                approved_by INTEGER,
                approved_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (club_id) REFERENCES clubs (id),
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (approved_by) REFERENCES admins (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER,
                home_club_id INTEGER,
                away_club_id INTEGER,
                match_date DATE,
                match_time TIME,
                location TEXT,
                status TEXT DEFAULT 'scheduled',
                home_score INTEGER DEFAULT 0,
                away_score INTEGER DEFAULT 0,
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (home_club_id) REFERENCES clubs (id),
                FOREIGN KEY (away_club_id) REFERENCES clubs (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                competition_id INTEGER,
                player_id INTEGER,
                event_type TEXT NOT NULL,
                minute INTEGER NOT NULL,
                description TEXT,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id),
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                from_club_id INTEGER NOT NULL,
                to_club_id INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_by_from_date TIMESTAMP,
                approved_by_to_date TIMESTAMP,
                completed_date TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (from_club_id) REFERENCES clubs (id),
                FOREIGN KEY (to_club_id) REFERENCES clubs (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lineups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER,
                competition_id INTEGER,
                player_id INTEGER,
                position TEXT,
                FOREIGN KEY (club_id) REFERENCES clubs (id),
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (player_id) REFERENCES players (id)
            )
        ''')

                    # Group stage tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER,
                group_name TEXT NOT NULL,
                FOREIGN KEY (competition_id) REFERENCES competitions (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER,
                group_id INTEGER,
                club_id INTEGER,
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (group_id) REFERENCES competition_groups (id),
                FOREIGN KEY (club_id) REFERENCES clubs (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER,
                group_id INTEGER,
                home_club_id INTEGER,
                away_club_id INTEGER,
                match_date DATE,
                match_time TIME,
                location TEXT,
                home_score INTEGER DEFAULT 0,
                away_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'scheduled',
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (group_id) REFERENCES competition_groups (id),
                FOREIGN KEY (home_club_id) REFERENCES clubs (id),
                FOREIGN KEY (away_club_id) REFERENCES clubs (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER,
                group_id INTEGER,
                club_id INTEGER,
                matches_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (group_id) REFERENCES competition_groups (id),
                FOREIGN KEY (club_id) REFERENCES clubs (id)
            )
        ''')

        competitions_exist = cursor.execute('SELECT COUNT(*) FROM competitions').fetchone()[0]
        
        if competitions_exist == 0:
            cursor.execute('''
                INSERT INTO competitions (name, description, start_date, end_date, registration_deadline, is_active)
                VALUES 
                ('Kano State Football League', 'Annual football league for clubs in Kano State', '2024-09-01', '2024-12-15', '2024-08-20', TRUE),
                ('Kano FA Cup', 'Knockout tournament for all registered clubs', '2024-10-01', '2024-11-30', '2024-09-15', TRUE)
            ''')
        
        conn.commit()
        conn.close()
        print("✅ SQLite database created successfully")
    else:
        print("✅ SQLite database already exists")

def create_postgresql_database():
    """Create PostgreSQL tables - converted from your SQLite schema"""
    print("🔄 Initializing PostgreSQL database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Enable UUID extension (if needed)
        try:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        except:
            print("⚠️  UUID extension not available, continuing without it")
        
        # Clubs table (PostgreSQL version)
        cursor.execute('''
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
            )
        ''')
        
        # Players table (PostgreSQL version)
        cursor.execute('''
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
                club_id INTEGER REFERENCES clubs(id),
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                yellow_cards INTEGER DEFAULT 0,
                red_cards INTEGER DEFAULT 0,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Admins table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Competitions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitions (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                start_date DATE,
                end_date DATE,
                registration_deadline DATE,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Competition registrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_registrations (
                id SERIAL PRIMARY KEY,
                club_id INTEGER REFERENCES clubs(id),
                competition_id INTEGER REFERENCES competitions(id),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                approved_by INTEGER REFERENCES admins(id),
                approved_date TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Matches table
        cursor.execute('''
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
            )
        ''')
        
        # Match events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_events (
                id SERIAL PRIMARY KEY,
                match_id INTEGER REFERENCES matches(id),
                competition_id INTEGER REFERENCES competitions(id),
                player_id INTEGER REFERENCES players(id),
                event_type TEXT NOT NULL,
                minute INTEGER NOT NULL,
                description TEXT,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transfer requests table
        cursor.execute('''
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
            )
        ''')
        
        # Lineups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lineups (
                id SERIAL PRIMARY KEY,
                club_id INTEGER REFERENCES clubs(id),
                competition_id INTEGER REFERENCES competitions(id),
                player_id INTEGER REFERENCES players(id),
                position TEXT
            )
        ''')
        
        # Group stage tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_groups (
                id SERIAL PRIMARY KEY,
                competition_id INTEGER REFERENCES competitions(id),
                group_name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_assignments (
                id SERIAL PRIMARY KEY,
                competition_id INTEGER REFERENCES competitions(id),
                group_id INTEGER REFERENCES competition_groups(id),
                club_id INTEGER REFERENCES clubs(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_matches (
                id SERIAL PRIMARY KEY,
                competition_id INTEGER REFERENCES competitions(id),
                group_id INTEGER REFERENCES competition_groups(id),
                home_club_id INTEGER REFERENCES clubs(id),
                away_club_id INTEGER REFERENCES clubs(id),
                match_date DATE,
                match_time TIME,
                location TEXT,
                home_score INTEGER DEFAULT 0,
                away_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'scheduled'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_standings (
                id SERIAL PRIMARY KEY,
                competition_id INTEGER REFERENCES competitions(id),
                group_id INTEGER REFERENCES competition_groups(id),
                club_id INTEGER REFERENCES clubs(id),
                matches_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')

        # Insert default admin user (PostgreSQL version)
        cursor.execute('''
            INSERT INTO admins (username, password, email)
            VALUES ('admin', 'Tama1234?', 'admin@tamaula.com')
            ON CONFLICT (username) DO NOTHING
        ''')
        
        # Check if competitions already exist
        cursor.execute('SELECT COUNT(*) FROM competitions')
        result = cursor.fetchone()
        competitions_exist = result['count'] if result else 0
        
        if competitions_exist == 0:
            cursor.execute('''
                INSERT INTO competitions (name, description, start_date, end_date, registration_deadline, is_active)
                VALUES 
                ('Kano State Football League', 'Annual football league for clubs in Kano State', '2024-09-01', '2024-12-15', '2024-08-20', TRUE),
                ('Kano FA Cup', 'Knockout tournament for all registered clubs', '2024-10-01', '2024-11-30', '2024-09-15', TRUE)
            ''')
        
        conn.commit()
        print("✅ PostgreSQL database initialized successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ PostgreSQL initialization error: {e}")
        raise e
    finally:
        conn.close()

def create_transfer_requests_table():
    """Create transfer_requests table if it doesn't exist"""
    conn = get_db_connection()
    try:
        execute_sql(conn, '''
            CREATE TABLE IF NOT EXISTS transfer_requests (
                id SERIAL PRIMARY KEY,
                player_id INTEGER NOT NULL,
                from_club_id INTEGER NOT NULL,
                to_club_id INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_by_from_date TIMESTAMP,
                approved_by_to_date TIMESTAMP,
                completed_date TIMESTAMP
            )
        ''')
        conn.commit()
        print("✅ transfer_requests table created/verified")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating transfer_requests table: {e}")
    finally:
        conn.close()

def update_transfer_requests_table():
    """Add missing columns to transfer_requests table"""
    conn = get_db_connection()
    try:
        db_type = get_db_config()
        
        if db_type == 'postgresql':
            # Check if columns exist in PostgreSQL
            columns_to_add = [
                ('approved_by_from_date', 'TIMESTAMP'),
                ('approved_by_to_date', 'TIMESTAMP'), 
                ('completed_date', 'TIMESTAMP')
            ]
            
            for column_name, column_type in columns_to_add:
                check_column = '''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transfer_requests' and column_name=%s
                '''
                result = fetch_one(conn, check_column, (column_name,))
                if not result:
                    execute_sql(conn, f'ALTER TABLE transfer_requests ADD COLUMN {column_name} {column_type}')
                    print(f"✅ Added column {column_name} to transfer_requests table")
        else:
            # SQLite - try to add columns
            columns_to_add = [
                'approved_by_from_date TIMESTAMP',
                'approved_by_to_date TIMESTAMP',
                'completed_date TIMESTAMP'
            ]
            
            for column_def in columns_to_add:
                try:
                    execute_sql(conn, f'ALTER TABLE transfer_requests ADD COLUMN {column_def}')
                    print(f"✅ Added column to transfer_requests table")
                except Exception as e:
                    print(f"⚠️ Column may already exist: {e}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating transfer_requests table: {e}")
    finally:
        conn.close()

def migrate_database():
    """Add new columns or tables without losing data"""
    conn = get_db_connection()
    try:
        db_type = get_db_config()
        
        # Add columns if they don't exist
        columns_to_add = [
            ('clubs', 'approved', 'BOOLEAN DEFAULT FALSE'),
            ('matches', 'match_time', 'TIME'),
            ('players', 'status', 'TEXT DEFAULT ''pending''')
        ]
        
        for table, column, definition in columns_to_add:
            if db_type == 'postgresql':
                # Check if column exists in PostgreSQL
                check_sql = '''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name=%s and column_name=%s
                '''
                exists = fetch_one(conn, check_sql, (table, column))
                if not exists:
                    execute_sql(conn, f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                    print(f"✅ Added column {column} to {table} table")
            else:
                # SQLite - try to add (will fail if exists)
                try:
                    execute_sql(conn, f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                    print(f"✅ Added column {column} to {table} table")
                except Exception as e:
                    print(f"⚠️ Column {column} may already exist in {table}: {e}")
        
        conn.commit()
        print("✅ Database migrations applied successfully")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration error: {e}")
    finally:
        conn.close()

def fix_match_events_table():
    """Ensure match_events table exists and has correct structure"""
    conn = get_db_connection()
    try:
        db_type = get_db_config()
        
        if db_type == 'postgresql':
            # For PostgreSQL, check if table exists
            table_check = '''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'match_events'
                );
            '''
            table_exists = fetch_one(conn, table_check)
            if not table_exists or not table_exists['exists']:
                execute_sql(conn, '''
                    CREATE TABLE match_events (
                        id SERIAL PRIMARY KEY,
                        match_id INTEGER NOT NULL REFERENCES matches(id),
                        competition_id INTEGER NOT NULL REFERENCES competitions(id),
                        player_id INTEGER NOT NULL REFERENCES players(id),
                        event_type TEXT NOT NULL,
                        minute INTEGER NOT NULL,
                        description TEXT,
                        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("✅ Created match_events table")
        else:
            # SQLite version
            table_exists = fetch_one(conn, """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='match_events'
            """)
            
            if not table_exists:
                execute_sql(conn, '''
                    CREATE TABLE match_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id INTEGER NOT NULL,
                        competition_id INTEGER NOT NULL,
                        player_id INTEGER NOT NULL,
                        event_type TEXT NOT NULL,
                        minute INTEGER NOT NULL,
                        description TEXT,
                        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (match_id) REFERENCES matches (id),
                        FOREIGN KEY (competition_id) REFERENCES competitions (id),
                        FOREIGN KEY (player_id) REFERENCES players (id)
                    )
                ''')
                print("✅ Created match_events table")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error fixing match_events table: {e}")
    finally:
        conn.close()

def clean_duplicate_competitions():
    """Remove duplicate competitions and fix foreign key references"""
    conn = get_db_connection()
    try:
        # This is complex for PostgreSQL, so we'll skip it for now
        # In production, we should handle this differently
        print("⚠️  Duplicate competition cleaning skipped in production")
        return
        
    except Exception as e:
        print(f"❌ Error cleaning duplicates: {e}")
    finally:
        conn.close()

def create_new_database():
    """Your existing function - now calls the appropriate database creator"""
    db_type = get_db_config()
    if db_type == 'sqlite':
        create_sqlite_database()
    else:
        create_postgresql_database()

# Add this function to help with database debugging
def check_database_connection():
    """Check if database connection is working"""
    try:
        conn = get_db_connection()
        result = fetch_one(conn, "SELECT 1 as test")
        conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialization complete")
import sqlite3
from datetime import datetime
import os
import shutil
import json
import sys

# Database configuration - AUTOMATICALLY SWITCHES BETWEEN SQLITE AND POSTGRESQL
def get_db_config():
    """Detect if we're in production (Railway) or development (local)"""
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
            # Import psycopg2 only when needed (for PostgreSQL)
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            db_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(db_url)
            # For PostgreSQL, we'll handle row factory differently
            return conn
        except ImportError:
            print("⚠️  psycopg2 not available, falling back to SQLite")
            return get_sqlite_connection()
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
    db_type = get_db_config()
    
    cursor = conn.cursor()
    
    try:
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return cursor
    except Exception as e:
        print(f"❌ SQL Error: {e}")
        print(f"   SQL: {sql}")
        print(f"   Params: {params}")
        conn.rollback()
        raise e
    
def fetch_one(conn, sql, params=None):
    """Fetch one row - converts to dictionary"""
    cursor = execute_sql(conn, sql, params)
    result = cursor.fetchone()
    cursor.close()
    
    if result and get_db_config() == 'postgresql':
        # Convert PostgreSQL result to dictionary-like object
        if hasattr(result, '_asdict'):
            return result._asdict()
        else:
            # Create a simple dict from tuple
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
    return result

def fetch_all(conn, sql, params=None):
    """Fetch all rows - converts to list of dictionaries"""
    cursor = execute_sql(conn, sql, params)
    results = cursor.fetchall()
    cursor.close()
    
    if get_db_config() == 'postgresql' and results:
        # Convert PostgreSQL results to list of dictionaries
        converted_results = []
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        for row in results:
            if hasattr(row, '_asdict'):
                converted_results.append(row._asdict())
            else:
                converted_results.append(dict(zip(columns, row)))
        return converted_results
    
    return results

def init_db():
    """Initialize database - works for both SQLite and PostgreSQL"""
    db_type = get_db_config()
    conn = get_db_connection()
    
    try:
        if db_type == 'sqlite':
            create_sqlite_database()
        else:
            create_postgresql_database()
        
        # Run migrations and fixes
        migrate_database()
        fix_match_events_table()
        clean_duplicate_competitions()
        create_transfer_requests_table()
        update_transfer_requests_table()
        
        conn.commit()
        print("✅ Database initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"❌ Database initialization error: {e}")
    finally:
        conn.close()

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
                FOREIGN KEY (club_id) REFERENCES clubs (id)
            )
        ''')
        
        # [KEEP ALL YOUR OTHER TABLE CREATIONS EXACTLY AS IS]
        
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
            VALUES ('admin', 'admin123', 'admin@tamaula.com')
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
        create_new_database()

def create_postgresql_database():
    """Create PostgreSQL tables - converted from your SQLite schema"""
    print("🔄 Initializing PostgreSQL database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Enable UUID extension
        cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        
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
                approved_by INTEGER,
                approved_date TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # [ADD ALL YOUR OTHER TABLES...]
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
        
        # Admins table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Insert default admin user (PostgreSQL version)
        cursor.execute('''
            INSERT INTO admins (username, password, email)
            VALUES ('admin', 'admin123', 'admin@tamaula.com')
            ON CONFLICT (username) DO NOTHING
        ''')
        
        # Check if competitions already exist
        cursor.execute('SELECT COUNT(*) FROM competitions')
        competitions_exist = cursor.fetchone()[0]
        
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

# KEEP ALL YOUR EXISTING FUNCTIONS BUT UPDATE THEM TO USE execute_sql

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
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (from_club_id) REFERENCES clubs (id),
                FOREIGN KEY (to_club_id) REFERENCES clubs (id)
            )
        ''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating transfer_requests table: {e}")
    finally:
        conn.close()

def update_transfer_requests_table():
    """Add missing columns to transfer_requests table"""
    conn = get_db_connection()
    try:
        # For PostgreSQL, we need to check if column exists differently
        db_type = get_db_config()
        
        if db_type == 'postgresql':
            # Check if column exists in PostgreSQL
            check_column = '''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='transfer_requests' and column_name='completed_date'
            '''
            result = fetch_one(conn, check_column)
            if not result:
                execute_sql(conn, 'ALTER TABLE transfer_requests ADD COLUMN completed_date TIMESTAMP')
        else:
            # SQLite - try to add column (will fail if exists)
            try:
                execute_sql(conn, 'ALTER TABLE transfer_requests ADD COLUMN completed_date TIMESTAMP')
            except:
                pass

        # Repeat for other columns...
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
            ('players', 'status', 'TEXT DEFAULT "pending"')
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
            else:
                # SQLite - try to add (will fail if exists)
                try:
                    execute_sql(conn, f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                except:
                    pass
        
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
        duplicates = fetch_all(conn, '''
            SELECT name, COUNT(*) as count, array_agg(id) as ids
            FROM competitions 
            GROUP BY name 
            HAVING COUNT(*) > 1
        ''')
        
        if duplicates:
            for duplicate in duplicates:
                name = duplicate['name']
                all_ids = duplicate['ids']
                keep_id = min(all_ids)
                delete_ids = [id for id in all_ids if id != keep_id]
                
                for delete_id in delete_ids:
                    # Update all references to use the kept ID
                    tables_to_update = [
                        'competition_registrations',
                        'matches', 
                        'match_events',
                        'lineups'
                    ]
                    
                    for table in tables_to_update:
                        execute_sql(conn, f'''
                            UPDATE {table} 
                            SET competition_id = %s 
                            WHERE competition_id = %s
                        ''', (keep_id, delete_id))
                    
                    # Delete duplicate competition
                    execute_sql(conn, 'DELETE FROM competitions WHERE id = %s', (delete_id,))
            
            conn.commit()
            print("✅ Duplicate competitions cleaned")
            
    except Exception as e:
        conn.rollback()
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

# ENHANCED BACKUP SYSTEM WITH CLOUDFLARE R2
def backup_database():
    """Create a backup and store in Cloudflare R2"""
    try:
        data = export_data()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.json"
        
        if get_db_config() == 'postgresql':
            upload_to_r2(json.dumps(data, indent=2), backup_filename)
        
        return {
            'status': 'success',
            'filename': backup_filename,
            'data': data
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def upload_to_r2(data, filename):
    """Upload backup to Cloudflare R2"""
    try:
        import boto3
        s3 = boto3.client('s3',
            endpoint_url=os.getenv('R2_ENDPOINT'),
            aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
            region_name='auto'
        )
        
        s3.put_object(
            Bucket=os.getenv('R2_BACKUP_BUCKET'),
            Key=f"backups/{filename}",
            Body=data.encode('utf-8'),
            ContentType='application/json'
        )
        return True
    except Exception as e:
        print(f"❌ R2 upload failed: {e}")
        return False

def export_data():
    """Export all data to JSON files"""
    conn = get_db_connection()
    data = {}
    
    try:
        # Export clubs
        clubs = fetch_all(conn, 'SELECT * FROM clubs')
        data['clubs'] = clubs
        
        # Export players
        players = fetch_all(conn, 'SELECT * FROM players')
        data['players'] = players
        
        # Export competitions
        competitions = fetch_all(conn, 'SELECT * FROM competitions')
        data['competitions'] = competitions
        
        # Export match_events
        match_events = fetch_all(conn, 'SELECT * FROM match_events')
        data['match_events'] = match_events
        
        # Export matches
        matches = fetch_all(conn, 'SELECT * FROM matches')
        data['matches'] = matches
        
        print("✅ Data exported successfully")
        return data
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return {}
    finally:
        conn.close()

def restore_latest_backup():
    """Restore from the latest backup"""
    return False

def import_data():
    """Import data from JSON backup"""
    return False

if __name__ == "__main__":
    init_db()
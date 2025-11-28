from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from database import get_db_connection, init_db
from database import execute_sql, fetch_one, fetch_all
from datetime import datetime, date
import atexit
import os
from werkzeug.utils import secure_filename
from functools import wraps
from storage import storage
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '5224078f7aa87433a624ffb37bf352fa09f4894ea6348a6b62f9db9c0215a30c')
app.config['UPLOAD_FOLDER'] = 'static/images/uploads'

storage.init_app(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Kano State Local Governments and Clubs data
LOCAL_GOVERNMENTS = {
    "Ajingi": ["Ajingi FC", "Dab FC", "Garu FC"],
    "Albasu": ["Albasu United", "Albasu Warriors", "Gagume FC"],
    "Bagwai": ["Bagwai Stars", "Bagwai United", "Rogo FC"],
    "Bebeji": ["Bebeji FC", "Bebeji United", "Zugachi FC"],
    "Bichi": ["Bichi FC", "Bichi United", "Danbatta FC"],
    "Bunkure": ["Bunkure FC", "Bunkure Warriors", "Gafan FC"],
    "Dala": ["Dala FC", "Dala United", "Kwalli FC"],
    "Dambatta": ["Dambatta FC", "Dambatta United", "Shanono FC"],
    "Dawakin Kudu": ["Dawakin Kudu FC", "Dawakin Kudu United", "Gwarzo FC"],
    "Dawakin Tofa": ["Dawakin Tofa FC", "Dawakin Tofa United", "Tofa FC"],
    "Doguwa": ["Doguwa FC", "Doguwa United", "Rano FC"],
    "Fagge": ["Fagge FC", "Fagge United", "Yankatsari FC"],
    "Gabasawa": ["Gabasawa FC", "Gabasawa United", "Geza FC"],
    "Garko": ["Garko FC", "Garko United", "Gaya FC"],
    "Garun Mallam": ["Garun Mallam FC", "Garun Mallam United", "Kura FC"],
    "Gaya": ["Gaya FC", "Gaya United", "Wudil FC"],
    "Gezawa": ["Gezawa FC", "Gezawa United", "Ungogo FC"],
    "Gwale": ["Gwale FC", "Gwale United", "Dawaki FC"],
    "Gwarzo": ["Gwarzo FC", "Gwarzo United", "Karaye FC"],
    "Kabo": ["Kabo FC", "Kabo United", "Rimin Gado FC"],
    "Kano Municipal": ["Kano Municipal FC", "Kano Municipal United", "Sharada FC"],
    "Karaye": ["Karaye FC", "Karaye United", "Kiru FC"],
    "Kibiya": ["Kibiya FC", "Kibiya United", "Bunkure FC"],
    "Kiru": ["Kiru FC", "Kiru United", "Kabo FC"],
    "Kumbotso": ["Kumbotso FC", "Kumbotso United", "Challawa FC"],
    "Kunchi": ["Kunchi FC", "Kunchi United", "Tsanyawa FC"],
    "Kura": ["Kura FC", "Kura United", "Garun Mallam FC"],
    "Madobi": ["Madobi FC", "Madobi United", "Gezawa FC"],
    "Makoda": ["Makoda FC", "Makoda United", "Bagwai FC"],
    "Minjibir": ["Minjibir FC", "Minjibir United", "Dawakin Tofa FC"],
    "Nasarawa": ["Nasarawa FC", "Nasarawa United", "Gwale FC"],
    "Rano": ["Rano FC", "Rano United", "Doguwa FC"],
    "Rimin Gado": ["Rimin Gado FC", "Rimin Gado United", "Tofa FC"],
    "Rogo": ["Rogo FC", "Rogo United", "Madobi FC"],
    "Shanono": ["Shanono FC", "Shanono United", "Bichi FC"],
    "Sumaila": ["Sumaila FC", "Sumaila United", "Takai FC"],
    "Takai": ["Takai FC", "Takai United", "Albasu FC"],
    "Tarauni": ["Tarauni FC", "Tarauni United", "Nasarawa FC"],
    "Tofa": ["Tofa FC", "Tofa United", "Rimin Gado FC"],
    "Tsanyawa": ["Tsanyawa FC", "Tsanyawa United", "Kunchi FC"],
    "Tudun Wada": ["Tudun Wada FC", "Tudun Wada United", "Sumaila FC"],
    "Ungogo": ["Ungogo FC", "Ungogo United", "Gabasawa FC"],
    "Warawa": ["Warawa FC", "Warawa United", "Dawakin Kudu FC"],
    "Wudil": ["Wudil FC", "Wudil United", "Garko FC"]
}

# Helper function to get parameter placeholder based on database type
def get_param_placeholder():
    from database import get_db_config
    return '%s' if get_db_config() == 'postgresql' else '?'

def check_admin_session():
    """Check if user is logged in as admin"""
    return 'admin_id' in session and session.get('user_type') == 'admin'

@app.route('/init-db')
def initialize():
    try:
        init_db()
        return "<h1>Tamaula is ready! All tables created.</h1>"
    except Exception as e:
        return f"<h1>Database initialization failed: {str(e)}</h1>", 500
    
@app.route('/')
def index():
    return render_template('index.html')

# Serve player profile pictures
@app.route('/static/images/uploads/<path:filename>')
def serve_player_profiles(filename):
    return send_from_directory('static/images/uploads/', filename)

# This serves all other uploads
@app.route('/static/images/uploads/<path:filename>')
def serve_uploaded_files(filename):
    return send_from_directory('static/images/uploads', filename)

@app.route('/fix_upload_paths')
def fix_upload_paths():
    """Fix player image paths to use consistent structure"""
    conn = get_db_connection()
    try:
        # Update player profile picture paths
        players = fetch_all(conn, "SELECT id, profile_picture FROM players WHERE profile_picture IS NOT NULL")
        
        for player in players:
            old_path = player['profile_picture']
            if old_path and 'uploads/player-profiles' in old_path:
                # Extract filename and create new path
                filename = old_path.split('/')[-1]
                new_path = f"/static/images/uploads/player-profiles/{filename}"
                execute_sql(conn, "UPDATE players SET profile_picture = ? WHERE id = ?", (new_path, player['id']))
        
        conn.commit()
        flash('Upload paths fixed successfully', 'success')
        return redirect(url_for('players'))
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('players'))
    finally:
        conn.close()

@app.route('/fix_player_images')
def fix_player_images():
    """Reset all player images to use default"""
    conn = get_db_connection()
    try:
        execute_sql(conn, "UPDATE players SET profile_picture = NULL")
        conn.commit()
        flash('Player images fixed. Please re-upload profile pictures.', 'success')
        return redirect(url_for('players'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('players'))
    finally:
        conn.close()

@app.route('/register_player', methods=['GET', 'POST'])
def register_player():
    if request.method == 'POST':
        try:
            # Get form data
            fullname = request.form.get('fullname', '').strip()
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            date_of_birth = request.form.get('date_of_birth', '').strip()
            jersey_number = request.form.get('jersey_number', '').strip()
            gender = request.form.get('gender', '').strip()
            local_government = request.form.get('local_government', '').strip()
            club_name = request.form.get('club', '').strip()
            password = request.form.get('password', '').strip()

            # Server-side validation for required fields
            required_fields = {
                'fullname': fullname,
                'username': username,
                'email': email,
                'date_of_birth': date_of_birth,
                'local_government': local_government,
                'club': club_name,
                'password': password
            }
            
            # Check for empty required fields
            missing_fields = []
            for field_name, field_value in required_fields.items():
                if not field_value:
                    missing_fields.append(field_name.replace('_', ' ').title())
            
            if missing_fields:
                flash(f'Please fill in all required fields: {", ".join(missing_fields)}', 'error')
                return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)

            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('Please enter a valid email address.', 'error')
                return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)

            # Validate date format and age (optional but recommended)
            from datetime import datetime, date
            try:
                birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < 5:  # Minimum age check
                    flash('You must be at least 5 years old to register.', 'error')
                    return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)
            except ValueError:
                flash('Please enter a valid date of birth.', 'error')
                return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)

            # Validate password length
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)

            conn = get_db_connection()
            try:
                # Check if club exists
                club = fetch_one(conn, 'SELECT id FROM clubs WHERE name = ? AND local_government = ?', 
                                (club_name, local_government))
                
                if not club:
                    flash('Selected club is not registered. Please ask your club to register first.', 'error')
                    return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)
                
                # Check if username or email already exists
                existing_user = fetch_one(conn,
                    'SELECT id FROM players WHERE username = ? OR email = ?', 
                    (username, email)
                )
                
                if existing_user:
                    flash('Username or email already exists.', 'error')
                    return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)
                
                # Handle profile picture upload
                profile_picture = None
                if 'profile_picture' in request.files:
                    file = request.files['profile_picture']
                    if file and file.filename != '':
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                            filename = secure_filename(f"{username}_{file.filename}")
                            # Upload to storage
                            file_url = storage.upload_file(file, filename, 'player-profiles')
                            if file_url:
                                profile_picture = file_url
                
                # Convert empty optional fields to None for database
                phone = phone if phone else None
                jersey_number = int(jersey_number) if jersey_number else None
                gender = gender if gender else None
                
                # Insert player into database with 'pending' status (club approval needed)
                execute_sql(conn, '''
                    INSERT INTO players (fullname, username, email, phone, date_of_birth, 
                    jersey_number, gender, profile_picture, club_id, password, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fullname, username, email, phone, date_of_birth, jersey_number, 
                      gender, profile_picture, club['id'], password, 'pending'))
                
                conn.commit()
                flash('Registration submitted successfully! Please wait for club approval.', 'success')
                return redirect(url_for('login'))
            finally:
                conn.close()
        
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)
    
    return render_template('register_player.html', local_governments=LOCAL_GOVERNMENTS)

@app.route('/get_clubs/<local_government>', methods=['GET'])
def get_clubs(local_government):
    normalized_lg = local_government.strip().lower() 
    conn = get_db_connection()
    try:
        clubs_data = fetch_all(conn,
            'SELECT id, name FROM clubs WHERE LOWER(local_government) = ?',
            (normalized_lg,)
        )

        club_names = [club['name'] for club in clubs_data]
        return jsonify(club_names)

    except Exception as e:
        print(f"Error in get_clubs: {e}")
        return jsonify([])
    finally:
        conn.close()

@app.route('/club/edit_details', methods=['GET', 'POST'])
def edit_club_details():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club = fetch_one(conn, 'SELECT * FROM clubs WHERE id = ?', (session['user_id'],))
        
        if request.method == 'POST':
            # Update club details
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            local_government = request.form['local_government']
            
            execute_sql(conn, '''
                UPDATE clubs 
                SET name = ?, email = ?, phone = ?, local_government = ?
                WHERE id = ?
            ''', (name, email, phone, local_government, session['user_id']))
            
            conn.commit()
            flash('Club details updated successfully!', 'success')
            return redirect(url_for('club_dashboard'))
        
        return render_template('edit_club_details.html', club=club, local_governments=LOCAL_GOVERNMENTS)
    except Exception as e:
        flash(f'Error updating club details: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/transfers')
def public_transfers():
    """Public page showing all transfer activity"""
    conn = get_db_connection()
    try:
        # Get all transfers with basic information
        all_transfers = fetch_all(conn, '''
            SELECT 
                tr.id,
                tr.status,
                tr.request_date,
                tr.reason,
                p.fullname as player_name, 
                p.jersey_number,
                from_club.name as from_club_name, 
                to_club.name as to_club_name,
                from_club.local_government as from_lg,
                to_club.local_government as to_lg
            FROM transfer_requests tr
            JOIN players p ON tr.player_id = p.id
            JOIN clubs from_club ON tr.from_club_id = from_club.id
            JOIN clubs to_club ON tr.to_club_id = to_club.id
            ORDER BY tr.request_date DESC
        ''')
        
        # Separate completed and pending transfers
        completed_transfers = [t for t in all_transfers if t['status'] == 'completed']
        pending_transfers = [t for t in all_transfers if t['status'] in ['pending', 'approved_by_from']]
        
        return render_template('public_transfers.html',
                             completed_transfers=completed_transfers,
                             pending_transfers=pending_transfers)
    except Exception as e:
        flash('Error loading transfer data', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/club/transfer_requests')
def club_transfer_requests():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        
        # Get outgoing transfers (players leaving)
        outgoing = fetch_all(conn, '''
            SELECT tr.*, p.fullname, to_club.name as to_club_name
            FROM transfer_requests tr
            JOIN players p ON tr.player_id = p.id
            JOIN clubs to_club ON tr.to_club_id = to_club.id
            WHERE tr.from_club_id = ? AND tr.status IN ('pending', 'approved_by_to')
        ''', (club_id,))
        
        # Get incoming transfers (players joining)
        incoming = fetch_all(conn, '''
            SELECT tr.*, p.fullname, from_club.name as from_club_name
            FROM transfer_requests tr
            JOIN players p ON tr.player_id = p.id
            JOIN clubs from_club ON tr.from_club_id = from_club.id
            WHERE tr.to_club_id = ? AND tr.status IN ('pending', 'approved_by_from')
        ''', (club_id,))
        
        return render_template('club_transfer_requests.html',
                             outgoing=outgoing,
                             incoming=incoming)
    except Exception as e:
        flash(f'Error loading transfer requests: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/club/approve_transfer/<int:transfer_id>')
def club_approve_transfer(transfer_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        transfer = fetch_one(conn, 'SELECT * FROM transfer_requests WHERE id = ?', (transfer_id,))
        
        if not transfer:
            flash('Transfer request not found', 'error')
            return redirect(url_for('club_transfer_requests'))
        
        if transfer['from_club_id'] == club_id:
            if transfer['status'] == 'pending':
                execute_sql(conn, '''
                    UPDATE transfer_requests 
                    SET status = 'approved_by_from', approved_by_from_date = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (transfer_id,))
                flash('Transfer approved. Waiting for destination club approval.', 'success')
            else:
                flash('Transfer already processed', 'warning')
                
        elif transfer['to_club_id'] == club_id:
            if transfer['status'] == 'approved_by_from':
                # Complete the transfer
                execute_sql(conn, 'UPDATE players SET club_id = ? WHERE id = ?', 
                           (transfer['to_club_id'], transfer['player_id']))
                execute_sql(conn, '''
                    UPDATE transfer_requests 
                    SET status = 'completed', 
                        approved_by_to_date = CURRENT_TIMESTAMP,
                        completed_date = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (transfer_id,))
                flash('Transfer completed! Player has been added to your club.', 'success')
            elif transfer['status'] == 'pending':
                flash('Source club must approve first', 'warning')
            else:
                flash('Transfer already processed', 'warning')
        else:
            flash('Not authorized to approve this transfer', 'error')
        
        conn.commit()
        return redirect(url_for('club_transfer_requests'))
    
    except Exception as e:
        conn.rollback()
        flash(f'Error approving transfer: {str(e)}', 'error')
        return redirect(url_for('club_transfer_requests'))
    finally:
        conn.close()

@app.route('/club/reject_transfer/<int:transfer_id>')
def club_reject_transfer(transfer_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        transfer = fetch_one(conn, 'SELECT * FROM transfer_requests WHERE id = ?', (transfer_id,))
        
        if transfer and (transfer['from_club_id'] == club_id or transfer['to_club_id'] == club_id):
            execute_sql(conn, 'UPDATE transfer_requests SET status = "rejected" WHERE id = ?', (transfer_id,))
            conn.commit()
            flash('Transfer rejected', 'success')
        else:
            flash('Not authorized', 'error')
        
        return redirect(url_for('club_transfer_requests'))
    except Exception as e:
        flash(f'Error rejecting transfer: {str(e)}', 'error')
        return redirect(url_for('club_transfer_requests'))
    finally:
        conn.close()

@app.route('/player/edit_profile', methods=['GET', 'POST'])
def edit_player_profile():
    if 'user_id' not in session or session['user_type'] != 'player':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        player = fetch_one(conn, '''
            SELECT p.*, c.name as club_name 
            FROM players p 
            LEFT JOIN clubs c ON p.club_id = c.id 
            WHERE p.id = ?
        ''', (session['user_id'],))

        # Get pending transfers for this player
        pending_transfers = fetch_all(conn, '''
            SELECT tr.*, from_club.name as from_club_name, to_club.name as to_club_name
            FROM transfer_requests tr
            JOIN clubs from_club ON tr.from_club_id = from_club.id
            JOIN clubs to_club ON tr.to_club_id = to_club.id
            WHERE tr.player_id = ? AND tr.status IN ('pending', 'approved_by_from')
        ''', (session['user_id'],))
        
        if request.method == 'POST':
            # Get form data
            fullname = request.form['fullname']
            username = request.form['username']
            email = request.form['email']
            phone = request.form['phone']
            date_of_birth = request.form['date_of_birth']
            jersey_number = request.form['jersey_number']
            gender = request.form['gender']
            club_id = request.form.get('club_id')
            current_password = request.form['current_password']
            new_password = request.form.get('new_password')
            transfer_reason = request.form.get('transfer_reason', '')
            
            # Verify current password
            if player['password'] != current_password:
                flash('Current password is incorrect', 'error')
                return redirect(url_for('edit_player_profile'))
            
            # Check if username or email already exists
            existing_user = fetch_one(conn,
                'SELECT id FROM players WHERE (username = ? OR email = ?) AND id != ?',
                (username, email, session['user_id'])
            )
            
            if existing_user:
                flash('Username or email already exists', 'error')
                return redirect(url_for('edit_player_profile'))
            
            # Handle profile picture upload - FIXED: Initialize variable first
            profile_picture = None
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '':
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                    if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        filename = secure_filename(f"{username}_{file.filename}")
                        file_url = storage.upload_file(file, filename, 'player-profiles')
                        if file_url:
                            profile_picture = file_url
            
            # Handle club transfer with approval system
            transfer_occurred = False
            if club_id and int(club_id) != player['club_id']:
                # Create transfer request
                execute_sql(conn, '''
                    INSERT INTO transfer_requests 
                    (player_id, from_club_id, to_club_id, reason, status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (session['user_id'], player['club_id'], club_id, transfer_reason))
                transfer_occurred = True
            
            # Update player information
            update_query = '''
                UPDATE players 
                SET fullname = ?, username = ?, email = ?, phone = ?, 
                    date_of_birth = ?, jersey_number = ?, gender = ?,
                    profile_picture = COALESCE(?, profile_picture)
            '''
            update_params = [fullname, username, email, phone, date_of_birth, 
                           jersey_number, gender, profile_picture]
            
            # Only update club if no transfer occurred
            if not transfer_occurred and club_id:
                update_query += ', club_id = ?'
                update_params.append(club_id)
            else:
                update_query += ', club_id = club_id'
            
            # Add password update if new password provided
            if new_password:
                update_query += ', password = ?'
                update_params.append(new_password)
            
            update_query += ' WHERE id = ?'
            update_params.append(session['user_id'])
            
            execute_sql(conn, update_query, update_params)
            conn.commit()
            
            if transfer_occurred:
                flash('Transfer request submitted! Waiting for approval from both clubs.', 'warning')
            else:
                flash('Profile updated successfully!', 'success')
            
            return redirect(url_for('dashboard'))
        
        # GET request
        clubs = fetch_all(conn, '''
            SELECT id, name, local_government 
            FROM clubs 
            WHERE approved = TRUE 
            ORDER BY name
        ''')
        
        return render_template('edit_player_profile.html', player=player, clubs=clubs)
    
    except Exception as e:
        conn.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
        return redirect(url_for('edit_player_profile'))
    finally:
        conn.close()

@app.route('/delete_account')
def delete_account():
    """Route to handle account deletion"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        if session['user_type'] == 'player':
            execute_sql(conn, 'DELETE FROM players WHERE id = ?', (session['user_id'],))
            flash('Your account has been deleted successfully.', 'success')
        else:
            flash('Club account deletion is not available through this method.', 'error')
        
        conn.commit()
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        conn.rollback()
        flash('Error deleting account. Please contact admin.', 'error')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

@app.route('/club_registration')
def club_registration():
    """Route for club registration"""
    return render_template('register_club.html', local_governments=LOCAL_GOVERNMENTS)

# Add this helper function for login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/club/competition_details/<int:competition_id>')
def competition_details(competition_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        # Get competition details
        competition = fetch_one(conn,
            'SELECT * FROM competitions WHERE id = ?', 
            (competition_id,)
        )
        
        # Get club's registration status for this competition
        registration = fetch_one(conn, '''
            SELECT * FROM competition_registrations 
            WHERE club_id = ? AND competition_id = ?
        ''', (session['user_id'], competition_id))
        
        # Get club's players for this competition lineup
        players = fetch_all(conn, '''
            SELECT p.*, l.position 
            FROM players p 
            LEFT JOIN lineups l ON p.id = l.player_id AND l.competition_id = ?
            WHERE p.club_id = ?
        ''', (competition_id, session['user_id']))
        
        return render_template('competition_details.html', 
                             competition=competition, 
                             registration=registration,
                             players=players)
    except Exception as e:
        flash(f'Error loading competition details: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/club/match/<int:match_id>')
def match_details(match_id):
    if 'user_id' not in session or session.get('user_type') != 'club':
        flash('Please login as club to access this page.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        
        # FIXED: Get match details with club logos
        match = fetch_one(conn, '''
            SELECT m.*, 
                   home.name as home_club_name, 
                   home.logo as home_club_logo,
                   away.name as away_club_name,
                   away.logo as away_club_logo,
                   c.name as competition_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            JOIN competitions c ON m.competition_id = c.id
            WHERE m.id = ? AND (m.home_club_id = ? OR m.away_club_id = ?)
        ''', (match_id, club_id, club_id))
        
        if not match:
            flash('Match not found or access denied.', 'error')
            return redirect(url_for('club_matches'))
        
        # FIXED: Get match events safely
        events = fetch_all(conn, '''
            SELECT me.*, p.fullname as player_name, p.jersey_number,
                   cl.name as club_name
            FROM match_events me
            JOIN players p ON me.player_id = p.id
            JOIN clubs cl ON p.club_id = cl.id
            WHERE me.match_id = ?
            ORDER BY me.minute ASC
        ''', (match_id,)) or []
        
        # FIXED: Get lineups for both teams
        home_lineup = fetch_all(conn, '''
            SELECT p.fullname, p.jersey_number, l.position
            FROM lineups l
            JOIN players p ON l.player_id = p.id
            WHERE l.club_id = ? AND l.competition_id = ?
            ORDER BY 
                CASE l.position
                    WHEN 'Goalkeeper' THEN 1
                    WHEN 'Defender' THEN 2
                    WHEN 'Midfielder' THEN 3
                    WHEN 'Forward' THEN 4
                    WHEN 'Substitute' THEN 5
                    ELSE 6
                END,
                p.jersey_number
        ''', (match['home_club_id'], match['competition_id'])) or []
        
        away_lineup = fetch_all(conn, '''
            SELECT p.fullname, p.jersey_number, l.position
            FROM lineups l
            JOIN players p ON l.player_id = p.id
            WHERE l.club_id = ? AND l.competition_id = ?
            ORDER BY 
                CASE l.position
                    WHEN 'Goalkeeper' THEN 1
                    WHEN 'Defender' THEN 2
                    WHEN 'Midfielder' THEN 3
                    WHEN 'Forward' THEN 4
                    WHEN 'Substitute' THEN 5
                    ELSE 6
                END,
                p.jersey_number
        ''', (match['away_club_id'], match['competition_id'])) or []
        
        return render_template('match_details.html', 
                             match=match, 
                             events=events, 
                             home_lineup=home_lineup,
                             away_lineup=away_lineup)
                             
    except Exception as e:
        flash(f'Error loading match details: {str(e)}', 'error')
        return redirect(url_for('club_matches'))
    finally:
        conn.close()

@app.route('/admin/matches')
def admin_matches():
    if not check_admin_session():
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        # FIXED: Get all matches safely
        matches = fetch_all(conn, '''
            SELECT m.*, 
                   home.name as home_club_name, 
                   away.name as away_club_name,
                   c.name as competition_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            JOIN competitions c ON m.competition_id = c.id
            ORDER BY m.match_date DESC, m.match_time DESC
        ''') or []  # Fallback to empty list
        
        # FIXED: Get all clubs safely
        clubs = fetch_all(conn, 'SELECT id, name FROM clubs WHERE approved = TRUE') or []
        
        # FIXED: Get all active competitions safely
        competitions = fetch_all(conn, 'SELECT id, name FROM competitions WHERE is_active = TRUE') or []
        
        return render_template('admin_matches.html', 
                             matches=matches, 
                             clubs=clubs, 
                             competitions=competitions)
                             
    except Exception as e:
        flash(f'Error loading matches: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/club/matches')
def club_matches():
    if 'user_id' not in session or session.get('user_type') != 'club':
        flash('Please login as club to access this page.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        
        # FIXED: Get matches for this club safely
        matches = fetch_all(conn, '''
            SELECT m.*, 
                   home.name as home_club_name, 
                   away.name as away_club_name,
                   c.name as competition_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            JOIN competitions c ON m.competition_id = c.id
            WHERE (m.home_club_id = ? OR m.away_club_id = ?)
            ORDER BY m.match_date DESC, m.match_time DESC
        ''', (club_id, club_id)) or []  # Fallback to empty list
        
        return render_template('club_matches.html', matches=matches)
        
    except Exception as e:
        flash(f'Error loading matches: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/admin/create_match', methods=['POST'])
def create_match():
    if not check_admin_session():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        # FIXED: Safe form data access with defaults
        competition_id = request.form.get('competition_id', '').strip()
        home_club_id = request.form.get('home_club_id', '').strip()
        away_club_id = request.form.get('away_club_id', '').strip()
        match_date = request.form.get('match_date', '').strip()
        match_time = request.form.get('match_time', '').strip()
        location = request.form.get('location', '').strip()
        
        # FIXED: Validate required fields
        if not all([competition_id, home_club_id, away_club_id, match_date, match_time]):
            return jsonify({'success': False, 'message': 'All required fields must be filled'})
        
        # Check if clubs are different
        if home_club_id == away_club_id:
            return jsonify({'success': False, 'message': 'Home and away clubs cannot be the same'})
        
        # FIXED: Create match with error handling
        execute_sql(conn, '''
            INSERT INTO matches (competition_id, home_club_id, away_club_id, match_date, match_time, location, status)
            VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
        ''', (competition_id, home_club_id, away_club_id, match_date, match_time, location))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Match created successfully'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error creating match: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/update_match_score/<int:match_id>', methods=['POST'])
def update_match_score(match_id):
    if not check_admin_session():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        # FIXED: Safe form data access with defaults
        home_score = request.form.get('home_score', 0)
        away_score = request.form.get('away_score', 0)
        status = request.form.get('status', 'scheduled')
        
        # FIXED: Convert scores to integers safely
        try:
            home_score = int(home_score)
            away_score = int(away_score)
        except (ValueError, TypeError):
            home_score = 0
            away_score = 0
        
        execute_sql(conn, '''
            UPDATE matches 
            SET home_score = ?, away_score = ?, status = ?
            WHERE id = ?
        ''', (home_score, away_score, status, match_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Match score updated successfully'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error updating score: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/get_match_events/<int:match_id>', methods=['GET'])
def admin_get_match_events(match_id):
    if not check_admin_session():
        return jsonify([])
    
    conn = get_db_connection()
    try:
        events = fetch_all(conn, '''
            SELECT me.*, p.fullname as player_name, p.jersey_number, c.name as club_name
            FROM match_events me
            JOIN players p ON me.player_id = p.id
            JOIN clubs c ON p.club_id = c.id
            WHERE me.match_id = ?
            ORDER BY me.minute ASC
        ''', (match_id,)) or []  # Fallback to empty list
        
        # FIXED: Convert all events to dictionaries safely
        events_list = []
        for event in events:
            try:
                events_list.append(dict(event))
            except Exception:
                continue  # Skip invalid events
                
        return jsonify(events_list)
    
    except Exception as e:
        print(f"Error getting match events: {e}")
        return jsonify([])
    finally:
        conn.close()

@app.route('/admin/match_events/<int:match_id>')
def admin_match_events(match_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        match = fetch_one(conn, '''
            SELECT m.*, home.name as home_club_name, away.name as away_club_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            WHERE m.id = ?
        ''', (match_id,))
        
        if not match:
            flash('Match not found', 'error')
            return redirect(url_for('admin_matches'))
        
        events = fetch_all(conn, '''
            SELECT me.*, p.fullname as player_name, p.jersey_number, c.name as club_name
            FROM match_events me
            JOIN players p ON me.player_id = p.id
            JOIN clubs c ON p.club_id = c.id
            WHERE me.match_id = ?
            ORDER BY me.minute ASC
        ''', (match_id,))
        
        home_players = fetch_all(conn, '''
            SELECT p.id, p.fullname, p.jersey_number 
            FROM players p 
            WHERE p.club_id = ?
            ORDER BY p.fullname
        ''', (match['home_club_id'],))
        
        away_players = fetch_all(conn, '''
            SELECT p.id, p.fullname, p.jersey_number 
            FROM players p 
            WHERE p.club_id = ?
            ORDER BY p.fullname
        ''', (match['away_club_id'],))
        
        return render_template('admin_match_events.html', 
                             match=match, 
                             events=events,
                             home_players=home_players,
                             away_players=away_players)
    except Exception as e:
        flash(f'Error loading match events: {str(e)}', 'error')
        return redirect(url_for('admin_matches'))
    finally:
        conn.close()

@app.route('/admin/add_match_event/<int:match_id>', methods=['POST'])
def admin_add_match_event(match_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        player_id = request.form.get('player_id')
        event_type = request.form.get('event_type')
        minute = request.form.get('minute')
        description = request.form.get('description', '')
        
        if not all([player_id, event_type, minute]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_match_events', match_id=match_id))
        
        match = fetch_one(conn, 'SELECT * FROM matches WHERE id = ?', (match_id,))
        if not match:
            flash('Match not found', 'error')
            return redirect(url_for('admin_matches'))
        
        execute_sql(conn, '''
            INSERT INTO match_events (match_id, competition_id, player_id, event_type, minute, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (match_id, match['competition_id'], player_id, event_type, minute, description))
        
        if event_type == 'goal':
            execute_sql(conn, 'UPDATE players SET goals = COALESCE(goals, 0) + 1 WHERE id = ?', (player_id,))
        elif event_type == 'assist':
            execute_sql(conn, 'UPDATE players SET assists = COALESCE(assists, 0) + 1 WHERE id = ?', (player_id,))
        elif event_type == 'yellow_card':
            execute_sql(conn, 'UPDATE players SET yellow_cards = COALESCE(yellow_cards, 0) + 1 WHERE id = ?', (player_id,))
        elif event_type == 'red_card':
            execute_sql(conn, 'UPDATE players SET red_cards = COALESCE(red_cards, 0) + 1 WHERE id = ?', (player_id,))
        
        conn.commit()
        flash('Event added successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error adding event: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_match_events', match_id=match_id))

@app.route('/admin/delete_match_event/<int:event_id>', methods=['POST'])
def admin_delete_match_event(event_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        event = fetch_one(conn, 'SELECT * FROM match_events WHERE id = ?', (event_id,))
        
        if event:
            if event['event_type'] == 'goal':
                execute_sql(conn, 'UPDATE players SET goals = GREATEST(COALESCE(goals, 0) - 1, 0) WHERE id = ?', (event['player_id'],))
            elif event['event_type'] == 'assist':
                execute_sql(conn, 'UPDATE players SET assists = GREATEST(COALESCE(assists, 0) - 1, 0) WHERE id = ?', (event['player_id'],))
            elif event['event_type'] == 'yellow_card':
                execute_sql(conn, 'UPDATE players SET yellow_cards = GREATEST(COALESCE(yellow_cards, 0) - 1, 0) WHERE id = ?', (event['player_id'],))
            elif event['event_type'] == 'red_card':
                execute_sql(conn, 'UPDATE players SET red_cards = GREATEST(COALESCE(red_cards, 0) - 1, 0) WHERE id = ?', (event['player_id'],))
            
            execute_sql(conn, 'DELETE FROM match_events WHERE id = ?', (event_id,))
            conn.commit()
            flash('Event deleted successfully', 'success')
            
            return redirect(url_for('admin_match_events', match_id=event['match_id']))
        else:
            flash('Event not found', 'error')
            return redirect(url_for('admin_matches'))
            
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting event: {str(e)}', 'error')
        return redirect(url_for('admin_matches'))
    finally:
        conn.close()

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            admin = fetch_one(conn,
                'SELECT * FROM admins WHERE username = ? AND password = ?', 
                (username, password)
            )
            
            if admin:
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session['user_type'] = 'admin'
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials.', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not check_admin_session():
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        # Get pending registrations
        pending_registrations = fetch_all(conn, '''
            SELECT cr.*, c.name as club_name, comp.name as competition_name,
                   cl.local_government, cl.email as club_email
            FROM competition_registrations cr
            JOIN clubs c ON cr.club_id = c.id
            JOIN competitions comp ON cr.competition_id = comp.id
            JOIN clubs cl ON cr.club_id = cl.id
            WHERE cr.status = 'pending'
            ORDER BY cr.registration_date DESC
        ''')
        
        # Get approved registrations
        approved_registrations = fetch_all(conn, '''
            SELECT cr.*, c.name as club_name, comp.name as competition_name,
                   cl.local_government, a.username as approved_by_admin
            FROM competition_registrations cr
            JOIN clubs c ON cr.club_id = c.id
            JOIN competitions comp ON cr.competition_id = comp.id
            JOIN clubs cl ON cr.club_id = cl.id
            LEFT JOIN admins a ON cr.approved_by = a.id
            WHERE cr.status = 'approved'
            ORDER BY cr.approved_date DESC
        ''')
        
        # Get rejected registrations
        rejected_registrations = fetch_all(conn, '''
            SELECT cr.*, c.name as club_name, comp.name as competition_name,
                   cl.local_government
            FROM competition_registrations cr
            JOIN clubs c ON cr.club_id = c.id
            JOIN competitions comp ON cr.competition_id = comp.id
            JOIN clubs cl ON cr.club_id = cl.id
            WHERE cr.status = 'rejected'
            ORDER BY cr.registration_date DESC
        ''')
        
        # Get active competitions for the groups section
        active_competitions = fetch_all(conn, '''
            SELECT * FROM competitions 
            WHERE is_active = TRUE 
            ORDER BY name
        ''')
        
        # Get all clubs for management - FIXED: Format dates properly
        clubs_data = fetch_all(conn, '''
            SELECT c.*, 
                   COUNT(p.id) as player_count,
                   COUNT(cr.id) as competition_count
            FROM clubs c
            LEFT JOIN players p ON c.id = p.club_id AND p.status = 'approved'
            LEFT JOIN competition_registrations cr ON c.id = cr.club_id
            GROUP BY c.id
            ORDER BY c.approved DESC, c.name
        ''')
        
        # Format club dates properly to avoid subscriptable error
        formatted_clubs = []
        for club in clubs_data:
            club_dict = dict(club)
            # Handle registration_date formatting
            registration_date = club_dict.get('registration_date')
            if registration_date:
                if hasattr(registration_date, 'strftime'):
                    # It's a datetime/date object
                    club_dict['registration_date'] = registration_date.strftime('%Y-%m-%d')
                else:
                    # It's already a string, ensure it's only the date part
                    club_dict['registration_date'] = str(registration_date)[:10]
            else:
                club_dict['registration_date'] = 'N/A'
            formatted_clubs.append(club_dict)
        
        # Statistics - FIXED: Properly handle count results
        total_clubs_result = fetch_one(conn, 'SELECT COUNT(*) as count FROM clubs')
        total_players_result = fetch_one(conn, 'SELECT COUNT(*) as count FROM players')
        total_competitions_result = fetch_one(conn, 'SELECT COUNT(*) as count FROM competitions')
        
        stats = {
            'total_clubs': total_clubs_result['count'] if total_clubs_result else 0,
            'total_players': total_players_result['count'] if total_players_result else 0,
            'total_competitions': total_competitions_result['count'] if total_competitions_result else 0,
            'pending_registrations': len(pending_registrations),
            'approved_registrations': len(approved_registrations),
        }
        
        return render_template('admin_dashboard.html',
                             pending_registrations=pending_registrations,
                             approved_registrations=approved_registrations,
                             rejected_registrations=rejected_registrations,
                             stats=stats,
                             active_competitions=active_competitions,
                             all_clubs=formatted_clubs)  # Use formatted_clubs instead of raw data
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        import traceback
        print(f"Admin dashboard error: {traceback.format_exc()}")
        return redirect(url_for('admin_login'))
    finally:
        conn.close()

# ADD THESE ROUTES FOR CLUB MANAGEMENT:

@app.route('/admin/delete_club/<int:club_id>', methods=['POST'])
def admin_delete_club(club_id):
    if not check_admin_session():
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        # First, get club info for confirmation message
        club = fetch_one(conn, 'SELECT name FROM clubs WHERE id = ?', (club_id,))
        
        if not club:
            flash('Club not found.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        club_name = club['name']
        
        # Delete related records first (to maintain referential integrity)
        # Delete player records
        execute_sql(conn, 'DELETE FROM players WHERE club_id = ?', (club_id,))
        
        # Delete competition registrations
        execute_sql(conn, 'DELETE FROM competition_registrations WHERE club_id = ?', (club_id,))
        
        # Delete lineup records
        execute_sql(conn, 'DELETE FROM lineups WHERE club_id = ?', (club_id,))
        
        # Delete transfer requests where club is involved
        execute_sql(conn, 'DELETE FROM transfer_requests WHERE from_club_id = ? OR to_club_id = ?', 
                   (club_id, club_id))
        
        # Delete group assignments
        execute_sql(conn, 'DELETE FROM group_assignments WHERE club_id = ?', (club_id,))
        
        # Delete group standings
        execute_sql(conn, 'DELETE FROM group_standings WHERE club_id = ?', (club_id,))
        
        # Finally delete the club
        execute_sql(conn, 'DELETE FROM clubs WHERE id = ?', (club_id,))
        
        conn.commit()
        flash(f'Club "{club_name}" and all associated data have been deleted successfully.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting club: {str(e)}', 'error')
        print(f"Delete club error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/deactivate_club/<int:club_id>', methods=['POST'])
def admin_deactivate_club(club_id):
    if not check_admin_session():
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        club = fetch_one(conn, 'SELECT name FROM clubs WHERE id = ?', (club_id,))
        
        if not club:
            flash('Club not found.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Soft delete - set approved to False
        execute_sql(conn, 'UPDATE clubs SET approved = FALSE WHERE id = ?', (club_id,))
        
        conn.commit()
        flash(f'Club "{club["name"]}" has been deactivated.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deactivating club: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/activate_club/<int:club_id>', methods=['POST'])
def admin_activate_club(club_id):
    if not check_admin_session():
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        club = fetch_one(conn, 'SELECT name FROM clubs WHERE id = ?', (club_id,))
        
        if not club:
            flash('Club not found.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Activate club - set approved to True
        execute_sql(conn, 'UPDATE clubs SET approved = TRUE WHERE id = ?', (club_id,))
        
        conn.commit()
        flash(f'Club "{club["name"]}" has been activated.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error activating club: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/create_competition', methods=['GET', 'POST'])
def admin_create_competition():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        registration_deadline = request.form['registration_deadline']
        is_active = 'is_active' in request.form
        
        conn = get_db_connection()
        try:
            # Check if competition already exists
            existing_comp = fetch_one(conn,
                'SELECT id FROM competitions WHERE name = ?', 
                (name,)
            )
            
            if existing_comp:
                flash('Competition with this name already exists.', 'error')
                return render_template('admin_create_competition.html')
            
            # Insert new competition
            execute_sql(conn, '''
                INSERT INTO competitions (name, description, start_date, end_date, registration_deadline, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, start_date, end_date, registration_deadline, is_active))
            
            conn.commit()
            flash('Competition created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error creating competition: {str(e)}', 'error')
            return render_template('admin_create_competition.html')
        finally:
            conn.close()
    
    return render_template('admin_create_competition.html')

@app.route('/admin/approve_registration/<int:registration_id>', methods=['POST'])
def approve_registration(registration_id):
    print(f"=== APPROVE ROUTE CALLED ===")
    print(f"Session data: admin_id={session.get('admin_id')}, user_type={session.get('user_type')}")
    print(f"Registration ID: {registration_id}")
    
    # Check admin session with detailed debugging
    if not session.get('admin_id'):
        print("❌ FAIL: No admin_id in session")
        return jsonify({
            'success': False, 
            'message': 'No admin ID in session'
        }), 401
    
    if session.get('user_type') != 'admin':
        print(f"❌ FAIL: user_type is '{session.get('user_type')}' instead of 'admin'")
        return jsonify({
            'success': False, 
            'message': f"User type is '{session.get('user_type')}' not 'admin'"
        }), 401
    
    print("✅ PASS: Admin session is valid")
    
    conn = get_db_connection()
    try:
        # Check if registration exists
        registration = fetch_one(conn,
            'SELECT * FROM competition_registrations WHERE id = ?', 
            (registration_id,)
        )
        
        if not registration:
            return jsonify({'success': False, 'message': 'Registration not found'}), 404
        
        # Update registration status
        execute_sql(conn, '''
            UPDATE competition_registrations 
            SET status = 'approved', 
                approved_by = ?,
                approved_date = CURRENT_TIMESTAMP,
                notes = ?
            WHERE id = ?
        ''', (session['admin_id'], request.form.get('notes', ''), registration_id))
        
        conn.commit()
        print(f"✅ SUCCESS: Registration {registration_id} approved")
        return jsonify({'success': True, 'message': 'Registration approved successfully!'})
    
    except Exception as e:
        conn.rollback()
        print(f"❌ DATABASE ERROR: {e}")
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/admin/reject_registration/<int:registration_id>', methods=['POST'])
def reject_registration(registration_id):
    print(f"=== REJECT ROUTE CALLED ===")
    print(f"Session data: admin_id={session.get('admin_id')}, user_type={session.get('user_type')}")
    print(f"Registration ID: {registration_id}")
    
    # Check admin session with detailed debugging
    if not session.get('admin_id'):
        print("❌ FAIL: No admin_id in session")
        return jsonify({
            'success': False, 
            'message': 'No admin ID in session'
        }), 401
    
    if session.get('user_type') != 'admin':
        print(f"❌ FAIL: user_type is '{session.get('user_type')}' instead of 'admin'")
        return jsonify({
            'success': False, 
            'message': f"User type is '{session.get('user_type')}' not 'admin'"
        }), 401
    
    print("✅ PASS: Admin session is valid")
    
    conn = get_db_connection()
    try:
        # Check if registration exists
        registration = fetch_one(conn,
            'SELECT * FROM competition_registrations WHERE id = ?', 
            (registration_id,)
        )
        
        if not registration:
            return jsonify({'success': False, 'message': 'Registration not found'}), 404
        
        # Update registration status
        execute_sql(conn, '''
            UPDATE competition_registrations 
            SET status = 'rejected',
                notes = ?
            WHERE id = ?
        ''', (request.form.get('notes', ''), registration_id))
        
        conn.commit()
        print(f"✅ SUCCESS: Registration {registration_id} rejected")
        return jsonify({'success': True, 'message': 'Registration rejected successfully!'})
    
    except Exception as e:
        conn.rollback()
        print(f"❌ DATABASE ERROR: {e}")
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/admin/check_session')
def check_admin_session_route():
    """Route to check if admin session is valid"""
    if check_admin_session():
        return jsonify({'valid': True, 'username': session.get('admin_username')})
    else:
        return jsonify({'valid': False}), 401

@app.route('/admin/pending_clubs')
def admin_pending_clubs():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        print("🔄 Loading pending clubs...")
        
        # Get pending clubs
        pending_clubs_result = fetch_all(conn, '''
            SELECT id, name, local_government, email, phone, logo, registration_date 
            FROM clubs WHERE approved = FALSE ORDER BY registration_date DESC
        ''')
        
        # Get approved clubs
        approved_clubs_result = fetch_all(conn, '''
            SELECT id, name, local_government, email, phone, logo, registration_date 
            FROM clubs WHERE approved = TRUE ORDER BY registration_date DESC
        ''')
        
        # SIMPLE FIX: Don't format dates at all, let template handle them
        pending_clubs = [dict(club) for club in pending_clubs_result]
        approved_clubs = [dict(club) for club in approved_clubs_result]
        
        print(f"✅ Found {len(pending_clubs)} pending clubs and {len(approved_clubs)} approved clubs")
        
        return render_template('admin_pending_clubs.html', 
                             pending_clubs=pending_clubs,
                             approved_clubs=approved_clubs)
        
    except Exception as e:
        error_msg = f'Error loading pending clubs: {str(e)}'
        flash(error_msg, 'error')
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/admin/approve_club/<int:club_id>', methods=['POST'])
def approve_club(club_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        # Approve the club
        execute_sql(conn, 'UPDATE clubs SET approved = TRUE WHERE id = ?', (club_id,))
        conn.commit()
        
        # Get club info for success message
        club = fetch_one(conn, 'SELECT name FROM clubs WHERE id = ?', (club_id,))
        
        return jsonify({'success': True, 'message': f'Club "{club["name"]}" approved successfully!'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/reject_club/<int:club_id>', methods=['POST'])
def reject_club(club_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        # Get club info before deletion
        club = fetch_one(conn, 'SELECT name FROM clubs WHERE id = ?', (club_id,))
        
        # Delete the club (or you can add a 'rejected' status instead)
        execute_sql(conn, 'DELETE FROM clubs WHERE id = ?', (club_id,))
        conn.commit()
        
        return jsonify({'success': True, 'message': f'Club "{club["name"]}" rejected and removed.'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/competition_groups/<int:competition_id>')
def admin_competition_groups(competition_id):
    """Admin page to manage competition groups"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        competition = fetch_one(conn,
            'SELECT * FROM competitions WHERE id = ?', (competition_id,)
        )
        
        groups = fetch_all(conn, '''
            SELECT * FROM competition_groups 
            WHERE competition_id = ? 
            ORDER BY group_name
        ''', (competition_id,))
        
        # Get registered clubs for this competition
        registered_clubs = fetch_all(conn, '''
            SELECT c.*, cr.registration_date 
            FROM clubs c
            JOIN competition_registrations cr ON c.id = cr.club_id
            WHERE cr.competition_id = ? AND cr.status = 'approved'
            ORDER BY c.name
        ''', (competition_id,))
        
        # Get group assignments
        group_assignments = {}
        for group in groups:
            assignments = fetch_all(conn, '''
                SELECT ga.*, c.name as club_name, c.logo
                FROM group_assignments ga
                JOIN clubs c ON ga.club_id = c.id
                WHERE ga.group_id = ?
            ''', (group['id'],))
            group_assignments[group['id']] = assignments
        
        return render_template('admin_competition_groups.html',
                             competition=competition,
                             groups=groups,
                             registered_clubs=registered_clubs,
                             group_assignments=group_assignments)
    except Exception as e:
        flash(f'Error loading competition groups: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/admin/create_group/<int:competition_id>', methods=['POST'])
def admin_create_group(competition_id):
    """Create a new group for competition"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    group_name = request.form['group_name']
    
    conn = get_db_connection()
    try:
        # Check if group already exists
        existing = fetch_one(conn,
            'SELECT id FROM competition_groups WHERE competition_id = ? AND group_name = ?',
            (competition_id, group_name)
        )
        
        if existing:
            return jsonify({'success': False, 'message': 'Group already exists'})
        
        execute_sql(conn,
            'INSERT INTO competition_groups (competition_id, group_name) VALUES (?, ?)',
            (competition_id, group_name)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Group created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/assign_club_to_group', methods=['POST'])
def admin_assign_club_to_group():
    """Assign club to a group"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    competition_id = request.form['competition_id']
    group_id = request.form['group_id']
    club_id = request.form['club_id']
    
    conn = get_db_connection()
    try:
        # Remove any existing assignment for this club in this competition
        execute_sql(conn,
            'DELETE FROM group_assignments WHERE competition_id = ? AND club_id = ?',
            (competition_id, club_id)
        )
        
        # Add new assignment
        execute_sql(conn,
            'INSERT INTO group_assignments (competition_id, group_id, club_id) VALUES (?, ?, ?)',
            (competition_id, group_id, club_id)
        )
        
        # Initialize standings
        execute_sql(conn, '''
            INSERT INTO group_standings 
            (competition_id, group_id, club_id, status)
            VALUES (?, ?, ?, 'active')
        ''', (competition_id, group_id, club_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Club assigned to group successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/remove_club_from_group/<int:assignment_id>', methods=['POST'])
def admin_remove_club_from_group(assignment_id):
    """Remove club from group"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        execute_sql(conn, 'DELETE FROM group_assignments WHERE id = ?', (assignment_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Club removed from group'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/group_matches/<int:competition_id>')
def admin_group_matches(competition_id):
    """Manage group stage matches"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    try:
        competition = fetch_one(conn,
            'SELECT * FROM competitions WHERE id = ?', (competition_id,)
        )
        
        groups = fetch_all(conn, '''
            SELECT * FROM competition_groups 
            WHERE competition_id = ? 
            ORDER BY group_name
        ''', (competition_id,))
        
        group_matches = {}
        group_standings = {}
        
        for group in groups:
            # Get matches for this group
            matches = fetch_all(conn, '''
                SELECT gm.*, 
                       home.name as home_club_name, 
                       away.name as away_club_name,
                       home.logo as home_logo,
                       away.logo as away_logo
                FROM group_matches gm
                JOIN clubs home ON gm.home_club_id = home.id
                JOIN clubs away ON gm.away_club_id = away.id
                WHERE gm.group_id = ?
                ORDER BY gm.match_date, gm.match_time
            ''', (group['id'],))
            group_matches[group['id']] = matches
            
            # Get standings for this group
            standings = fetch_all(conn, '''
                SELECT gs.*, c.name as club_name, c.logo
                FROM group_standings gs
                JOIN clubs c ON gs.club_id = c.id
                WHERE gs.group_id = ?
                ORDER BY gs.points DESC, (gs.goals_for - gs.goals_against) DESC, gs.goals_for DESC
            ''', (group['id'],))
            group_standings[group['id']] = standings
        
        return render_template('admin_group_matches.html',
                             competition=competition,
                             groups=groups,
                             group_matches=group_matches,
                             group_standings=group_standings)
    except Exception as e:
        flash(f'Error loading group matches: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/admin/create_group_match', methods=['POST'])
def admin_create_group_match():
    """Create a group stage match"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        competition_id = request.form['competition_id']
        group_id = request.form['group_id']
        home_club_id = request.form['home_club_id']
        away_club_id = request.form['away_club_id']
        match_date = request.form['match_date']
        match_time = request.form.get('match_time')
        location = request.form.get('location', '')
        
        # Check if clubs are in the same group
        home_in_group = fetch_one(conn,
            'SELECT id FROM group_assignments WHERE group_id = ? AND club_id = ?',
            (group_id, home_club_id)
        )
        
        away_in_group = fetch_one(conn,
            'SELECT id FROM group_assignments WHERE group_id = ? AND club_id = ?',
            (group_id, away_club_id)
        )
        
        if not home_in_group or not away_in_group:
            return jsonify({'success': False, 'message': 'Both clubs must be in the same group'})
        
        # Check if match already exists
        existing = fetch_one(conn, '''
            SELECT id FROM group_matches 
            WHERE group_id = ? AND home_club_id = ? AND away_club_id = ?
        ''', (group_id, home_club_id, away_club_id))
        
        if existing:
            return jsonify({'success': False, 'message': 'Match already exists'})
        
        execute_sql(conn, '''
            INSERT INTO group_matches 
            (competition_id, group_id, home_club_id, away_club_id, match_date, match_time, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (competition_id, group_id, home_club_id, away_club_id, match_date, match_time, location))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Group match created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/update_group_match_score/<int:match_id>', methods=['POST'])
def admin_update_group_match_score(match_id):
    """Update group match score and standings"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        home_score = int(request.form['home_score'])
        away_score = int(request.form['away_score'])
        status = request.form['status']
        
        # Get match details
        match = fetch_one(conn, 'SELECT * FROM group_matches WHERE id = ?', (match_id,))
        if not match:
            return jsonify({'success': False, 'message': 'Match not found'})
        
        # Update match
        execute_sql(conn, '''
            UPDATE group_matches 
            SET home_score = ?, away_score = ?, status = ?
            WHERE id = ?
        ''', (home_score, away_score, status, match_id))
        
        # Update standings if match is completed
        if status == 'completed':
            update_group_standings(conn, match['group_id'], match['home_club_id'], match['away_club_id'], home_score, away_score)
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Match updated successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

def update_group_standings(conn, group_id, home_club_id, away_club_id, home_score, away_score):
    """Update group standings after a match"""
    # Get current standings
    home_standing = fetch_one(conn,
        'SELECT * FROM group_standings WHERE group_id = ? AND club_id = ?',
        (group_id, home_club_id)
    )
    
    away_standing = fetch_one(conn,
        'SELECT * FROM group_standings WHERE group_id = ? AND club_id = ?',
        (group_id, away_club_id)
    )
    
    # Update matches played
    execute_sql(conn, '''
        UPDATE group_standings 
        SET matches_played = COALESCE(matches_played, 0) + 1,
            goals_for = COALESCE(goals_for, 0) + ?,
            goals_against = COALESCE(goals_against, 0) + ?
        WHERE group_id = ? AND club_id = ?
    ''', (home_score, away_score, group_id, home_club_id))
    
    execute_sql(conn, '''
        UPDATE group_standings 
        SET matches_played = COALESCE(matches_played, 0) + 1,
            goals_for = COALESCE(goals_for, 0) + ?,
            goals_against = COALESCE(goals_against, 0) + ?
        WHERE group_id = ? AND club_id = ?
    ''', (away_score, home_score, group_id, away_club_id))
    
    # Update wins/draws/losses and points
    if home_score > away_score:
        # Home win
        execute_sql(conn, '''
            UPDATE group_standings 
            SET wins = COALESCE(wins, 0) + 1, points = COALESCE(points, 0) + 3
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, home_club_id))
        
        execute_sql(conn, '''
            UPDATE group_standings 
            SET losses = COALESCE(losses, 0) + 1
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, away_club_id))
        
    elif away_score > home_score:
        # Away win
        execute_sql(conn, '''
            UPDATE group_standings 
            SET wins = COALESCE(wins, 0) + 1, points = COALESCE(points, 0) + 3
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, away_club_id))
        
        execute_sql(conn, '''
            UPDATE group_standings 
            SET losses = COALESCE(losses, 0) + 1
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, home_club_id))
        
    else:
        # Draw
        execute_sql(conn, '''
            UPDATE group_standings 
            SET draws = COALESCE(draws, 0) + 1, points = COALESCE(points, 0) + 1
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, home_club_id))
        
        execute_sql(conn, '''
            UPDATE group_standings 
            SET draws = COALESCE(draws, 0) + 1, points = COALESCE(points, 0) + 1
            WHERE group_id = ? AND club_id = ?
        ''', (group_id, away_club_id))

@app.route('/competition/<int:competition_id>/groups')
def public_competition_groups(competition_id):
    """Public page showing competition groups and standings"""
    conn = get_db_connection()
    try:
        competition = fetch_one(conn,
            'SELECT * FROM competitions WHERE id = ?', (competition_id,)
        )
        
        if not competition:
            flash('Competition not found', 'error')
            return redirect(url_for('competitions'))
        
        groups = fetch_all(conn, '''
            SELECT * FROM competition_groups 
            WHERE competition_id = ? 
            ORDER BY group_name
        ''', (competition_id,))
        
        group_standings = {}
        group_matches = {}
        
        for group in groups:
            # Get standings
            standings = fetch_all(conn, '''
                SELECT gs.*, c.name as club_name, c.logo
                FROM group_standings gs
                JOIN clubs c ON gs.club_id = c.id
                WHERE gs.group_id = ?
                ORDER BY gs.points DESC, (gs.goals_for - gs.goals_against) DESC, gs.goals_for DESC
            ''', (group['id'],))
            group_standings[group['id']] = standings
            
            # Get recent matches
            matches = fetch_all(conn, '''
                SELECT gm.*, 
                       home.name as home_club_name, 
                       away.name as away_club_name,
                       home.logo as home_logo,
                       away.logo as away_logo
                FROM group_matches gm
                JOIN clubs home ON gm.home_club_id = home.id
                JOIN clubs away ON gm.away_club_id = away.id
                WHERE gm.group_id = ?
                ORDER BY gm.match_date DESC, gm.match_time DESC
                LIMIT 10
            ''', (group['id'],))
            group_matches[group['id']] = matches
        
        return render_template('public_competition_groups.html',
                             competition=competition,
                             groups=groups,
                             group_standings=group_standings,
                             group_matches=group_matches)
    except Exception as e:
        flash(f'Error loading competition groups: {str(e)}', 'error')
        return redirect(url_for('competitions'))
    finally:
        conn.close()

@app.route('/admin/update_elimination_status', methods=['POST'])
def admin_update_elimination_status():
    """Update club elimination status in group"""
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conn = get_db_connection()
    try:
        standing_id = request.form['standing_id']
        status = request.form['status']
        
        execute_sql(conn, '''
            UPDATE group_standings SET status = ? WHERE id = ?
        ''', (status, standing_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'Status updated to {status}'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        
        conn = get_db_connection()
        try:
            if user_type == 'player':
                user = fetch_one(conn,
                    'SELECT * FROM players WHERE username = ? AND password = ?', 
                    (username, password)
                )
                
                # Check if player is approved
                if user and user.get('status') != 'approved':
                    flash('Your account is pending approval from your club. Please wait for approval before logging in.', 'warning')
                    return render_template('login.html')
                    
            else:  # club
                user = fetch_one(conn,
                    'SELECT * FROM clubs WHERE name = ? AND password = ?', 
                    (username, password)
                )
                
                # Check if club is approved
                if user and not user.get('approved'):
                    flash('Your club registration is pending approval. Please wait for admin approval before logging in.', 'warning')
                    return render_template('login.html')
            
            if user:
                session['user_id'] = user['id']
                session['user_type'] = user_type
                session['username'] = user['username'] if user_type == 'player' else user['name']
                
                if user_type == 'player':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('club_dashboard'))
            else:
                flash('Invalid credentials. Please try again.', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('login.html')

@app.route('/matches')
def public_matches():
    """Public matches page accessible to all users"""
    conn = get_db_connection()
    try:
        print("🔍 Loading public matches...")
        
        # Get all matches with club and competition details
        matches = fetch_all(conn, '''
            SELECT m.*, 
                   home.name as home_club_name, 
                   away.name as away_club_name,
                   home.logo as home_club_logo,
                   away.logo as away_club_logo,
                   c.name as competition_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            JOIN competitions c ON m.competition_id = c.id
            ORDER BY m.match_date DESC, m.match_time DESC
        ''')
        
        print(f"✅ Found {len(matches)} matches")
        return render_template('public_matches.html', matches=matches)
        
    except Exception as e:
        print(f"❌ Error in public_matches: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading matches: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/debug/clubs')
def debug_clubs():
    """Debug route to check clubs in database"""
    conn = get_db_connection()
    try:
        # Get all clubs
        clubs = fetch_all(conn, 'SELECT * FROM clubs')
        clubs_list = [dict(club) for club in clubs]
        
        # Get clubs by local government
        dala_clubs = fetch_all(conn,
            'SELECT name FROM clubs WHERE local_government = "Dala"'
        )
        
        return jsonify({
            'total_clubs': len(clubs_list),
            'all_clubs': clubs_list,
            'dala_clubs': [club['name'] for club in dala_clubs],
            'local_governments': LOCAL_GOVERNMENTS
        })
    finally:
        conn.close()

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['user_type'] != 'player':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        player = fetch_one(conn, '''
            SELECT p.*, c.name as club_name 
            FROM players p 
            JOIN clubs c ON p.club_id = c.id 
            WHERE p.id = ?
        ''', (session['user_id'],))
        
        # Check if player exists
        if not player:
            session.clear()
            flash('Player not found. Please login again.', 'error')
            return redirect(url_for('login'))
        
        # Get pending transfers
        pending_transfers = fetch_all(conn, '''
            SELECT tr.*, to_club.name as to_club_name
            FROM transfer_requests tr
            JOIN clubs to_club ON tr.to_club_id = to_club.id
            WHERE tr.player_id = ? AND tr.status IN ('pending', 'approved_by_from')
        ''', (session['user_id'],))
        
        # Calculate age from date of birth - FIXED VERSION
        try:
            # Check if date_of_birth is already a date object or string
            if isinstance(player['date_of_birth'], str):
                birth_date = datetime.strptime(player['date_of_birth'], '%Y-%m-%d').date()
            else:
                birth_date = player['date_of_birth']
            
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, KeyError, TypeError) as e:
            print(f"Age calculation error: {e}")
            age = 'N/A'
        
        return render_template('dashboard.html', player=player, age=age, pending_transfers=pending_transfers)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))
    finally:
        conn.close()

@app.route('/manage_lineup', methods=['GET', 'POST'])
def manage_lineup():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club_id = session['user_id']
        
        if request.method == 'POST':
            competition_id = request.form.get('competition_id')
            player_positions = request.form.getlist('player_positions')
            player_ids = request.form.getlist('player_ids')
            
            # Clear existing lineup for this competition
            execute_sql(conn,
                'DELETE FROM lineups WHERE club_id = ? AND competition_id = ?',
                (club_id, competition_id)
            )
            
            # Insert new lineup
            for player_id, position in zip(player_ids, player_positions):
                if player_id and position:
                    execute_sql(conn, '''
                        INSERT INTO lineups (club_id, competition_id, player_id, position)
                        VALUES (?, ?, ?, ?)
                    ''', (club_id, competition_id, player_id, position))
            
            conn.commit()
            flash('Lineup updated successfully!', 'success')
            return redirect(url_for('manage_lineup'))
        
        # Get club's players
        players = fetch_all(conn,
            'SELECT id, fullname, jersey_number FROM players WHERE club_id = ? ORDER BY fullname',
            (club_id,)
        )
        
        # Get all active competitions
        competitions = fetch_all(conn, '''
            SELECT c.id, c.name 
            FROM competitions c
            WHERE c.is_active = TRUE
        ''')
        
        # Get current lineups for all competitions
        current_lineups = {}
        for comp in competitions:
            lineup_data = fetch_all(conn, '''
                SELECT p.id, l.position
                FROM players p
                JOIN lineups l ON p.id = l.player_id
                WHERE l.club_id = ? AND l.competition_id = ?
            ''', (club_id, comp['id']))
            
            current_lineups[comp['id']] = {str(player['id']): player['position'] for player in lineup_data}
        
        return render_template('manage_lineup.html', 
                             players=players, 
                             competitions=competitions,
                             current_lineups=current_lineups)
    
    except Exception as e:
        flash(f'Error saving lineup: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/match/<int:match_id>')
def public_match_details(match_id):
    """Public match details page accessible to all users"""
    conn = get_db_connection()
    try:
        # Get match details
        match = fetch_one(conn, '''
            SELECT m.*, 
                   home.name as home_club_name, 
                   away.name as away_club_name,
                   home.logo as home_club_logo,
                   away.logo as away_club_logo,
                   c.name as competition_name
            FROM matches m
            JOIN clubs home ON m.home_club_id = home.id
            JOIN clubs away ON m.away_club_id = away.id
            JOIN competitions c ON m.competition_id = c.id
            WHERE m.id = ?
        ''', (match_id,))
        
        if not match:
            flash('Match not found.', 'error')
            return redirect(url_for('index'))
        
        # Get match events (goals, assists, cards)
        events = fetch_all(conn, '''
            SELECT me.*, p.fullname as player_name, p.jersey_number,
                   cl.name as club_name, cl.id as club_id
            FROM match_events me
            JOIN players p ON me.player_id = p.id
            JOIN clubs cl ON p.club_id = cl.id
            WHERE me.match_id = ?
            ORDER BY me.minute ASC
        ''', (match_id,))
        
        # Get lineups for both clubs
        home_lineup = fetch_all(conn, '''
            SELECT p.fullname, p.jersey_number, l.position
            FROM lineups l
            JOIN players p ON l.player_id = p.id
            WHERE l.club_id = ? AND l.competition_id = ?
            ORDER BY 
                CASE 
                    WHEN l.position = 'GK' THEN 1
                    WHEN l.position LIKE 'DF%' THEN 2
                    WHEN l.position LIKE 'MF%' THEN 3
                    WHEN l.position LIKE 'FW%' THEN 4
                    ELSE 5
                END,
                p.jersey_number
        ''', (match['home_club_id'], match['competition_id']))
        
        away_lineup = fetch_all(conn, '''
            SELECT p.fullname, p.jersey_number, l.position
            FROM lineups l
            JOIN players p ON l.player_id = p.id
            WHERE l.club_id = ? AND l.competition_id = ?
            ORDER BY 
                CASE 
                    WHEN l.position = 'GK' THEN 1
                    WHEN l.position LIKE 'DF%' THEN 2
                    WHEN l.position LIKE 'MF%' THEN 3
                    WHEN l.position LIKE 'FW%' THEN 4
                    ELSE 5
                END,
                p.jersey_number
        ''', (match['away_club_id'], match['competition_id']))
        
        return render_template('public_match_details.html', 
                             match=match, 
                             events=events,
                             home_lineup=home_lineup,
                             away_lineup=away_lineup)
        
    except Exception as e:
        flash(f'Error loading match details: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()



@app.route('/get_lineup/<int:competition_id>')
def get_lineup(competition_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return jsonify({})
    
    conn = get_db_connection()
    try:
        lineup = fetch_all(conn, '''
            SELECT player_id, position 
            FROM lineups 
            WHERE club_id = ? AND competition_id = ?
        ''', (session['user_id'], competition_id))
        
        lineup_dict = {str(player['player_id']): player['position'] for player in lineup}
        return jsonify(lineup_dict)
    
    finally:
        conn.close()

@app.route('/players')
def players():
    conn = get_db_connection()
    try:
        players = fetch_all(conn, '''
            SELECT p.*, c.name as club_name 
            FROM players p 
            JOIN clubs c ON p.club_id = c.id 
            WHERE p.status = 'approved'  -- Only club-approved players
            ORDER BY p.goals DESC, p.assists DESC
        ''')
        
        # Calculate age for each player - FIXED VERSION
        players_with_age = []
        for player in players:
            age = 'N/A'
            try:
                dob = player['date_of_birth']
                if isinstance(dob, str):
                    birth_date = datetime.strptime(dob, '%Y-%m-%d').date()
                else:
                    birth_date = dob
                    
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            except:
                age = 'N/A'
                
            players_with_age.append((player, age))
        
        return render_template('players.html', players=players_with_age)
    except Exception as e:
        flash(f'Error loading players: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/clubs')
def clubs():
    conn = get_db_connection()
    try:
        clubs = fetch_all(conn, 'SELECT * FROM clubs WHERE approved = TRUE')
        
        # Format dates properly for template
        formatted_clubs = []
        for club in clubs:
            club_data = dict(club)
            
            # Handle registration_date - convert to string if it's a datetime object
            registration_date = club_data.get('registration_date')
            if registration_date:
                if hasattr(registration_date, 'strftime'):
                    # It's a datetime/date object
                    club_data['registration_date'] = registration_date.strftime('%Y-%m-%d')
                else:
                    # It's already a string, ensure it's only the date part
                    club_data['registration_date'] = str(registration_date)[:10]
            else:
                club_data['registration_date'] = 'N/A'
                
            formatted_clubs.append(club_data)
        
        return render_template('clubs.html', clubs=formatted_clubs)
    except Exception as e:
        flash(f'Error loading clubs: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/test-upload')
def test_upload():
    """Test if Cloudinary uploads work"""
    try:
        # Create a simple test image
        from io import BytesIO
        import base64
        
        # Create a simple PNG image in memory
        test_image_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        test_image = BytesIO(test_image_data)
        
        # Try upload
        result = storage.upload_file(test_image, "test_file.jpg", "test-folder")
        
        if result:
            return f"✅ SUCCESS! Image uploaded to: <a href='{result}' target='_blank'>{result}</a>"
        else:
            return "❌ FAILED: Cloudinary upload returned None"
            
    except Exception as e:
        return f"❌ ERROR: {str(e)}"

@app.route('/register_club', methods=['GET', 'POST'])
def register_club():
    if request.method == 'POST':
        try:
            name = request.form['name']
            local_government = request.form['local_government']
            email = request.form['email']
            phone = request.form['phone']
            password = request.form['password']
            
            conn = get_db_connection()
            try:
                # Check if club already exists
                existing_club = fetch_one(conn,
                    'SELECT id FROM clubs WHERE name = ? OR email = ?', 
                    (name, email)
                )
                
                if existing_club:
                    flash('Club name or email already exists.', 'error')
                    return render_template('register_club.html', local_governments=LOCAL_GOVERNMENTS)
                
                # Handle logo upload
                logo = None
                if 'logo' in request.files:
                    file = request.files['logo']
                    if file and file.filename != '':
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                            filename = secure_filename(f"{name}_{file.filename}")
                            file_url = storage.upload_file(file, filename, 'club-logos')
                            if file_url:
                                logo = file_url
                
                # Insert club into database (initially not approved)
                execute_sql(conn, '''
                    INSERT INTO clubs (name, local_government, email, phone, password, logo, approved)
                    VALUES (?, ?, ?, ?, ?, ?, FALSE)
                ''', (name, local_government, email, phone, password, logo))
                
                conn.commit()
                flash('Registration submitted! Your club is pending admin approval. You will be notified once approved.', 'success')
                return redirect(url_for('index'))
            finally:
                conn.close()
        
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('register_club.html', local_governments=LOCAL_GOVERNMENTS)
    
    return render_template('register_club.html', local_governments=LOCAL_GOVERNMENTS)

@app.route('/club_dashboard')
def club_dashboard():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        club = fetch_one(conn, 'SELECT * FROM clubs WHERE id = ?', (session['user_id'],))
        
        # Only fetch approved players for main roster
        players = fetch_all(conn, 'SELECT * FROM players WHERE club_id = ? AND status = ?', 
                          (session['user_id'], 'approved'))
        
        # Get pending players count for the badge
        pending_count_result = fetch_one(conn, 'SELECT COUNT(*) as count FROM players WHERE club_id = ? AND status = ?', 
                                      (session['user_id'], 'pending'))
        pending_count = pending_count_result['count'] if pending_count_result else 0
        
        competitions = fetch_all(conn, '''
            SELECT c.*, cr.status 
            FROM competitions c 
            JOIN competition_registrations cr ON c.id = cr.competition_id 
            WHERE cr.club_id = ?
        ''', (session['user_id'],))
        
        return render_template('club_dashboard.html', club=club, players=players, 
                             pending_count=pending_count, competitions=competitions)
    except Exception as e:
        flash(f'Error loading club dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))
    finally:
        conn.close()

@app.route('/club/player_approvals')
def club_player_approvals():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        # Get pending players for this club
        pending_players = fetch_all(conn, '''
            SELECT * FROM players 
            WHERE club_id = ? AND status = ?
            ORDER BY id DESC
        ''', (session['user_id'], 'pending'))
        
        # Get approved players for this club
        approved_players = fetch_all(conn, '''
            SELECT * FROM players 
            WHERE club_id = ? AND status = ?
            ORDER BY fullname
        ''', (session['user_id'], 'approved'))
        
        return render_template('club_player_approvals.html', 
                             pending_players=pending_players,
                             approved_players=approved_players)
    except Exception as e:
        flash(f'Error loading player approvals: {str(e)}', 'error')
        return redirect(url_for('club_dashboard'))
    finally:
        conn.close()

@app.route('/club/approve_player/<int:player_id>')
def club_approve_player(player_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        # Verify the player belongs to this club
        player = fetch_one(conn, 'SELECT * FROM players WHERE id = ? AND club_id = ?', 
                         (player_id, session['user_id']))
        
        if not player:
            flash('Player not found or you do not have permission to approve this player.', 'error')
            return redirect(url_for('club_player_approvals'))
        
        # Update status to approved
        execute_sql(conn, 'UPDATE players SET status = ? WHERE id = ?', 
                    ('approved', player_id))
        conn.commit()
        flash('Player approved successfully!', 'success')
        return redirect(url_for('club_player_approvals'))
    except Exception as e:
        conn.rollback()
        flash(f'Error approving player: {str(e)}', 'error')
        return redirect(url_for('club_player_approvals'))
    finally:
        conn.close()

@app.route('/club/reject_player/<int:player_id>')
def club_reject_player(player_id):
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        # Verify the player belongs to this club
        player = fetch_one(conn, 'SELECT * FROM players WHERE id = ? AND club_id = ?', 
                         (player_id, session['user_id']))
        
        if not player:
            flash('Player not found or you do not have permission to reject this player.', 'error')
            return redirect(url_for('club_player_approvals'))
        
        # Update status to rejected
        execute_sql(conn, 'UPDATE players SET status = ? WHERE id = ?', 
                    ('rejected', player_id))
        conn.commit()
        flash('Player registration rejected.', 'success')
        return redirect(url_for('club_player_approvals'))
    except Exception as e:
        conn.rollback()
        flash(f'Error rejecting player: {str(e)}', 'error')
        return redirect(url_for('club_player_approvals'))
    finally:
        conn.close()

@app.route('/competitions')
def competitions():
    conn = get_db_connection()
    try:
        competitions = fetch_all(conn, 'SELECT * FROM competitions WHERE is_active = TRUE')
        
        # Create a list to store competition data with top scorers
        competition_data = []
        
        for comp in competitions:
            # Get top scorers for this competition - FIXED for PostgreSQL
            top_scorers = fetch_all(conn, '''
                SELECT p.fullname, p.profile_picture, c.name as club_name, COUNT(me.id) as goals
                FROM match_events me
                JOIN players p ON me.player_id = p.id
                JOIN clubs c ON p.club_id = c.id
                WHERE me.competition_id = ? AND me.event_type = 'goal'
                GROUP BY p.id, p.fullname, p.profile_picture, c.name
                ORDER BY goals DESC
                LIMIT 5
            ''', (comp['id'],))
            
            # Create a dictionary with competition data and top scorers
            comp_data = {
                'id': comp['id'],
                'name': comp['name'],
                'description': comp['description'],
                'start_date': comp['start_date'],
                'end_date': comp['end_date'],
                'registration_deadline': comp['registration_deadline'],
                'is_active': comp['is_active'],
                'top_scorers': top_scorers
            }
            competition_data.append(comp_data)
        
        return render_template('competitions.html', competitions=competition_data)
    except Exception as e:
        flash(f'Error loading competitions: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/lineup')
def lineup():
    competition_id = request.args.get('competition_id', type=int)
    
    conn = get_db_connection()
    try:
        # Get all competitions for dropdown
        competitions = fetch_all(conn, '''
            SELECT id, name FROM competitions 
            WHERE is_active = TRUE 
            ORDER BY name
        ''')
        
        # If no competition selected, use the first one
        if not competition_id and competitions:
            competition_id = competitions[0]['id']
        
        # Get clubs in the competition (approved registrations)
        clubs = fetch_all(conn, '''
            SELECT DISTINCT c.id, c.name, c.logo
            FROM clubs c
            JOIN competition_registrations cr ON c.id = cr.club_id
            WHERE cr.competition_id = ? AND cr.status = 'approved'
            ORDER BY c.name
        ''', (competition_id,))
        
        # Get lineups for each club - ONLY APPROVED PLAYERS
        lineups_data = {}
        for club in clubs:
            players = fetch_all(conn, '''
                SELECT p.id, p.fullname, p.jersey_number, l.position
                FROM players p
                JOIN lineups l ON p.id = l.player_id
                WHERE l.club_id = ? 
                  AND l.competition_id = ?
                  AND p.status = 'approved'  -- Only club-approved players
                ORDER BY 
                    CASE l.position
                        WHEN 'Goalkeeper' THEN 1
                        WHEN 'Defender' THEN 2
                        WHEN 'Midfielder' THEN 3
                        WHEN 'Forward' THEN 4
                        WHEN 'Substitute' THEN 5
                        ELSE 6
                    END,
                    p.jersey_number
            ''', (club['id'], competition_id))
            
            lineups_data[club['id']] = players
        
        return render_template('lineup.html', 
                             clubs=clubs, 
                             lineups=lineups_data,
                             competitions=competitions,
                             current_competition_id=competition_id)
    except Exception as e:
        flash(f'Error loading lineup: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/competition_registration', methods=['GET', 'POST'])
def competition_registration():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        competition_id = request.form['competition_id']
        
        conn = get_db_connection()
        try:
            existing_reg = fetch_one(conn,
                'SELECT id FROM competition_registrations WHERE club_id = ? AND competition_id = ?', 
                (session['user_id'], competition_id)
            )
            
            if existing_reg:
                flash('Your club is already registered for this competition.', 'warning')
            else:
                # Set status to 'pending' for admin approval
                execute_sql(conn, '''
                    INSERT INTO competition_registrations (club_id, competition_id, status)
                    VALUES (?, ?, 'pending')
                ''', (session['user_id'], competition_id))
                
                conn.commit()
                flash('Registration submitted! Waiting for admin approval.', 'success')
            
            return redirect(url_for('club_dashboard'))
        finally:
            conn.close()
    
    conn = get_db_connection()
    try:
        competitions_data = fetch_all(conn, 'SELECT * FROM competitions WHERE is_active = TRUE')
        return render_template('competition_registration.html', competitions=competitions_data)
    finally:
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Error handler for debugging
@app.errorhandler(500)
def internal_error(error):
    print("🔥 500 Error Details:")
    import traceback
    traceback.print_exc()
    return "Internal Server Error", 500

if __name__ == '__main__':
    from database import init_db, fix_match_events_table, clean_duplicate_competitions, create_transfer_requests_table, update_transfer_requests_table
    try:
        init_db()
        fix_match_events_table()
        clean_duplicate_competitions()
        create_transfer_requests_table()
        update_transfer_requests_table()
        print("✅ Database initialization completed successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
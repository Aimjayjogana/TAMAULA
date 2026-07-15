"""Generate fake historical data and train ML model"""
import random
from datetime import datetime, timedelta
from database import get_db_connection, execute_sql, fetch_all, fetch_one
import pickle
import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def generate_fake_matches():
    """Generate fake historical matches for your 10 clubs"""
    print("📊 Generating fake historical matches...")
    conn = get_db_connection()
    
    # Check if matches already exist
    existing = fetch_one(conn, "SELECT COUNT(*) as count FROM matches WHERE status = 'completed'")
    if existing and existing['count'] > 0:
        print(f"⚠️  Found {existing['count']} existing completed matches.")
        response = input("Delete existing matches and generate new ones? (y/n): ")
        if response.lower() == 'y':
            # Delete in correct order to avoid foreign key errors
            print("🗑️  Deleting related match events...")
            execute_sql(conn, "DELETE FROM match_events")
            
            print("🗑️  Deleting group matches...")
            execute_sql(conn, "DELETE FROM group_matches")
            
            print("🗑️  Deleting group standings...")
            execute_sql(conn, "DELETE FROM group_standings")
            
            print("🗑️  Deleting lineups...")
            execute_sql(conn, "DELETE FROM lineups")
            
            print("🗑️  Deleting matches...")
            execute_sql(conn, "DELETE FROM matches")
            
            conn.commit()
            print("✅ Existing data deleted")
        else:
            print("❌ Cancelled. Keeping existing matches.")
            conn.close()
            return False
    
    # Get all clubs
    clubs = fetch_all(conn, "SELECT id, name FROM clubs WHERE approved = TRUE")
    if len(clubs) < 2:
        print("❌ Need at least 2 clubs to generate matches")
        conn.close()
        return False
    
    club_ids = [club['id'] for club in clubs]
    
    # Get first competition ID
    competition = fetch_one(conn, "SELECT id FROM competitions LIMIT 1")
    if not competition:
        print("❌ No competition found. Please create a competition first.")
        conn.close()
        return False
    
    competition_id = competition['id']
    
    # Assign random strengths to clubs
    club_strengths = {}
    for club in clubs:
        club_strengths[club['id']] = random.randint(60, 90)
    
    # Generate matches
    matches = []
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    for home_id in club_ids:
        for away_id in club_ids:
            if home_id == away_id:
                continue
            
            date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            
            # Calculate outcome based on strengths
            home_strength = club_strengths[home_id]
            away_strength = club_strengths[away_id]
            home_effective = home_strength + 5
            
            total = home_effective + away_strength
            home_win_prob = home_effective / total
            draw_prob = 0.25 * (1 - abs(home_strength - away_strength) / 50)
            
            rand = random.random()
            
            if rand < home_win_prob:
                home_score = random.randint(1, 4)
                away_score = random.randint(0, home_score - 1)
            elif rand < home_win_prob + draw_prob:
                home_score = random.randint(0, 2)
                away_score = home_score
            else:
                away_score = random.randint(1, 4)
                home_score = random.randint(0, away_score - 1)
            
            matches.append({
                'competition_id': competition_id,
                'home_club_id': home_id,
                'away_club_id': away_id,
                'home_score': home_score,
                'away_score': away_score,
                'match_date': date.strftime('%Y-%m-%d'),
                'match_time': '15:00',
                'status': 'completed',
                'location': 'Stadium'
            })
    
    # Insert matches
    for match in matches:
        try:
            execute_sql(conn, """
                INSERT INTO matches (competition_id, home_club_id, away_club_id, 
                                   match_date, match_time, location, status, 
                                   home_score, away_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (match['competition_id'], match['home_club_id'], match['away_club_id'],
                  match['match_date'], match['match_time'], match['location'],
                  match['status'], match['home_score'], match['away_score']))
        except Exception as e:
            print(f"⚠️  Error inserting match: {e}")
            continue
    
    conn.commit()
    print(f"✅ Generated {len(matches)} fake historical matches")
    conn.close()
    return True

def extract_training_data():
    """Extract features from completed matches for training"""
    print("📊 Extracting features from matches...")
    conn = get_db_connection()
    
    matches = fetch_all(conn, """
        SELECT id, home_club_id, away_club_id, home_score, away_score, match_date
        FROM matches 
        WHERE status = 'completed'
        ORDER BY match_date
    """)
    
    if len(matches) < 10:
        print(f"❌ Not enough matches for training. Need at least 10, found {len(matches)}")
        conn.close()
        return None
    
    features_list = []
    
    for match in matches:
        if match['home_score'] > match['away_score']:
            result = 'H'
        elif match['home_score'] == match['away_score']:
            result = 'D'
        else:
            result = 'A'
        
        # Simple features for now
        features = {
            'strength_ratio': 0.5,
            'form_diff': 0.0,
            'home_advantage': 1.0,
            'result': result
        }
        features_list.append(features)
    
    conn.close()
    
    if len(features_list) < 10:
        return None
    
    return pd.DataFrame(features_list)

def train_model():
    """Train the Random Forest model"""
    print("🤖 Training Machine Learning Model...")
    
    df = extract_training_data()
    
    if df is None or len(df) < 10:
        print("⚠️  No training data found. Generating fake matches...")
        if not generate_fake_matches():
            return False
        df = extract_training_data()
        
    if df is None or len(df) < 10:
        print("❌ Still not enough data.")
        return False
    
    feature_columns = ['strength_ratio', 'form_diff', 'home_advantage']
    X = df[feature_columns]
    y = df['result']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    accuracy = model.score(X_test, y_test)
    print(f"✅ Model trained with {accuracy:.2%} accuracy")
    
    os.makedirs('ml', exist_ok=True)
    with open('ml/model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    with open('ml/feature_columns.pkl', 'wb') as f:
        pickle.dump(feature_columns, f)
    
    print("✅ Model saved to ml/model.pkl")
    return True

if __name__ == "__main__":
    train_model()
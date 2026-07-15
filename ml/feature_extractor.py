"""Extract features from your database for ML predictions"""
from database import get_db_connection, fetch_all, fetch_one
from datetime import datetime, timedelta

def get_club_strength(club_id, conn, before_date=None):
    """Calculate club strength based on all completed matches"""
    if before_date:
        query = """
            SELECT home_score, away_score, home_club_id
            FROM matches 
            WHERE (home_club_id = ? OR away_club_id = ?)
            AND status = 'completed'
            AND match_date < ?
        """
        matches = fetch_all(conn, query, (club_id, club_id, before_date))
    else:
        query = """
            SELECT home_score, away_score, home_club_id
            FROM matches 
            WHERE (home_club_id = ? OR away_club_id = ?)
            AND status = 'completed'
        """
        matches = fetch_all(conn, query, (club_id, club_id))
    
    if len(matches) == 0:
        return 70  # Default medium strength
    
    total_scored = 0
    total_conceded = 0
    
    for match in matches:
        if match['home_club_id'] == club_id:
            total_scored += match['home_score']
            total_conceded += match['away_score']
        else:
            total_scored += match['away_score']
            total_conceded += match['home_score']
    
    avg_scored = total_scored / len(matches)
    avg_conceded = total_conceded / len(matches)
    strength = 50 + (avg_scored - avg_conceded) * 10
    return max(30, min(100, strength))

def get_club_form(club_id, conn, before_date=None, num_matches=5):
    """Calculate recent form (0-1 scale)"""
    if before_date:
        query = """
            SELECT home_score, away_score, home_club_id, match_date
            FROM matches 
            WHERE (home_club_id = ? OR away_club_id = ?)
            AND status = 'completed'
            AND match_date < ?
            ORDER BY match_date DESC
            LIMIT ?
        """
        matches = fetch_all(conn, query, (club_id, club_id, before_date, num_matches))
    else:
        query = """
            SELECT home_score, away_score, home_club_id, match_date
            FROM matches 
            WHERE (home_club_id = ? OR away_club_id = ?)
            AND status = 'completed'
            ORDER BY match_date DESC
            LIMIT ?
        """
        matches = fetch_all(conn, query, (club_id, club_id, num_matches))
    
    if len(matches) == 0:
        return 0.5
    
    points = 0
    for match in matches:
        if match['home_club_id'] == club_id:
            if match['home_score'] > match['away_score']:
                points += 3
            elif match['home_score'] == match['away_score']:
                points += 1
        else:
            if match['away_score'] > match['home_score']:
                points += 3
            elif match['away_score'] == match['home_score']:
                points += 1
    
    return points / (num_matches * 3)

def get_head_to_head(home_club_id, away_club_id, conn, before_date=None):
    """Calculate home team advantage in previous meetings"""
    if before_date:
        query = """
            SELECT home_score, away_score
            FROM matches 
            WHERE ((home_club_id = ? AND away_club_id = ?) 
            OR (home_club_id = ? AND away_club_id = ?))
            AND status = 'completed'
            AND match_date < ?
            ORDER BY match_date DESC
            LIMIT 5
        """
        matches = fetch_all(conn, query, (home_club_id, away_club_id, away_club_id, home_club_id, before_date))
    else:
        query = """
            SELECT home_score, away_score
            FROM matches 
            WHERE ((home_club_id = ? AND away_club_id = ?) 
            OR (home_club_id = ? AND away_club_id = ?))
            AND status = 'completed'
            ORDER BY match_date DESC
            LIMIT 5
        """
        matches = fetch_all(conn, query, (home_club_id, away_club_id, away_club_id, home_club_id))
    
    if len(matches) == 0:
        return 0.5
    
    home_wins = 0
    for match in matches:
        if match['home_score'] > match['away_score']:
            home_wins += 1
    
    return home_wins / len(matches)

def get_features_for_match(home_club_id, away_club_id, conn, match_date=None):
    """Extract all features needed for prediction"""
    home_strength = get_club_strength(home_club_id, conn, match_date)
    away_strength = get_club_strength(away_club_id, conn, match_date)
    home_form = get_club_form(home_club_id, conn, match_date)
    away_form = get_club_form(away_club_id, conn, match_date)
    h2h = get_head_to_head(home_club_id, away_club_id, conn, match_date)
    
    # Calculate features
    strength_ratio = home_strength / (home_strength + away_strength) if (home_strength + away_strength) > 0 else 0.5
    form_diff = home_form - away_form
    home_advantage = 1.0 + (h2h * 0.3)
    
    return {
        'strength_ratio': strength_ratio,
        'form_diff': form_diff,
        'home_advantage': home_advantage
    }
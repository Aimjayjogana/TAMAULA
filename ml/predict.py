"""Make predictions for matches"""
import pickle
import os
from database import get_db_connection
from ml.feature_extractor import get_features_for_match

# Load model at module level
model = None
feature_columns = None

def load_model():
    """Load the trained model"""
    global model, feature_columns
    
    model_path = 'ml/model.pkl'
    features_path = 'ml/feature_columns.pkl'
    
    if not os.path.exists(model_path):
        print("⚠️  Model not found. Please run ml/train.py first")
        return False
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    with open(features_path, 'rb') as f:
        feature_columns = pickle.load(f)
    
    return True

def predict_match_outcome(home_club_id, away_club_id):
    """Predict outcome for a match"""
    global model, feature_columns
    
    if model is None:
        if not load_model():
            return {'outcome': 'N/A', 'confidence': 0, 'error': 'Model not trained'}
    
    conn = get_db_connection()
    try:
        features_dict = get_features_for_match(home_club_id, away_club_id, conn)
        
        # Create feature vector in correct order
        features = [[features_dict[col] for col in feature_columns]]
        
        # Predict
        prediction = model.predict(features)[0]
        probabilities = model.predict_proba(features)[0]
        confidence = max(probabilities)
        
        outcome_map = {'H': '🏠 Home Win', 'D': '🤝 Draw', 'A': '✈️ Away Win'}
        
        # Get probability for each outcome
        class_map = {cls: idx for idx, cls in enumerate(model.classes_)}
        
        return {
            'outcome': outcome_map.get(prediction, prediction),
            'confidence': round(confidence * 100, 1),
            'probabilities': {
                'home': round(probabilities[class_map.get('H', 0)] * 100, 1) if 'H' in class_map else 0,
                'draw': round(probabilities[class_map.get('D', 0)] * 100, 1) if 'D' in class_map else 0,
                'away': round(probabilities[class_map.get('A', 0)] * 100, 1) if 'A' in class_map else 0
            }
        }
    except Exception as e:
        print(f"Prediction error: {e}")
        return {'outcome': 'N/A', 'confidence': 0, 'error': str(e)}
    finally:
        conn.close()
# train_model.py - Place this in your project root folder
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

from ml.train import train_model

if __name__ == "__main__":
    print("Starting model training...")
    success = train_model()
    if success:
        print("✅ Model training completed successfully!")
    else:
        print("❌ Model training failed!")